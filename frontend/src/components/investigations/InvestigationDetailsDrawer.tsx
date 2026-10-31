import { useState, useRef } from "react";
import { X, ArrowRight, ShieldAlert, Lock, Unlock, FileText, CheckCircle2, ChevronRight, Link as LinkIcon, Search, CreditCard, ShoppingCart, Terminal, AlertCircle, Loader2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Investigation } from "@/data/mock-investigations";
import { Button } from "@/components/ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { investigationsApi } from "@/api/investigations";
import type { ResolutionType } from "@/types/investigation";

interface InvestigationDetailsDrawerProps {
  investigation: Investigation;
  onClose: () => void;
}

const RESOLUTION_OPTIONS: { label: string; value: ResolutionType }[] = [
  { label: "False positive — expected behavior", value: "FALSE_POSITIVE" },
  { label: "Confirmed threat — action blocked correctly", value: "CONFIRMED_THREAT" },
  { label: "Authorized behavior — policy updated", value: "AUTHORIZED_BEHAVIOR" },
  { label: "Policy configuration issue", value: "POLICY_CONFIGURATION_ISSUE" },
  { label: "Agent misbehavior — remediated", value: "AGENT_MISBEHAVIOR" },
  { label: "Merchant / third-party issue", value: "MERCHANT_ISSUE" },
  { label: "User error", value: "USER_ERROR" },
  { label: "System error", value: "SYSTEM_ERROR" },
  { label: "Other", value: "OTHER" },
];

