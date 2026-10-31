import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { 
  ShieldAlert, ShieldCheck, Download, Filter,
  ArrowRight, XCircle, AlertTriangle, CheckCircle2, MoreHorizontal, Activity, Bot, Shield, Clock, Search, Eye, ChevronRight, Check
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { approvalsApi, ApprovalRequest, GateDecisionListItem } from "@/api/approvals";
import { agentsApi } from "@/api/agents";
import { format } from "date-fns";
import { useAuth } from "@/lib/auth-context";
import { GateDecisionDrawer } from "@/components/gate/GateDecisionDrawer";

export const Route = createFileRoute("/app/approvals")({
  component: ApprovalsCenterPage,
});

function ApprovalsCenterPage() {
  const queryClient = useQueryClient();
  const [inspectDecisionId, setInspectDecisionId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<'gate_decisions' | 'approvals'>('gate_decisions');
  const [confirmAction, setConfirmAction] = useState<{ id: string; type: 'APPROVE' | 'REJECT' } | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const { workspace } = useAuth();

  const { data: approvals = [], isLoading: isLoadingApprovals, refetch: refetchApprovals } = useQuery({
    queryKey: ['approvals', workspace?.id],
    queryFn: () => approvalsApi.getApprovals(workspace?.id || ""),
    enabled: !!workspace?.id,
  });

  const { data: gateDecisions = [], isLoading: isLoadingDecisions, refetch: refetchDecisions } = useQuery({
    queryKey: ['gate-decisions', workspace?.id],
    queryFn: () => approvalsApi.listGateDecisions({ limit: 50 }),
    enabled: !!workspace?.id,
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approvalsApi.decide(id, "APPROVED", "Approved via Approvals Center UI"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', workspace?.id] });
      queryClient.invalidateQueries({ queryKey: ['gate-decisions', workspace?.id] });
      setConfirmAction(null);
      refetchApprovals();
      refetchDecisions();
    }
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => 
      approvalsApi.decide(id, "REJECTED", reason || "Rejected via Approvals Center UI"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals', workspace?.id] });
      queryClient.invalidateQueries({ queryKey: ['gate-decisions', workspace?.id] });
      setConfirmAction(null);
      setRejectReason("");
      refetchApprovals();
      refetchDecisions();
    }
  });

  const pendingApprovals = approvals.filter(a => a.status === 'PENDING');
  const pastApprovals = approvals.filter(a => a.status !== 'PENDING');

  const getDecisionBadge = (decision?: string) => {
    const upper = (decision || "").toUpperCase();
    switch (upper) {
      case 'ALLOW':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-safe/10 text-safe border border-safe/20 flex items-center gap-1"><ShieldCheck className="size-3" /> ALLOW</span>;
      case 'REVIEW':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-warn/10 text-warn border border-warn/20 flex items-center gap-1"><AlertTriangle className="size-3" /> REVIEW</span>;
      case 'BLOCK':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-danger/10 text-danger border border-danger/20 flex items-center gap-1"><ShieldAlert className="size-3" /> BLOCK</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-highlight text-muted-foreground border border-border">{upper || 'N/A'}</span>;
    }
  };

  const getApprovalStatusBadge = (status?: string | null) => {
    switch (status) {
      case 'PENDING': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-warn/10 text-warn border border-warn/20 flex items-center gap-1.5"><Clock className="size-3" /> Pending Review</span>;
      case 'APPROVED': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-safe/10 text-safe border border-safe/20 flex items-center gap-1.5"><CheckCircle2 className="size-3" /> Approved</span>;
      case 'REJECTED': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-danger/10 text-danger border border-danger/20 flex items-center gap-1.5"><XCircle className="size-3" /> Rejected</span>;
      case 'CONSUMED': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 flex items-center gap-1.5"><CheckCircle2 className="size-3" /> Consumed</span>;
      case 'EXPIRED': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1.5"><Clock className="size-3" /> Expired</span>;
      case 'CANCELLED': return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-highlight text-muted-foreground border border-border">Cancelled</span>;
      default: return status ? <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-highlight text-muted-foreground border border-border">{status}</span> : <span className="text-muted-foreground text-xs font-mono">Not Required</span>;
    }
  };

  const getAgentName = (id?: string | null) => {
    if (!id) return "Unknown Agent";
    return agents.find(a => a.id === id)?.name || id;
  };

  const filteredDecisions = gateDecisions.filter(d => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      d.id.toLowerCase().includes(q) ||
      (d.agent_name && d.agent_name.toLowerCase().includes(q)) ||
      (d.tool_name && d.tool_name.toLowerCase().includes(q)) ||
      (d.explanation && d.explanation.toLowerCase().includes(q)) ||
      (d.decision && d.decision.toLowerCase().includes(q)) ||
      (d.reason_codes && d.reason_codes.some(c => c.toLowerCase().includes(q)))
    );
  });

  const filteredApprovals = pastApprovals.filter(a => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.id.toLowerCase().includes(q) ||
      (a.reason && a.reason.toLowerCase().includes(q)) ||
      (a.status && a.status.toLowerCase().includes(q)) ||
      (a.gate_decision_id && a.gate_decision_id.toLowerCase().includes(q))
    );
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2 flex items-center gap-2">
            <Shield className="size-7 text-primary" />
            Action Gate & Approvals
          </h1>
          <p className="text-muted-foreground font-medium">
            Inspect autonomous agent gate decisions and resolve manual approval requests.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative w-72">
             <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
             <Input 
               placeholder="Search by ID, agent, code..." 
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               className="pl-9 bg-background" 
             />
          </div>
        </div>
      </div>

      {/* 2. KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Clock className="size-16" />
          </div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Pending Reviews Required</div>
          <div className="text-4xl font-bold font-mono text-foreground mb-1">
            {pendingApprovals.length}
          </div>
          {pendingApprovals.length > 0 ? (
            <div className="text-sm text-warn font-medium flex items-center gap-1">
              <AlertTriangle className="size-3.5" /> Requires manual review
            </div>
          ) : (
            <div className="text-sm text-safe font-medium flex items-center gap-1">
              <ShieldCheck className="size-3.5" /> All pending actions resolved
            </div>
          )}
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Gate Decisions Evaluated</div>
          <div className="text-4xl font-bold font-mono text-foreground mb-1">{gateDecisions.length}</div>
          <div className="text-sm text-muted-foreground font-medium">Deterministic policy & risk evaluations</div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Historical Reviews Processed</div>
          <div className="text-4xl font-bold font-mono text-foreground mb-1">{pastApprovals.length}</div>
          <div className="text-sm text-muted-foreground font-medium">Resolved human approvals & rejections</div>
        </Card>
      </div>

      {/* 3. Action Required (Pending Approvals) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            Action Required
            <span className={`text-xs py-0.5 px-2 rounded-full font-mono ${
              pendingApprovals.length > 0 ? "bg-warn/20 text-warn" : "bg-surface-highlight text-muted-foreground"
            }`}>
              {pendingApprovals.length}
            </span>
          </h3>
          {pendingApprovals.length === 0 && (
            <span className="text-xs text-muted-foreground">Action Gate actively monitoring agent execution</span>
          )}
        </div>
        
        {pendingApprovals.length === 0 ? (
          <Card className="p-8 border-dashed border-border bg-transparent flex flex-col items-center justify-center text-center">
            <div className="size-12 rounded-full bg-safe/10 text-safe flex items-center justify-center mb-3 border border-safe/20">
              <ShieldCheck className="size-6" />
            </div>
            <h4 className="text-base font-semibold text-foreground mb-1">Zero Pending Approvals Required</h4>
            <p className="text-sm text-muted-foreground max-w-md">
              There are currently no agent actions requiring manual approval. Historical Action Gate evaluations ({gateDecisions.length}) and past review decisions ({pastApprovals.length}) are listed below.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {pendingApprovals.map(approval => (
              <Card key={approval.id} className="p-0 overflow-hidden border-warn/30 bg-surface shadow-sm hover:border-warn/50 transition-colors">
                <div className="p-5 flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
                  
                  {/* Info */}
                  <div className="flex items-start gap-4 flex-1">
                    <div className="size-10 rounded-full bg-warn/10 flex items-center justify-center shrink-0 border border-warn/20 text-warn">
                      <AlertTriangle className="size-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-semibold text-foreground">{getAgentName(approval.agent_id)}</span>
                        {getApprovalStatusBadge(approval.status)}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                        {approval.reason}
                      </p>
                      
                      <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono text-muted-foreground mt-2">
                        <div className="flex items-center gap-1.5">
                           <Clock className="size-3" />
                           {format(new Date(approval.created_at), 'MMM d, h:mm:ss a')}
                        </div>
                        {approval.amount !== undefined && approval.amount !== null && (
                           <div className="flex items-center gap-1.5 font-semibold text-foreground bg-surface-highlight px-2 py-0.5 rounded">
                             {approval.currency === 'INR' ? '₹' : (approval.currency === 'USD' ? '$' : `${approval.currency} `)}{approval.amount.toLocaleString()}
                           </div>
                        )}
                        <div className="flex items-center gap-1 bg-surface-highlight px-2 py-0.5 rounded text-foreground">
                          ID: <span className="font-semibold">{approval.id}</span>
                        </div>
                        {approval.gate_decision_id && (
                          <div 
                            onClick={() => setInspectDecisionId(approval.gate_decision_id)}
                            className="flex items-center gap-1 bg-surface-highlight px-2 py-0.5 rounded text-primary hover:underline cursor-pointer"
                            title="Click to view underlying Gate Decision"
                          >
                            Gate: <span className="font-semibold">{approval.gate_decision_id.slice(0, 14)}...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col sm:flex-row items-center gap-2.5 w-full md:w-auto mt-4 md:mt-0 pt-4 md:pt-0 border-t border-border md:border-0">
                     
                     {confirmAction?.id === approval.id ? (
                       <div className="flex items-center gap-2 bg-background p-2 rounded-lg border border-border">
                         {confirmAction.type === 'APPROVE' ? (
                           <>
                             <span className="text-xs font-medium text-foreground">Confirm Approve?</span>
                             <Button 
                               size="sm" 
                               className="bg-safe hover:bg-safe/90 text-white text-xs h-7 px-2"
                               disabled={approveMutation.isPending}
                               onClick={() => approveMutation.mutate(approval.id)}
                             >
                               {approveMutation.isPending ? "Approving..." : "Yes, Approve"}
                             </Button>
                             <Button 
                               size="sm" 
                               variant="ghost" 
                               className="text-xs h-7 px-2"
                               onClick={() => setConfirmAction(null)}
                             >
                               Cancel
                             </Button>
                           </>
                         ) : (
                           <>
                             <Input 
                               placeholder="Reason..." 
                               value={rejectReason}
                               onChange={(e) => setRejectReason(e.target.value)}
                               className="h-7 text-xs w-36 bg-background"
                             />
                             <Button 
                               size="sm" 
                               className="bg-danger hover:bg-danger/90 text-white text-xs h-7 px-2"
                               disabled={rejectMutation.isPending}
                               onClick={() => rejectMutation.mutate({ id: approval.id, reason: rejectReason })}
                             >
                               {rejectMutation.isPending ? "Rejecting..." : "Yes, Reject"}
                             </Button>
                             <Button 
                               size="sm" 
                               variant="ghost" 
                               className="text-xs h-7 px-2"
                               onClick={() => setConfirmAction(null)}
                             >
                               Cancel
                             </Button>
                           </>
                         )}
                       </div>
                     ) : (
                       <>
                         <Button 
                            variant="outline" 
                            size="sm"
                            className="w-full sm:w-auto bg-background hover:bg-surface-highlight text-xs border-border"
                            onClick={() => setInspectDecisionId(approval.gate_decision_id || approval.id)}
                         >
                           <Eye className="size-3.5 mr-1.5 text-primary" />
                           Inspect Decision
                         </Button>
                         <Button 
                            variant="outline" 
                            size="sm"
                            className="w-full sm:w-auto bg-background hover:bg-danger/10 hover:text-danger hover:border-danger/30 transition-colors text-xs"
                            onClick={() => setConfirmAction({ id: approval.id, type: 'REJECT' })}
                         >
                           <XCircle className="size-3.5 mr-1.5" />
                           Reject
                         </Button>
                         <Button 
                            size="sm"
                            className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-primary-foreground text-xs"
                            onClick={() => setConfirmAction({ id: approval.id, type: 'APPROVE' })}
                         >
                           <CheckCircle2 className="size-3.5 mr-1.5" />
                           Approve
                         </Button>
                       </>
                     )}

                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 4. Recent Decisions Table */}
      <div className="space-y-4 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Recent Decisions</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Click any row or decision identifier to open the full Action Gate evidence verification drawer.
            </p>
          </div>

          {/* Toggle View */}
          <div className="flex items-center gap-1 bg-surface-highlight p-1 rounded-lg border border-border text-xs">
            <button
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                activeTab === 'gate_decisions'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab('gate_decisions')}
            >
              Action Gate Decisions ({gateDecisions.length})
            </button>
            <button
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                activeTab === 'approvals'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab('approvals')}
            >
              Approval History ({pastApprovals.length})
            </button>
          </div>
        </div>
        
        {/* Table */}
        <div className="rounded-md border border-border bg-surface overflow-hidden shadow-sm">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-highlight text-muted-foreground border-b border-border text-xs uppercase tracking-wider">
              {activeTab === 'gate_decisions' ? (
                <tr>
                  <th className="px-4 py-3 font-semibold">Decision ID</th>
                  <th className="px-4 py-3 font-semibold">Gate Decision</th>
                  <th className="px-4 py-3 font-semibold">Approval State</th>
                  <th className="px-4 py-3 font-semibold">Agent & Action</th>
                  <th className="px-4 py-3 font-semibold">Reason Codes</th>
                  <th className="px-4 py-3 font-semibold">Amount</th>
                  <th className="px-4 py-3 font-semibold">Evaluated At</th>
                  <th className="px-4 py-3 font-semibold text-right">Actions</th>
                </tr>
              ) : (
                <tr>
                  <th className="px-4 py-3 font-semibold">Approval ID</th>
                  <th className="px-4 py-3 font-semibold">Approval Status</th>
                  <th className="px-4 py-3 font-semibold">Agent</th>
                  <th className="px-4 py-3 font-semibold">Reason</th>
                  <th className="px-4 py-3 font-semibold">Amount</th>
                  <th className="px-4 py-3 font-semibold">Resolved At</th>
                  <th className="px-4 py-3 font-semibold text-right">Actions</th>
                </tr>
              )}
            </thead>
            <tbody className="divide-y divide-border">
              {activeTab === 'gate_decisions' ? (
                filteredDecisions.map(item => (
                  <tr 
                    key={item.id} 
                    className="hover:bg-surface-highlight/70 transition-colors cursor-pointer group"
                    onClick={() => setInspectDecisionId(item.id)}
                    title="Click row to inspect decision and evidence provenance"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-primary font-medium select-all">
                      <button 
                        onClick={(e) => { e.stopPropagation(); setInspectDecisionId(item.id); }}
                        className="hover:underline text-left"
                      >
                        {item.id}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getDecisionBadge(item.decision)}
                      {item.decision === 'ALLOW' && item.consumed_at && (
                        <div className="text-[10px] text-primary font-mono mt-0.5">Executed Nonce</div>
                      )}
                      {item.decision === 'REVIEW' && item.approval_status === 'CONSUMED' && (
                        <div className="text-[10px] text-muted-foreground font-mono mt-0.5">Gated · Resolved</div>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {(() => {
                        let status = item.approval_status;
                        // An executed, consumed decision must never show PENDING
                        if (item.consumed_at && (!status || status === 'PENDING')) {
                          status = 'CONSUMED';
                        } else if (item.decision === 'ALLOW' && (!status || status === 'PENDING')) {
                          status = item.consumed_at ? 'CONSUMED' : (item.approval_id ? 'APPROVED' : null);
                        } else if (!status) {
                          if (item.required_approval || item.decision === 'REVIEW') {
                            status = 'PENDING';
                          }
                        }
                        if (status) {
                          return getApprovalStatusBadge(status);
                        }
                        return <span className="text-xs text-muted-foreground font-mono">Not Required</span>;
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground flex items-center gap-1.5">
                        <Bot className="size-3.5 text-muted-foreground" />
                        <span>{item.agent_name || item.agent_id}</span>
                      </div>
                      <div className="text-xs font-mono text-primary mt-0.5">
                        {item.tool_name || item.agent_action_id}
                      </div>
                    </td>
                    <td className="px-4 py-3 max-w-[260px]">
                      {item.reason_codes && item.reason_codes.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {item.reason_codes.map((code, idx) => (
                            <span key={idx} className="font-mono text-[10px] px-1.5 py-0.5 bg-surface-highlight rounded border border-border text-foreground font-medium">
                              {code}
                            </span>
                          ))}
                        </div>
                      ) : item.explanation ? (
                        <span className="text-xs text-muted-foreground truncate block" title={item.explanation}>
                          {item.explanation}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-foreground whitespace-nowrap">
                      {item.amount !== undefined && item.amount !== null 
                        ? `${item.currency === 'INR' ? '₹' : (item.currency === 'USD' ? '$' : `${item.currency} `)}${item.amount.toLocaleString()}`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                      {item.created_at ? format(new Date(item.created_at), 'MMM d, h:mm a') : '-'}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs px-2 text-primary hover:text-primary hover:bg-primary/10"
                        onClick={(e) => {
                          e.stopPropagation();
                          setInspectDecisionId(item.id);
                        }}
                      >
                        Inspect <ChevronRight className="size-3.5 ml-1" />
                      </Button>
                    </td>
                  </tr>
                ))
              ) : (
                filteredApprovals.map(approval => (
                  <tr 
                    key={approval.id} 
                    className="hover:bg-surface-highlight/70 transition-colors cursor-pointer group"
                    onClick={() => setInspectDecisionId(approval.gate_decision_id || approval.id)}
                    title="Click row to inspect decision and evidence provenance"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-primary font-medium select-all">
                      <button 
                        onClick={(e) => { e.stopPropagation(); setInspectDecisionId(approval.gate_decision_id || approval.id); }}
                        className="hover:underline text-left"
                      >
                        {approval.id}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getApprovalStatusBadge(approval.status)}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground flex items-center gap-2">
                      <Bot className="size-3.5 text-muted-foreground" />
                      {getAgentName(approval.agent_id)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground max-w-[280px] truncate" title={approval.reason}>
                      {approval.reason}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-foreground whitespace-nowrap">
                      {approval.amount !== undefined && approval.amount !== null 
                        ? `${approval.currency === 'INR' ? '₹' : (approval.currency === 'USD' ? '$' : `${approval.currency} `)}${approval.amount.toLocaleString()}`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                      {approval.updated_at ? format(new Date(approval.updated_at), 'MMM d, h:mm a') : '-'}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs px-2 text-primary hover:text-primary hover:bg-primary/10"
                        onClick={(e) => {
                          e.stopPropagation();
                          setInspectDecisionId(approval.gate_decision_id || approval.id);
                        }}
                      >
                        Inspect <ChevronRight className="size-3.5 ml-1" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
              
              {((activeTab === 'gate_decisions' && filteredDecisions.length === 0) || 
                (activeTab === 'approvals' && filteredApprovals.length === 0)) && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-muted-foreground">
                    No decisions found matching your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decision Detail Drawer */}
      <GateDecisionDrawer 
        decisionId={inspectDecisionId} 
        onClose={() => setInspectDecisionId(null)}
        onDecisionUpdated={() => {
          refetchApprovals();
          refetchDecisions();
        }}
      />
      
    </div>
  );
}
