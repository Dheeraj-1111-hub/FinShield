import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Terminal, Play, Pause, Square, AlertTriangle, 
  CheckCircle2, CircleDot, ArrowRight, ShieldCheck, Plus, List, LayoutTemplate, XCircle, Target, ArrowDown,
  Loader2, ShieldAlert
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { agentsApi } from "@/api/agents";
import { agentRuntimeApi } from "@/api/agent_runtime";
import { authoritiesApi } from "@/api/authorities";
export interface FinshieldEvaluation {
  id: string;
  timestamp: string;
  intentAlignment: "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN" | "NOT EVALUATED";
  transactionRisk: 'LOW' | 'MEDIUM' | 'HIGH' | 'NOT EVALUATED';
  policyResult: 'PASS' | 'REVIEW' | 'FAIL' | 'NOT EVALUATED';
  authorityCheck: 'PASS' | 'EXCEEDED' | 'NOT EVALUATED';
  decision: 'ALLOW' | 'REVIEW_REQUIRED' | 'BLOCK' | 'FAILED' | 'NOT EVALUATED' | 'UNAVAILABLE';
  actionContext: {
    type: string;
    amount?: number;
    target?: string;
  };
  reasoning?: string;
  isLatestAuthoritative?: boolean;
  stepNumber?: number;
  totalSteps?: number;
  runStatus?: string;
}
import { ActionGate } from "@/components/console/ActionGate";
import { DecisionTraceDrawer } from "@/components/console/DecisionTraceDrawer";

export const Route = createFileRoute("/app/console/$agentId")({
  component: AgentConsoleRoute,
});