export function InvestigationDetailsDrawer({ investigation, onClose }: InvestigationDetailsDrawerProps) {
  const [isContained, setIsContained] = useState(investigation.status === 'CONTAINED');
  const [showContainmentConfirm, setShowContainmentConfirm] = useState(false);
  const [showResolveConfirm, setShowResolveConfirm] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  // Preserve user inputs on failure
  const resolutionRef = useRef<HTMLSelectElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);

  const queryClient = useQueryClient();

  const isCritical = investigation.severity === 'CRITICAL';

  const resolveMutation = useMutation({
    mutationFn: (data: { resolution: ResolutionType; resolution_reason: string }) =>
      investigationsApi.resolveInvestigation(investigation.id, data),
    onSuccess: async (data: any) => {
      // Refresh the investigations list and counters from persisted backend data
      await queryClient.invalidateQueries({ queryKey: ['investigations'] });
      await queryClient.refetchQueries({ queryKey: ['investigations'] });
      toast.success(`Investigation ${investigation.id} successfully resolved as ${data?.resolution || 'RESOLVED'}`);
      setShowResolveConfirm(false);
      setResolveError(null);
      onClose();
    },
    onError: (err: any) => {
      // Surface the real actionable error — keep drawer open with entered values
      const detail =
        err?.response?.data?.error?.message ??
        err?.response?.data?.detail ??
        err?.message ??
        "Resolution failed. Please try again.";
      const errorMsg = typeof detail === "string" ? detail : JSON.stringify(detail);
      setResolveError(errorMsg);
      toast.error(errorMsg);
    },
  });

  const handleContainAgent = () => {
    setIsContained(true);
    setShowContainmentConfirm(false);
  };

  const handleResolve = () => {
    const resolution = resolutionRef.current?.value as ResolutionType;
    const notes = notesRef.current?.value?.trim() ?? "";

    if (!resolution) {
      const msg = "Please select a resolution type.";
      setResolveError(msg);
      toast.error(msg);
      return;
    }

    setResolveError(null);
    resolveMutation.mutate({ resolution, resolution_reason: notes || `Resolved as: ${resolution}` });
  };

  return (
    <div className="absolute inset-y-0 right-0 w-[700px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onClose} className="size-6 -ml-2 rounded-full">
              <ArrowRight className="size-3.5 rotate-180" />
            </Button>
            Investigations
          </div>
          <span className="text-muted-foreground">/</span>
          <div className="font-mono text-sm font-bold">{investigation.id}</div>
        </div>
        <div className="flex items-center gap-2">
          {!isContained ? (
            <Button variant="outline" size="sm" onClick={() => setShowContainmentConfirm(true)} className="border-danger/30 text-danger hover:bg-danger/10 hover:text-danger h-8">
              <Lock className="size-3.5 mr-1.5" /> Contain Agent
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setIsContained(false)} className="border-border text-muted-foreground h-8">
              <Unlock className="size-3.5 mr-1.5" /> Release Agent
            </Button>
          )}
          {(investigation as any).status !== 'RESOLVED' && (investigation as any).status !== 'CLOSED' && (
            <Button
              size="sm"
              onClick={() => { setShowResolveConfirm(true); setResolveError(null); }}
              className="h-8"
              id="resolve-investigation-btn"
            >
              Resolve Investigation
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full ml-1">
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        
        {/* Modals / Alerts Layer */}
        {showContainmentConfirm && (
          <div className="bg-surface border border-danger/30 rounded-xl p-5 mb-6 shadow-lg animate-in zoom-in-95 duration-200">
            <div className="flex items-start gap-3">
              <div className="size-10 rounded-full bg-danger/10 flex items-center justify-center shrink-0">
                <Lock className="size-5 text-danger" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold mb-1">Contain {investigation.agentName}?</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  This will temporarily suspend autonomous financial actions for this agent.
                  <br/>Active sessions: 1. Pending transactions: 0.
                </p>
                <div className="space-y-1 mb-4">
                  <div className="text-xs font-semibold text-muted-foreground">Reason</div>
                  <input type="text" defaultValue={`${investigation.title} investigation`} className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm" />
                </div>
                <div className="flex justify-end gap-3">
                  <Button variant="outline" onClick={() => setShowContainmentConfirm(false)}>Cancel</Button>
                  <Button variant="destructive" onClick={handleContainAgent}>Contain Agent</Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {showResolveConfirm && (
          <div className="bg-surface border border-border rounded-xl p-5 mb-6 shadow-lg animate-in zoom-in-95 duration-200">
            <h3 className="text-base font-bold mb-4 uppercase tracking-wider text-muted-foreground text-xs">Resolve Investigation</h3>
            
            {/* Error banner — shown inline to keep drawer open */}
            {resolveError && (
              <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 rounded-lg p-3 mb-4 text-sm text-danger">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <span>{resolveError}</span>
              </div>
            )}

            <div className="space-y-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">Resolution type</div>
                <select
                  ref={resolutionRef}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
                  defaultValue=""
                >
                  <option value="" disabled>Select resolution…</option>
                  {RESOLUTION_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium">Analyst notes</div>
                <textarea
                  ref={notesRef}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:border-primary"
                  placeholder="Add context to the resolution..."
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={() => { setShowResolveConfirm(false); setResolveError(null); }}
                  disabled={resolveMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleResolve}
                  disabled={resolveMutation.isPending}
                  id="confirm-resolve-investigation"
                >
                  {resolveMutation.isPending ? (
                    <><Loader2 className="size-4 mr-2 animate-spin" /> Resolving…</>
                  ) : (
                    "Resolve Investigation"
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {isContained && !showContainmentConfirm && (
          <div className="bg-danger/5 border border-danger/20 rounded-xl p-4 flex items-start gap-3">
            <div className="size-8 rounded-full bg-danger/20 flex items-center justify-center shrink-0">
              <Lock className="size-4 text-danger" />
            </div>
            <div>
              <div className="font-bold text-danger uppercase tracking-wider text-sm mb-0.5">Agent Contained</div>
              <div className="text-sm text-foreground/80 mb-2">Autonomous financial actions are suspended.</div>
              <div className="text-xs font-mono text-muted-foreground">Reason: {investigation.id} — {investigation.title}</div>
            </div>
          </div>
        )}

        {/* Hero Section */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider border uppercase ${
              isCritical ? 'bg-danger/10 text-danger border-danger/20' : 
              'bg-warn/10 text-warn border-warn/20'
            }`}>
              <div className={`size-1.5 rounded-full ${isCritical ? 'bg-danger' : 'bg-warn'}`} />
              {investigation.severity}
            </div>
            <div className={`text-xs font-bold tracking-wider uppercase border px-2.5 py-1 rounded-md ${
              investigation.status === 'RESOLVED' ? 'bg-safe/10 text-safe border-safe/20' : 'bg-surface-raised text-muted-foreground border-border'
            }`}>
              {investigation.status}
            </div>
            {investigation.resolution && (
              <div className="text-xs font-bold tracking-wider text-safe uppercase border border-safe/30 bg-safe/10 px-2.5 py-1 rounded-md flex items-center gap-1">
                <CheckCircle2 className="size-3" />
                {investigation.resolution.replace(/_/g, ' ')}
              </div>
            )}
          </div>
          
          <h2 className="text-3xl font-bold tracking-tight mb-2">{investigation.title}</h2>
          <p className="text-lg text-muted-foreground">{investigation.description}</p>
        </div>

        {/* Investigation Summary */}
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Investigation Summary</div>
          <p className="text-sm leading-relaxed mb-6">
            {investigation.decisionReason?.toLowerCase().includes('rejected by approver') || investigation.description?.toLowerCase().includes('rejected by approver')
              ? "FINSHIELD blocked this autonomous transaction because the human approver rejected the requested action during Action Gate review. The proposed action remained aligned with authorized intent constraints, but was halted by human-in-the-loop governance."
              : investigation.divergenceSignals && investigation.divergenceSignals.length > 0
              ? "FINSHIELD blocked an autonomous transaction because the requested action materially diverged from the agent's authorized intent."
              : "FINSHIELD evaluated this autonomous transaction through the Action Gate and blocked execution in accordance with governance policies."}
          </p>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Confidence</div>
              <div className="text-xl font-bold font-mono">{investigation.confidence}%</div>
            </div>
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Risk Score</div>
              <div className="text-xl font-bold font-mono text-danger">{investigation.riskScore} / 100</div>
            </div>
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Intent Alignment</div>
              <div className={`text-xl font-bold font-mono ${investigation.intentAlignment >= 80 ? 'text-safe' : 'text-danger'}`}>
                {investigation.intentAlignment}%
              </div>
            </div>
          </div>
        </div>

        {/* Intent Analysis & Action Alignment */}
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Intent & Action Evidence</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-surface border border-border rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">Original User Intent</div>
                <div className="text-sm font-mono p-3 bg-background border border-border rounded-lg">"{investigation.originalIntent}"</div>
              </div>
            </div>
            <div className={`bg-surface border rounded-xl p-4 flex flex-col justify-between relative overflow-hidden ${
              investigation.divergenceSignals.length > 0 ? 'border-danger/30' : 'border-border'
            }`}>
              {investigation.divergenceSignals.length > 0 && (
                <div className="absolute right-0 top-0 w-32 h-32 bg-danger/5 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none" />
              )}
              <div>
                <div className={`text-[10px] font-bold uppercase tracking-wider mb-2 ${
                  investigation.divergenceSignals.length > 0 ? 'text-danger' : 'text-muted-foreground'
                }`}>
                  Agent Proposed Action
                </div>
                <div className={`text-sm font-mono p-3 bg-background border rounded-lg relative z-10 ${
                  investigation.divergenceSignals.length > 0 ? 'border-danger/30 text-danger' : 'border-border text-foreground'
                }`}>
                  "{investigation.executedIntent}"
                </div>
              </div>
            </div>
          </div>

          {/* Action Gate Outcome & Decision Reason */}
          <div className="bg-surface border border-border rounded-xl p-4 mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">Action Gate Outcome & Decision Reason</div>
              <div className="text-sm font-medium text-foreground">
                {investigation.decisionReason || investigation.description || "Action blocked by Action Gate"}
              </div>
            </div>
            <div className={`text-xs font-bold font-mono px-2.5 py-1 rounded border uppercase ${
              (investigation.outcome === 'REJECTED' || (investigation.description && investigation.description.includes('rejected by approver')))
                ? 'border-danger/30 bg-danger/10 text-danger'
                : 'border-border bg-surface-raised text-muted-foreground'
            }`}>
              {investigation.outcome || (investigation.description?.includes('rejected by approver') ? 'REJECTED' : 'BLOCKED')}
            </div>
          </div>
          
          <div className="bg-surface border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                {investigation.divergenceSignals.length > 0 ? "Divergence Signals" : "Intent Alignment Signals"}
              </div>
              <div className={`flex items-center gap-2 font-mono font-bold text-sm ${
                investigation.intentAlignment >= 80 ? 'text-safe' : 'text-danger'
              }`}>
                {investigation.intentAlignment >= 80 && <CheckCircle2 className="size-4 text-safe" />}
                {investigation.intentAlignment}% MATCH
              </div>
            </div>
            
            <div className="w-full h-2 bg-surface-raised rounded-full mb-6 overflow-hidden flex">
              <div className="h-full bg-safe" style={{ width: `${investigation.intentAlignment}%` }} />
              <div className="h-full bg-danger/80" style={{ width: `${100 - investigation.intentAlignment}%` }} />
            </div>

            {investigation.divergenceSignals.length > 0 ? (
              <div className="space-y-3">
                {investigation.divergenceSignals.map((signal, idx) => (
                  <div key={idx} className="flex gap-4 p-3 bg-background border border-border rounded-lg text-sm">
                    <X className="size-4 text-danger shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="font-semibold mb-2">{signal.type}</div>
                      <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                        <div>
                          <div className="text-muted-foreground mb-1">User requested:</div>
                          <div>{signal.userRequested}</div>
                        </div>
                        <div>
                          <div className="text-danger mb-1">Agent requested:</div>
                          <div className="text-danger">{signal.agentRequested}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {investigation.alignmentSignals && investigation.alignmentSignals.length > 0 ? (
                  investigation.alignmentSignals.map((signal, idx) => (
                    <div key={idx} className="flex gap-4 p-3 bg-background border border-border rounded-lg text-sm">
                      <CheckCircle2 className="size-4 text-safe shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="font-semibold mb-1 flex items-center gap-2">
                          <span>{signal.type}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-safe/10 text-safe border border-safe/30">ALIGNED</span>
                        </div>
                        <div className="text-xs font-mono text-muted-foreground">{signal.reason}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex gap-3 p-3 bg-background border border-border rounded-lg text-sm items-center">
                    <CheckCircle2 className="size-4 text-safe shrink-0" />
                    <div className="text-xs font-mono text-muted-foreground">
                      Action conformant with authorized user intent constraints. Security outcome enforced at Action Gate.
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Agent Trajectory */}
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center justify-between">
            <span>Agent Trajectory</span>
            <span className="font-mono text-[10px]">RECONSTRUCTED</span>
          </div>
          
          <div className="bg-surface border border-border rounded-xl p-6 relative">
            {/* Timeline Line */}
            <div className="absolute left-[83px] top-8 bottom-8 w-px bg-border z-0" />
            
            <div className="space-y-6 relative z-10">
              {investigation.trajectory.map((event, idx) => (
                <div key={idx} className="flex gap-4 group">
                  <div className="w-12 text-right pt-1 shrink-0">
                    <div className="text-xs font-mono text-muted-foreground">{event.time}</div>
                  </div>
                  <div className="pt-1.5 shrink-0">
                    <div className={`size-3 rounded-full border-2 bg-background ${
                      event.isTerminal && event.status === 'BLOCKED' ? 'border-danger shadow-[0_0_8px_rgba(239,68,68,0.5)]' :
                      event.isTerminal && event.status === 'REVIEW' ? 'border-warn' :
                      'border-border group-hover:border-primary transition-colors'
                    }`} />
                  </div>
                  <div className={`flex-1 pb-2 ${event.isTerminal ? '' : ''}`}>
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{event.source}</div>
                    <div className={`text-sm ${
                      event.isTerminal && event.status === 'BLOCKED' ? 'font-bold text-danger' : 
                      event.isTerminal && event.status === 'REVIEW' ? 'font-bold text-warn' : 
                      'font-medium'
                    }`}>
                      {event.source === 'USER INTENT' ? <span className="font-mono bg-surface-raised px-1 py-0.5 rounded">{event.description}</span> : event.description}
                    </div>
                    {event.details && (
                      <div className="mt-2 space-y-1">
                        {event.details.map((detail, dIdx) => (
                          <div key={dIdx} className="text-xs font-mono text-muted-foreground bg-background px-2 py-1 rounded border border-border/50 inline-block mr-2">
                            {detail}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Evidence & Cross-links */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Policy Evaluation summary */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Policy Evaluation</div>
            <div className="bg-surface border border-border rounded-xl overflow-hidden">
              <div className="divide-y divide-border">
                {investigation.policiesTriggered.map((policy, idx) => (
                  <div key={idx} className="p-3 flex items-center justify-between text-sm">
                    <div className="font-medium truncate">{policy.name}</div>
                    <div className={`text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded border ${
                      policy.decision === 'BLOCK' ? 'bg-danger/10 text-danger border-danger/20' : 'bg-warn/10 text-warn border-warn/20'
                    }`}>
                      {policy.decision}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-3 bg-surface-raised border-t border-border flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Final policy decision: BLOCK</span>
                <Link to="/app/policies" className="text-primary hover:underline flex items-center">View policies <ChevronRight className="size-3 ml-0.5" /></Link>
              </div>
            </div>
          </div>

          {/* Evidence Checklist */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Evidence Reference</div>
            <div className="space-y-2">
              {investigation.evidence.map((item, idx) => (
                <div key={idx} className="flex items-start gap-3 text-sm p-2 hover:bg-surface rounded-md group">
                  <div className="font-mono text-muted-foreground text-xs pt-0.5">{item.id}</div>
                  <div className="flex-1">
                    <div className="text-xs text-muted-foreground mb-0.5">{item.type}</div>
                    <div className="font-mono truncate group-hover:text-primary transition-colors cursor-pointer">{item.description}</div>
                  </div>
                  <LinkIcon className="size-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Action Links Context */}
        <div className="pt-4 border-t border-border flex flex-wrap gap-3">
          <Button variant="outline" size="sm" className="bg-surface-raised" asChild>
            <Link to="/app/agents">
              <Terminal className="size-4 mr-2" />
              View Agent Profile
            </Link>
          </Button>
          {investigation.paymentId && (
            <Button variant="outline" size="sm" className="bg-surface-raised" asChild>
              <Link to="/app/payments">
                <CreditCard className="size-4 mr-2 text-safe" />
                View Transaction
              </Link>
            </Button>
          )}
          {investigation.orderId && (
            <Button variant="outline" size="sm" className="bg-surface-raised" asChild>
              <Link to="/app/orders">
                <ShoppingCart className="size-4 mr-2 text-muted-foreground" />
                View Order
              </Link>
            </Button>
          )}
        </div>

      </div>
    </div>
  );
}