function AgentConsoleRoute() {
  const { agentId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [developerMode, setDeveloperMode] = useState(false);
  const [inputIntent, setInputIntent] = useState("Buy laptop under ₹80K");
  const [isTraceOpen, setIsTraceOpen] = useState(false);

  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => agentsApi.get(agentId)
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['agent_runs', agentId],
    queryFn: () => agentRuntimeApi.runs.list(agentId),
    refetchInterval: 5000,
  });

  const { data: authorities, isLoading: authLoading } = useQuery({
    queryKey: ['authorities', agentId],
    queryFn: () => authoritiesApi.list(0, 10, agentId, "ACTIVE")
  });

  const activeRunIdToFetch = activeSessionId || (runs && runs.length > 0 ? runs[0]?.id : null) || null;
  
  const { data: activeRun, isLoading: runLoading } = useQuery({
    queryKey: ['run', activeRunIdToFetch],
    queryFn: () => agentRuntimeApi.runs.get(activeRunIdToFetch!),
    enabled: !!activeRunIdToFetch,
    refetchInterval: (query) => {
       const data = query.state.data;
       if (data && (data.status === 'RUNNING' || data.status === 'PENDING')) return 2000;
       // Also poll if any action is PENDING_APPROVAL so we know when it resumes
       if (data && data.actions?.some(a => a.status === 'PENDING_APPROVAL')) return 2000;
       return false;
    }
  });

  const startRunMutation = useMutation({
    mutationFn: async ({ intent, authorityId }: { intent: string, authorityId?: string | undefined }) => {
      const currentRun = runs?.find(r => r.id === activeRunIdToFetch);
      const sessionId = activeRunIdToFetch ? (currentRun?.session_id || activeRunIdToFetch) : undefined;
      const run = await agentRuntimeApi.runs.create(agentId, intent, authorityId, sessionId);
      return run;
    },
    onSuccess: (run) => {
      setActiveSessionId(run.id);
      setInputIntent("");
      queryClient.invalidateQueries({ queryKey: ['agent_runs', agentId] });
    }
  });

  const resumeRunMutation = useMutation({
    mutationFn: async (runId: string) => {
      return await agentRuntimeApi.runs.resume(runId);
    },
    onSuccess: (data) => {
      toast.success("Run resumed successfully. Payment captured.");
      queryClient.invalidateQueries({ queryKey: ['run', activeRun?.id] });
      queryClient.invalidateQueries({ queryKey: ['agent_runs', agentId] });
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
    onError: (err: any) => {
      const errorMsg = err.response?.data?.detail || err.message || "Failed to resume run";
      toast.error(errorMsg);
    }
  });

  const handleStartRun = () => {
    if (!inputIntent) return;
    const authorityId = authorities?.[0]?.id;
    startRunMutation.mutate({ intent: inputIntent, authorityId });
  };

  const handleResumeRun = () => {
    if (!activeRun || resumeRunMutation.isPending) return;
    resumeRunMutation.mutate(activeRun.id);
  };

  if (agentLoading) {
    return <div className="p-8">Loading agent...</div>;
  }
  
  if (!agent) {
    return <div className="p-8">Agent not found</div>;
  }

  // Convert real action to trajectory step
  const trajectory = activeRun ? (activeRun.actions || []).map(action => ({
    id: action.id,
    name: action.tool_name,
    status: (action.status.toLowerCase() === 'completed' || action.status.toLowerCase() === 'success') ? 'completed' : 
            action.status.toLowerCase() === 'denied' ? 'blocked' :
            action.status.toLowerCase() === 'pending_approval' ? 'blocked' : 'running',
    timestamp: new Date().toLocaleTimeString(),
    intentId: action.alignment_result ? "yes" : undefined,
    authorityId: action.authority_id ? "yes" : undefined,
    alignmentResult: action.alignment_result || undefined
  })) : [];

  // Convert real action to evaluation for the right pane
  // Find authoritative evaluation for the run
  const evaluatedActions = activeRun ? (activeRun.actions || []).filter(a => a.alignment_result && a.alignment_result !== 'UNKNOWN') : [];
  const latestEvaluatedAction = evaluatedActions.length > 0 ? evaluatedActions[evaluatedActions.length - 1] : null;
  const overallIntentAlignment = latestEvaluatedAction?.alignment_result || (
    activeRun?.status === 'FAILED' || activeRun?.authoritative_decision === 'FAILED' || activeRun?.authoritative_decision === 'UNAVAILABLE'
      ? 'MISALIGNED'
      : 'NOT EVALUATED'
  );

  const evaluations: FinshieldEvaluation[] = (() => {
    if (!activeRun) return [];
    if (activeRun.actions && activeRun.actions.length > 0) {
      return activeRun.actions.map((action, idx, arr) => {
        let decision: any = 'NOT EVALUATED';
        let reasoning = (action as any).error_message || "";
        
        // Truthful decision presentation:
        // Derive from authoritative action status and gate decision.
        if (action.status === 'DENIED') {
          decision = 'BLOCK';
          reasoning = (action as any).error_message || "Action was rejected by approver or blocked by policy";
        } else if (action.status === 'PENDING_APPROVAL') {
          decision = 'REVIEW_REQUIRED';
          reasoning = (action as any).error_message || "Action requires human approval before proceeding";
        } else if (action.status === 'FAILED') {
          decision = 'FAILED';
          reasoning = (action as any).error_message || "Action execution failed";
        } else if (action.status === 'SUCCESS' || action.status === 'COMPLETED') {
          const safeTools = ["search_products", "list_products", "get_product"];
          if (safeTools.includes(action.tool_name)) {
            decision = 'NOT EVALUATED';
          } else if (action.gate_decision === 'ALLOW') {
            decision = 'ALLOW';
            if (action.tool_name === 'checkout') {
              const orderId = (action.output as any)?.order_id;
              reasoning = orderId 
                ? `Cart checked out successfully. Order ${orderId} created in PENDING_PAYMENT. Final payment authorization requires pay_order.`
                : "Cart checked out successfully. Order created in PENDING_PAYMENT. Final payment authorization requires pay_order.";
            } else if (action.tool_name === 'pay_order') {
              reasoning = "Payment authorized and captured successfully.";
            } else {
              reasoning = "Action approved and executed successfully";
            }
          } else if (action.gate_decision === 'REVIEW') {
            decision = 'REVIEW_REQUIRED';
            reasoning = (action as any).error_message || "Action requires human approval";
          } else if (action.gate_decision === 'BLOCK') {
            decision = 'BLOCK';
            reasoning = (action as any).error_message || "Action blocked by policy";
          } else {
            // Protected action executed without an authoritative GateDecision - NEVER convert to ALLOW!
            decision = 'NOT EVALUATED';
            reasoning = "Protected action executed without authoritative gate decision";
          }
        } else if (activeRun.status === 'BLOCKED') {
          decision = 'BLOCK';
          reasoning = (action as any).error_message || "Run blocked before this action could execute";
        } else if (activeRun.status === 'WAITING_FOR_APPROVAL') {
          decision = 'REVIEW_REQUIRED';
          reasoning = "Waiting for human approval";
        } else if (activeRun.status === 'FAILED') {
          decision = 'FAILED';
          reasoning = "Run failed";
        } else {
          decision = 'NOT EVALUATED';
        }

        const intentAlignmentValue = ((action.alignment_result && action.alignment_result !== 'UNKNOWN') 
          ? action.alignment_result 
          : 'NOT EVALUATED') as "PARTIAL" | "ALIGNED" | "MISALIGNED" | "UNKNOWN" | "NOT EVALUATED";

        const policyResultValue = decision === 'REVIEW_REQUIRED' 
          ? 'REVIEW' 
          : (decision === 'BLOCK' ? 'FAIL' : (decision === 'ALLOW' ? 'PASS' : 'NOT EVALUATED'));

        const authorityCheckValue = decision === 'BLOCK' && ((action as any).error_code === 'CAPABILITY_DENIED' || ((action as any).error_message && (action as any).error_message.toLowerCase().includes('authority')))
          ? 'EXCEEDED'
          : (decision === 'ALLOW' || decision === 'REVIEW_REQUIRED' ? 'PASS' : 'NOT EVALUATED');

        const transactionRiskValue = (decision === 'ALLOW' || decision === 'REVIEW_REQUIRED') 
          ? 'LOW' 
          : (decision === 'BLOCK' ? 'HIGH' : 'NOT EVALUATED');

        const isLastAction = idx === arr.length - 1;
        const isRunFailed = activeRun.status === 'FAILED';
        const isCheckout = action.tool_name === 'checkout';
        const hasCompletedPayment = arr.some(a => a.tool_name === 'pay_order' && (a.status === 'SUCCESS' || a.status === 'COMPLETED'));
        const hasPendingApprovalAction = arr.some(a => a.status === 'PENDING_APPROVAL') || activeRun.status === 'WAITING_FOR_APPROVAL';

        // Intermediate checkout creates an order in PENDING_PAYMENT, but does NOT authorize payment.
        // It must NOT be labeled as the run's Latest Authoritative Decision when payment is pending, unexecuted, or failed.
        const isIntermediateCheckout = isCheckout && (!hasCompletedPayment || hasPendingApprovalAction || isRunFailed);
        const isLatestAuthoritative = isLastAction && !isRunFailed && !isIntermediateCheckout;

        let targetText = action.input ? JSON.stringify(action.input) : "Execution";
        if (action.tool_name === 'checkout') {
          const orderId = (action.output as any)?.order_id;
          if (orderId) targetText = `Order ${orderId}`;
        } else if (action.tool_name === 'pay_order') {
          const orderId = (action.input as any)?.order_id;
          if (orderId) targetText = `Payment for ${orderId}`;
        }

        const amountVal = (action.output as any)?.total || (action.output as any)?.amount || (action.input as any)?.amount;

        return {
          id: action.id,
          timestamp: new Date().toISOString(),
          intentAlignment: intentAlignmentValue,
          transactionRisk: transactionRiskValue,
          policyResult: policyResultValue,
          authorityCheck: authorityCheckValue,
          decision: decision,
          actionContext: {
            type: action.tool_name,
            target: targetText,
            amount: typeof amountVal === 'number' ? amountVal : undefined
          },
          reasoning: reasoning,
          runId: activeRun.id,
          actionId: action.id,
          isLatestAuthoritative: isLatestAuthoritative,
          stepNumber: idx + 1,
          totalSteps: arr.length,
          runStatus: activeRun.status
        };
      });
    }

    if (activeRun.status === 'FAILED' || activeRun.authoritative_decision === 'FAILED' || activeRun.authoritative_decision === 'UNAVAILABLE') {
      const isRefusal = activeRun.error_code === 'LLM_REFUSAL';
      return [{
        id: `unexecuted-${activeRun.id}`,
        timestamp: activeRun.completed_at || activeRun.created_at || new Date().toISOString(),
        intentAlignment: 'MISALIGNED' as const,
        transactionRisk: 'HIGH' as const,
        policyResult: 'FAIL' as const,
        authorityCheck: 'NOT EVALUATED' as const,
        decision: (activeRun.authoritative_decision === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'FAILED') as any,
        actionContext: {
          type: isRefusal ? 'LLM Refusal' : 'Execution Halted',
          target: activeRun.error_message || 'Model refused or failed before executing financial action'
        },
        reasoning: activeRun.error_message || 'Financial action failed before any tool execution.',
        runId: activeRun.id,
        isLatestAuthoritative: true,
        stepNumber: 1,
        totalSteps: 1,
        runStatus: activeRun.status
      }];
    }

    return [];
  })();

  // Determine authoritative headline gate decision for the run
  const isRunWaitingApproval = activeRun?.status === 'WAITING_FOR_APPROVAL' || (activeRun?.actions || []).some(a => a.status === 'PENDING_APPROVAL');
  const isRunBlocked = activeRun?.status === 'BLOCKED' || (activeRun?.actions || []).some(a => a.status === 'DENIED');
  const isRunFailed = activeRun?.status === 'FAILED' || (activeRun?.actions || []).some(a => a.status === 'FAILED');

  const hasCheckout = (activeRun?.actions || []).some(a => a.tool_name === 'checkout' && (a.status === 'SUCCESS' || a.status === 'COMPLETED'));
  const hasPaid = (activeRun?.actions || []).some(a => a.tool_name === 'pay_order' && (a.status === 'SUCCESS' || a.status === 'COMPLETED'));

  const headlineDecision: 'ALLOW' | 'REVIEW_REQUIRED' | 'BLOCK' | 'FAILED' | 'UNAVAILABLE' | 'NOT EVALUATED' = (() => {
    if (isRunWaitingApproval) return 'REVIEW_REQUIRED';
    if (isRunBlocked) return 'BLOCK';
    if (isRunFailed) return 'FAILED';
    if (activeRun?.authoritative_decision) {
      if (activeRun.authoritative_decision === 'REVIEW' || activeRun.authoritative_decision === 'REVIEW_REQUIRED') return 'REVIEW_REQUIRED';
      if (activeRun.authoritative_decision === 'BLOCK') return 'BLOCK';
      if (activeRun.authoritative_decision === 'FAILED') return 'FAILED';
      if (activeRun.authoritative_decision === 'UNAVAILABLE') return 'UNAVAILABLE';
      if (activeRun.authoritative_decision === 'ALLOW') {
        if (hasCheckout && !hasPaid) return 'REVIEW_REQUIRED';
        return 'ALLOW';
      }
    }
    if (hasCheckout && !hasPaid) {
      return 'REVIEW_REQUIRED';
    }
    const evaluated = (evaluations || []).filter(e => e.decision !== 'NOT EVALUATED');
    if (evaluated.length > 0) {
      const latest = evaluated[evaluated.length - 1];
      if (latest && (latest.decision === 'ALLOW' || latest.decision === 'REVIEW_REQUIRED' || latest.decision === 'BLOCK' || latest.decision === 'FAILED' || latest.decision === 'UNAVAILABLE')) {
        if (latest.decision === 'ALLOW' && hasCheckout && !hasPaid) return 'REVIEW_REQUIRED';
        return latest.decision;
      }
    }
    return 'NOT EVALUATED';
  })();

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden animate-in fade-in duration-300 -m-8">
      
      {/* LEFT PANE: Workspace & Sessions (250px) */}
      <div className="w-[250px] shrink-0 border-r border-border bg-surface flex flex-col h-full z-10 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.5)]">
        <div className="p-4 border-b border-border">
          <Button 
            variant="outline" 
            className="w-full justify-between bg-background border-border hover:bg-surface-raised h-10 px-3"
            onClick={() => navigate({ to: '/app/console' })}
          >
            <div className="flex items-center gap-2 truncate">
              <span className="size-2 rounded-full bg-safe shrink-0" />
              <span className="font-semibold truncate">{agent.name}</span>
            </div>
            <span className="text-xs text-muted-foreground ml-2">▾</span>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-6">
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-2 flex justify-between items-center">
              <span>Sessions</span>
              <Button variant="ghost" size="icon" className="h-5 w-5 rounded-full hover:bg-surface" onClick={() => setActiveSessionId(null)}>
                <Plus className="size-3" />
              </Button>
            </div>
            <div className="space-y-1">
              {runs?.map(run => (
                <button
                  key={run.id}
                  onClick={() => setActiveSessionId(run.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors ${
                    activeRunIdToFetch === run.id 
                      ? 'bg-primary/10 text-primary font-medium border border-primary/20' 
                      : 'hover:bg-surface-raised text-muted-foreground'
                  }`}
                >
                  <div className="truncate mb-1">{run.input || "No Intent"}</div>
                  <div className="flex items-center gap-1.5 text-xs opacity-80">
                    {run.status === 'COMPLETED' && <CheckCircle2 className="size-3 text-safe" />}
                    {run.status === 'RUNNING' && <CircleDot className="size-3 text-primary animate-pulse" />}
                    {run.status === 'FAILED' && <AlertTriangle className="size-3 text-danger" />}
                    <span className="capitalize">{run.status.toLowerCase()}</span>
                  </div>
                </button>
              ))}
              {runs?.length === 0 && (
                <div className="px-2 text-xs text-muted-foreground">No sessions yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* CENTER PANE: Agent Trajectory & Interaction */}
      <div className="flex-1 flex flex-col min-w-0 bg-background relative z-0">
        
        {/* Center Header */}
        <div className="h-14 border-b border-border flex items-center justify-between px-6 bg-surface/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-3">
            {activeRun?.status === 'WAITING_FOR_APPROVAL' || (activeRun?.actions || []).some(a => a.status === 'PENDING_APPROVAL') ? (
              <span className="flex items-center gap-1.5 text-xs font-bold tracking-wider text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" /> WAITING FOR APPROVAL
              </span>
            ) : activeRun?.status === 'RUNNING' ? (
              <span className="flex items-center gap-1.5 text-xs font-bold tracking-wider text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                <span className="size-1.5 rounded-full bg-primary animate-pulse" /> LIVE
              </span>
            ) : activeRun?.status === 'FAILED' ? (
              <span className="flex items-center gap-1.5 text-xs font-bold tracking-wider text-danger bg-danger/10 px-2 py-0.5 rounded-full border border-danger/20">
                <AlertTriangle className="size-3" /> FAILED
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-bold tracking-wider text-muted-foreground bg-surface-raised px-2 py-0.5 rounded-full border border-border">
                {activeRun?.status || 'NO RUN'}
              </span>
            )}
            <span className="text-xs font-mono text-muted-foreground hidden sm:inline-block">Execution: {activeRun?.id || '---'}</span>
          </div>
        </div>

        {/* Conversation Workspace */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-10 space-y-10 custom-scrollbar">
          
          {!activeRun ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto space-y-6">
              <Terminal className="size-12 text-muted-foreground opacity-50" />
              <h2 className="text-xl font-semibold">Start a new session</h2>
              <input 
                type="text" 
                value={inputIntent}
                onChange={e => setInputIntent(e.target.value)}
                placeholder="What should the agent do?"
                className="w-full bg-surface border border-border rounded-md p-3 focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
              <Button onClick={handleStartRun} disabled={startRunMutation.isPending || !inputIntent} className="w-full">
                {startRunMutation.isPending ? "Starting..." : "Start Agent Run"}
              </Button>
            </div>
          ) : (
            <>
              {/* User Message */}
              <div className="flex gap-4 max-w-3xl mx-auto">
                <div className="size-8 rounded bg-surface border border-border flex items-center justify-center shrink-0 mt-1 font-semibold text-sm">
                  ME
                </div>
                <div className="flex-1 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">YOU</div>
                  <div className="bg-surface border border-border rounded-2xl rounded-tl-sm p-4 text-[15px] leading-relaxed">
                    {activeRun.input}
                  </div>
                </div>
              </div>

              {/* Agent Trajectory */}
              <div className="flex gap-4 max-w-3xl mx-auto pb-8">
                <div className="size-8 rounded bg-primary/20 text-primary border border-primary/30 flex items-center justify-center shrink-0 mt-1">
                  <Terminal className="size-4" />
                </div>
                <div className="flex-1 space-y-4">
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{agent.name}</div>
                  
                  <div className="bg-background rounded-lg border border-border overflow-hidden">
                    <div className="bg-surface px-4 py-2.5 border-b border-border text-xs font-semibold text-muted-foreground flex items-center gap-2">
                      <LayoutTemplate className="size-3.5" />
                      TASK PROGRESS
                    </div>
                    <div className="p-4 space-y-4">
                      {trajectory.map((step, idx) => (
                        <div key={step.id} className="flex items-start gap-3">
                          <div className="mt-0.5">
                            {step.status === 'completed' && <CheckCircle2 className="size-4 text-safe" />}
                            {step.status === 'running' && <ArrowRight className="size-4 text-primary animate-pulse" />}
                            {step.status === 'pending' && <CircleDot className="size-4 text-muted-foreground/30" />}
                            {step.status === 'blocked' && <XCircle className="size-4 text-danger" />}
                          </div>
                          <div className="flex-1">
                            <div className={`text-sm ${
                              step.status === 'running' ? 'text-primary font-medium' :
                              step.status === 'blocked' ? 'text-danger font-medium' :
                              step.status === 'pending' ? 'text-muted-foreground' : 'text-foreground'
                            }`}>
                              {step.name}
                            </div>
                            {(step.authorityId || step.intentId) && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {step.authorityId && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20">
                                    <ShieldCheck className="size-3" /> Auth
                                  </span>
                                )}
                                {step.intentId && (
                                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                                    step.alignmentResult === 'ALIGNED' ? 'bg-safe/10 text-safe border-safe/20' :
                                    step.alignmentResult === 'MISALIGNED' ? 'bg-danger/10 text-danger border-danger/20' :
                                    'bg-muted text-muted-foreground border-border'
                                  }`}>
                                    <Target className="size-3" /> Intent
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="text-xs font-mono text-muted-foreground/50">
                            {step.timestamp}
                          </div>
                        </div>
                      ))}
                      {activeRun.status === 'RUNNING' && !(activeRun?.actions || []).some(a => a.status === 'PENDING_APPROVAL') && (
                        <div className="flex items-start gap-3">
                           <div className="mt-0.5"><CircleDot className="size-4 text-muted-foreground/30 animate-pulse" /></div>
                           <div className="text-sm text-muted-foreground">Thinking...</div>
                        </div>
                      )}
                    </div>
                  </div>

                  {activeRun.output && (() => {
                    const hasCompletedPayment = activeRun.actions?.some(a => a.tool_name === 'pay_order' && (a.status === 'SUCCESS' || a.status === 'COMPLETED'));
                    const isPartiallyBlocked = hasCompletedPayment && (activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED');

                    return (
                      <div className={`p-4 rounded-lg border text-sm flex items-start gap-3 ${
                        isPartiallyBlocked
                          ? 'bg-amber-500/10 border-amber-500/30 text-amber-500'
                          : (activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED')
                            ? 'bg-danger/10 border-danger/30 text-danger'
                            : 'bg-safe/10 border-safe/30 text-safe'
                      }`}>
                        {isPartiallyBlocked ? (
                          <AlertTriangle className="size-4 mt-0.5 shrink-0 text-amber-500" />
                        ) : (activeRun.status === 'BLOCKED' || activeRun.status === 'FAILED') ? (
                          <AlertTriangle className="size-4 mt-0.5 shrink-0" />
                        ) : (
                          <CheckCircle2 className="size-4 mt-0.5 shrink-0" />
                        )}
                        <div>
                          <div className="font-semibold text-xs uppercase tracking-wider mb-0.5">
                            {isPartiallyBlocked 
                              ? 'Order Completed (Subsequent Action Blocked)' 
                              : (activeRun.status === 'BLOCKED' ? 'Run Blocked' : activeRun.status === 'FAILED' ? 'Run Failed' : 'Final Result')}
                          </div>
                          <div className="text-foreground text-xs leading-relaxed">
                            {activeRun.output}
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Chat Input */}
        <div className="p-4 bg-background border-t border-border">
          <div className="max-w-3xl mx-auto relative flex items-center">
            <div className="absolute left-3 flex gap-2">
              <Button variant="ghost" size="icon" className="size-8 rounded-full text-muted-foreground"><Plus className="size-4" /></Button>
            </div>
            <input 
              type="text" 
              value={inputIntent}
              onChange={e => setInputIntent(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleStartRun()}
              placeholder={`Message ${agent.name}...`}
              className="w-full bg-surface border border-border rounded-full py-3 pl-14 pr-14 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
            />
            <Button onClick={handleStartRun} disabled={startRunMutation.isPending || !inputIntent} size="icon" className="absolute right-2 size-8 rounded-full bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground">
              <ArrowRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* RIGHT PANE: Finshield Runtime (340px) */}
      <div className="w-[340px] shrink-0 border-l border-border bg-surface flex flex-col h-full z-10 shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.5)]">
        
        <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-background shrink-0">
          <div className="flex items-center gap-2 text-sm font-semibold tracking-wide">
            <ShieldCheck className="size-4 text-safe" />
            FINSHIELD RUNTIME
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar bg-background">
          
          <div className="space-y-3">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Intent Alignment</div>
            <div className="p-3 bg-surface border border-border rounded-lg space-y-2">
              <div className="flex justify-between items-end">
                <span className={`text-xl font-bold tracking-tight ${
                  overallIntentAlignment === 'ALIGNED' ? 'text-safe' :
                  overallIntentAlignment === 'MISALIGNED' ? 'text-danger' :
                  overallIntentAlignment === 'PARTIAL' ? 'text-warn' :
                  'text-muted-foreground'
                }`}>
                  {overallIntentAlignment}
                </span>
                <span className="text-xs text-muted-foreground font-mono">STATUS</span>
              </div>
            </div>
          </div>

          {/* Headline Authoritative Gate Decision */}
          <div className="space-y-3">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Headline Decision</div>
            <div className={`p-4 rounded-lg border space-y-2 ${
              headlineDecision === 'ALLOW' ? 'bg-safe/10 border-safe/30 text-safe' :
              headlineDecision === 'REVIEW_REQUIRED' ? 'bg-warn/10 border-warn/30 text-warn' :
              headlineDecision === 'BLOCK' ? 'bg-danger/10 border-danger/30 text-danger' :
              headlineDecision === 'FAILED' ? 'bg-danger/10 border-danger/30 text-danger' :
              headlineDecision === 'UNAVAILABLE' ? 'bg-danger/10 border-danger/30 text-danger' :
              'bg-primary/10 border-primary/20 text-primary'
            }`}>
              <div className="flex justify-between items-center">
                <span className="text-xl font-bold tracking-tight flex items-center gap-2">
                  {headlineDecision === 'ALLOW' && <CheckCircle2 className="size-5 text-safe" />}
                  {headlineDecision === 'REVIEW_REQUIRED' && <ShieldAlert className="size-5 text-warn" />}
                  {(headlineDecision === 'BLOCK' || headlineDecision === 'FAILED' || headlineDecision === 'UNAVAILABLE') && <XCircle className="size-5 text-danger" />}
                  {headlineDecision === 'NOT EVALUATED' && <CircleDot className="size-5 text-primary" />}
                  {headlineDecision === 'NOT EVALUATED' ? 'READ-ONLY' : headlineDecision}
                </span>
                <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-background/50 border border-current/20">
                  {activeRun?.status || 'NO RUN'}
                </span>
              </div>
              <div className="text-xs text-muted-foreground leading-relaxed">
                {headlineDecision === 'REVIEW_REQUIRED' && "Human review required. Protected financial action paused."}
                {headlineDecision === 'BLOCK' && "Protected financial action blocked by security policy."}
                {headlineDecision === 'ALLOW' && "Execution authorized: Protected financial action evaluated and permitted."}
                {headlineDecision === 'NOT EVALUATED' && "Permitted read-only operation. No financial action gated or authorized."}
                {headlineDecision === 'FAILED' && (activeRun?.error_message || "Action execution failed or refused by model.")}
                {headlineDecision === 'UNAVAILABLE' && (activeRun?.error_message || "Protected financial action unavailable or blocked.")}
              </div>
              {headlineDecision === 'REVIEW_REQUIRED' && (
                <div className="pt-2">
                  <Button variant="outline" className="w-full bg-safe/10 text-safe border-safe hover:bg-safe/20 text-xs h-8" onClick={() => navigate({ to: '/app/approvals' })}>
                    Review Pending Approval
                  </Button>
                </div>
              )}
            </div>
          </div>

          {[...evaluations].reverse().map((evaluation, i) => (
            <div key={evaluation.id} className="pt-4 border-t border-border mt-6">
              <ActionGate 
                evaluation={evaluation} 
                onInspectDecisionTrace={() => setIsTraceOpen(true)}
              />
              
              {evaluation.decision === 'REVIEW_REQUIRED' && (
                <div className="mt-4 flex gap-2">
                  <Button variant="outline" className="w-full bg-safe/10 text-safe border-safe hover:bg-safe/20" onClick={() => navigate({ to: '/app/approvals' })}>
                    Go To Approvals
                  </Button>
                </div>
              )}
            </div>
          ))}
          
          {activeRun && (activeRun?.actions || []).some(a => a.status === 'PENDING_APPROVAL') && (
            <Button 
              className="w-full mt-4 flex items-center justify-center gap-2" 
              onClick={handleResumeRun}
              disabled={resumeRunMutation.isPending}
            >
              {resumeRunMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Resuming & Capturing Payment...</span>
                </>
              ) : (
                <span>Resume Run (After Approval)</span>
              )}
            </Button>
          )}

          {evaluations.length === 0 && (
            <div className="text-center p-8 border border-dashed border-border rounded-xl text-muted-foreground text-sm">
              Monitoring agent activity...
            </div>
          )}

        </div>
      </div>

      <DecisionTraceDrawer 
        runId={activeRun?.id || null}
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
      />
    </div>
  );
}
