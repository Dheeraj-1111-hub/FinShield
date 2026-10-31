import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  X, ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, XCircle, 
  Clock, Bot, FileText, Scale, CreditCard, ShoppingBag, Copy, Check,
  ExternalLink, ChevronDown, ChevronRight, Info, Shield, ArrowUpRight,
  Lock, RefreshCw
} from "lucide-react";
import { approvalsApi, GateDecisionDetail } from "@/api/approvals";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { format } from "date-fns";

interface GateDecisionDrawerProps {
  decisionId: string | null;
  onClose: () => void;
  onDecisionUpdated?: () => void;
}

export function GateDecisionDrawer({ decisionId, onClose, onDecisionUpdated }: GateDecisionDrawerProps) {
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>("approval");
  const [actionConfirm, setActionConfirm] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: decision, isLoading, error, refetch } = useQuery({
    queryKey: ['gate-decision-detail', decisionId],
    queryFn: () => approvalsApi.getGateDecision(decisionId!),
    enabled: !!decisionId,
  });

  const decideMutation = useMutation({
    mutationFn: async ({ approvalId, decisionType, reason }: { approvalId: string; decisionType: 'APPROVED' | 'REJECTED'; reason?: string }) => {
      return await approvalsApi.decide(approvalId, decisionType, reason);
    },
    onSuccess: () => {
      setActionConfirm(null);
      setRejectReason("");
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ['gate-decision-detail', decisionId] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['gate-decisions'] });
      refetch();
      if (onDecisionUpdated) {
        onDecisionUpdated();
      }
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.error?.message || err.message || "Action failed");
    }
  });

  if (!decisionId) return null;

  const copyId = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleSection = (section: string) => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  const isPendingApproval = decision?.approval?.status === 'PENDING';
  const isTerminalApproval = decision?.approval && decision.approval.status !== 'PENDING';

  const getDecisionBadge = (res: string) => {
    const upper = (res || "").toUpperCase();
    if (upper === "ALLOW") {
      return (
        <span className="px-3 py-1 rounded-full text-xs font-bold bg-safe/10 text-safe border border-safe/30 flex items-center gap-1.5 shadow-sm">
          <ShieldCheck className="size-4" /> ALLOW
        </span>
      );
    }
    if (upper === "REVIEW") {
      return (
        <span className="px-3 py-1 rounded-full text-xs font-bold bg-warn/10 text-warn border border-warn/30 flex items-center gap-1.5 shadow-sm">
          <AlertTriangle className="size-4" /> REVIEW REQUIRED
        </span>
      );
    }
    if (upper === "BLOCK") {
      return (
        <span className="px-3 py-1 rounded-full text-xs font-bold bg-danger/10 text-danger border border-danger/30 flex items-center gap-1.5 shadow-sm">
          <ShieldAlert className="size-4" /> BLOCKED
        </span>
      );
    }
    return (
      <span className="px-3 py-1 rounded-full text-xs font-bold bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1.5">
        <Shield className="size-4" /> {upper}
      </span>
    );
  };

  const getApprovalStatusBadge = (status?: string | null) => {
    switch (status) {
      case "PENDING":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-warn/10 text-warn border border-warn/30 flex items-center gap-1"><Clock className="size-3" /> PENDING REVIEW</span>;
      case "APPROVED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-safe/10 text-safe border border-safe/30 flex items-center gap-1"><CheckCircle2 className="size-3" /> APPROVED</span>;
      case "REJECTED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-danger/10 text-danger border border-danger/30 flex items-center gap-1"><XCircle className="size-3" /> REJECTED</span>;
      case "CONSUMED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/30 flex items-center gap-1"><CheckCircle2 className="size-3" /> CONSUMED</span>;
      case "EXPIRED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1"><Clock className="size-3" /> EXPIRED</span>;
      case "CANCELLED":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-highlight text-muted-foreground border border-border">CANCELLED</span>;
      default:
        return status ? <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-highlight text-muted-foreground border border-border">{status}</span> : null;
    }
  };

  const getEvidenceStatusBadge = (status?: string) => {
    switch (status) {
      case "AVAILABLE":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-safe/10 text-safe border border-safe/20 flex items-center gap-1"><CheckCircle2 className="size-3" /> Available</span>;
      case "CHECK_FAILED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-danger/10 text-danger border border-danger/20 flex items-center gap-1"><XCircle className="size-3" /> Check Failed</span>;
      case "NOT_CONFIGURED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1"><Info className="size-3" /> Not Configured</span>;
      case "MISSING":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-warn/10 text-warn border border-warn/20 flex items-center gap-1"><AlertTriangle className="size-3" /> Missing Record</span>;
      case "NOT_REQUIRED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1">Not Required</span>;
      case "NONE_LINKED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-highlight text-muted-foreground border border-border flex items-center gap-1">None Linked</span>;
      case "SNAPSHOT_ONLY":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">Snapshot Only</span>;
      default:
        return status ? <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-highlight text-muted-foreground border border-border">{status}</span> : null;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[640px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Drawer Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-2">
          <Shield className="size-4 text-primary" />
          <span className="font-semibold text-sm tracking-wide text-foreground">ACTION GATE DECISION & EVIDENCE</span>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      {isLoading && (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
          <div className="animate-spin size-8 border-2 border-primary border-t-transparent rounded-full mb-4" />
          <p className="text-sm font-medium">Retrieving Action Gate decision & evidence provenance...</p>
        </div>
      )}

      {error && (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <div className="size-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mb-4 border border-danger/20">
            <XCircle className="size-6" />
          </div>
          <h4 className="font-semibold text-foreground mb-1">Decision Not Found or Forbidden</h4>
          <p className="text-sm text-muted-foreground max-w-sm mb-4">
            {(error as any)?.response?.data?.error?.message || "Could not retrieve decision details for this ID."}
          </p>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </div>
      )}

      {decision && (
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          
          {/* Hero Section */}
          <div className="p-6 border-b border-border bg-gradient-to-b from-surface/50 to-transparent">
            
            <div className="flex items-center justify-between gap-4 mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-muted-foreground select-all">{decision.id}</span>
                <button 
                  onClick={() => copyId(decision.id)} 
                  className="text-muted-foreground hover:text-foreground transition-colors p-1"
                  title="Copy Decision ID"
                >
                  {copied ? <Check className="size-3.5 text-safe" /> : <Copy className="size-3.5" />}
                </button>
              </div>
              <div className="flex items-center gap-2">
                {getDecisionBadge(decision.decision)}
              </div>
            </div>

            {/* Amount / Currency if applicable */}
            {decision.amount !== null && decision.amount !== undefined && (
              <div className="mb-4">
                <div className="text-3xl font-bold tracking-tight text-foreground font-mono">
                  {decision.currency === 'INR' ? '₹' : (decision.currency === 'USD' ? '$' : `${decision.currency} `)}
                  {decision.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                  Action Transaction Value
                </div>
              </div>
            )}

            {/* Explanation box */}
            {decision.explanation && (
              <div className={`p-3.5 rounded-lg border text-sm mb-4 ${
                decision.decision === 'BLOCK' ? 'bg-danger/10 border-danger/20 text-danger' :
                decision.decision === 'REVIEW' ? 'bg-warn/10 border-warn/20 text-warn' :
                'bg-safe/10 border-safe/20 text-safe'
              }`}>
                <div className="font-semibold text-xs uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <Info className="size-3.5" />
                  Decision Reason & Explanation
                </div>
                <div className="text-sm text-foreground/90">{decision.explanation}</div>
              </div>
            )}

            {/* Reason codes */}
            {decision.reason_codes && decision.reason_codes.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 mt-2">
                <span className="text-xs text-muted-foreground mr-1">Policy / Risk Codes:</span>
                {decision.reason_codes.map((code, idx) => (
                  <span 
                    key={idx} 
                    className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-highlight border border-border text-foreground font-medium"
                  >
                    {code}
                  </span>
                ))}
              </div>
            )}

            {/* Metadata pills */}
            <div className="grid grid-cols-2 gap-3 mt-4 text-xs text-muted-foreground bg-surface/80 p-3 rounded-lg border border-border">
              <div>
                <span className="font-medium text-foreground">Evaluated At:</span>{' '}
                {decision.created_at ? format(new Date(decision.created_at), 'MMM d, yyyy, h:mm:ss a') : '-'}
              </div>
              <div>
                <span className="font-medium text-foreground">Approval Required:</span>{' '}
                {decision.required_approval || decision.decision === 'REVIEW' || decision.approval_id || decision.approval ? (
                  <span className="text-foreground font-semibold">YES</span>
                ) : (
                  <span className="text-muted-foreground font-semibold">NO</span>
                )}
              </div>
              <div>
                <span className="font-medium text-foreground">Approval Lifecycle:</span>{' '}
                {decision.approval?.status ? (
                  getApprovalStatusBadge(decision.approval.status)
                ) : (decision.required_approval || decision.decision === 'REVIEW') ? (
                  getApprovalStatusBadge('PENDING')
                ) : (
                  <span className="text-muted-foreground font-mono">Not Required</span>
                )}
              </div>
              <div>
                <span className="font-medium text-foreground">Gate Execution:</span>{' '}
                {(() => {
                  if (decision.decision === 'ALLOW') {
                    if (decision.consumed_at) {
                      return (
                        <span className="text-primary font-semibold flex items-center gap-1">
                          <CheckCircle2 className="size-3" />
                          CONSUMED ({format(new Date(decision.consumed_at), 'h:mm a')})
                        </span>
                      );
                    }
                    if (decision.valid_until && new Date(decision.valid_until) < new Date()) {
                      return (
                        <span className="text-muted-foreground font-semibold flex items-center gap-1">
                          <Clock className="size-3" />
                          EXPIRED (UNCONSUMED)
                        </span>
                      );
                    }
                    return (
                      <span className="text-safe font-semibold flex items-center gap-1">
                        <ShieldCheck className="size-3" />
                        AUTHORIZED (UNCONSUMED)
                      </span>
                    );
                  }
                  if (decision.decision === 'REVIEW') {
                    if (decision.approval?.status === 'CONSUMED') {
                      return (
                        <span className="text-foreground font-semibold flex items-center gap-1">
                          <Lock className="size-3 text-primary" />
                          GATED (Resolved via Post-Approval ALLOW)
                        </span>
                      );
                    }
                    if (decision.approval?.status === 'APPROVED') {
                      return (
                        <span className="text-safe font-semibold flex items-center gap-1">
                          <CheckCircle2 className="size-3" />
                          GATED (Approved — Awaiting ALLOW)
                        </span>
                      );
                    }
                    if (decision.approval?.status === 'REJECTED') {
                      return (
                        <span className="text-danger font-semibold flex items-center gap-1">
                          <XCircle className="size-3" />
                          GATED (Blocked by Reviewer)
                        </span>
                      );
                    }
                    return (
                      <span className="text-warn font-semibold flex items-center gap-1">
                        <Clock className="size-3" />
                        PAUSED (Awaiting Human Review)
                      </span>
                    );
                  }
                  return (
                    <span className="text-danger font-semibold flex items-center gap-1">
                      <ShieldAlert className="size-3" />
                      NON-EXECUTABLE (Blocked)
                    </span>
                  );
                })()}
              </div>
            </div>

          </div>

          {/* Pending Approval Interactive Action Banner */}
          {isPendingApproval && decision.approval && (
            <div className="p-4 bg-warn/10 border-b border-warn/30">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-warn flex items-center gap-2 text-sm mb-1">
                    <AlertTriangle className="size-4" />
                    Human Approval Required
                  </div>
                  <p className="text-xs text-foreground/90 max-w-md">
                    This action is currently paused in the Action Gate awaiting manual resolution. Approving permits a one-time execution nonce; rejecting blocks execution permanently.
                  </p>
                </div>
              </div>

              {actionError && (
                <div className="mt-3 p-2.5 bg-danger/10 border border-danger/30 rounded text-xs text-danger">
                  {actionError}
                </div>
              )}

              {/* Confirmation State */}
              {actionConfirm === 'APPROVE' ? (
                <div className="mt-3 p-3 bg-surface rounded-lg border border-border space-y-2">
                  <div className="text-xs font-semibold text-foreground">
                    Confirm Approval
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Are you sure you want to approve this action? This will issue an authorized gate execution token.
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <Button 
                      size="sm" 
                      className="bg-safe hover:bg-safe/90 text-white text-xs h-8"
                      disabled={decideMutation.isPending}
                      onClick={() => decideMutation.mutate({
                        approvalId: decision.approval!.id,
                        decisionType: 'APPROVED',
                        reason: 'Approved via Action Gate detail drawer'
                      })}
                    >
                      {decideMutation.isPending ? "Approving..." : "Yes, Approve Action"}
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="text-xs h-8"
                      onClick={() => setActionConfirm(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : actionConfirm === 'REJECT' ? (
                <div className="mt-3 p-3 bg-surface rounded-lg border border-border space-y-2">
                  <div className="text-xs font-semibold text-danger">
                    Confirm Rejection
                  </div>
                  <Input 
                    placeholder="Enter reason for rejection (optional)..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="text-xs h-8 bg-background"
                  />
                  <div className="flex items-center gap-2 pt-1">
                    <Button 
                      size="sm" 
                      className="bg-danger hover:bg-danger/90 text-white text-xs h-8"
                      disabled={decideMutation.isPending}
                      onClick={() => decideMutation.mutate({
                        approvalId: decision.approval!.id,
                        decisionType: 'REJECTED',
                        reason: rejectReason || 'Rejected via Action Gate detail drawer'
                      })}
                    >
                      {decideMutation.isPending ? "Rejecting..." : "Yes, Reject Action"}
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="text-xs h-8"
                      onClick={() => setActionConfirm(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2.5 mt-3">
                  <Button 
                    size="sm" 
                    className="bg-safe hover:bg-safe/90 text-white text-xs h-8"
                    onClick={() => setActionConfirm('APPROVE')}
                  >
                    <CheckCircle2 className="size-3.5 mr-1.5" />
                    Approve Action
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="border-danger/30 text-danger hover:bg-danger/10 text-xs h-8"
                    onClick={() => setActionConfirm('REJECT')}
                  >
                    <XCircle className="size-3.5 mr-1.5" />
                    Reject Action
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Terminal State Banner */}
          {isTerminalApproval && decision.approval && (
            <div className="p-3.5 bg-surface-highlight border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock className="size-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium">
                  {decision.decision === 'REVIEW' ? (
                    <>
                      Review Request: <strong className="text-foreground">
                        {decision.approval.status === 'CONSUMED' 
                          ? 'APPROVED & CONSUMED' 
                          : decision.approval.status}
                      </strong> (Immutable Historical Record)
                    </>
                  ) : (
                    <>
                      Approval Token: <strong className="text-foreground">{decision.approval.status}</strong>
                      {decision.consumed_at ? ' (Executed)' : ''}
                    </>
                  )}
                </span>
              </div>
              <span className="text-[11px] text-muted-foreground font-mono">
                {decision.decision === 'REVIEW' ? 'Initial Review Decision' : 'Post-Approval Authorization'}
              </span>
            </div>
          )}

          {/* Evidence Dossier Breakdown */}
          <div className="p-6 space-y-4">
            
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold tracking-wider text-muted-foreground uppercase flex items-center gap-2">
                <Scale className="size-4 text-primary" />
                Evidence Verification & Provenance
              </h4>
              <span className="text-xs text-muted-foreground font-mono">Workspace: {decision.workspace_id}</span>
            </div>

            {/* 1. Approval Request State */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("approval")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-warn/10 text-warn flex items-center justify-center border border-warn/20">
                    <Clock className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Human Approval Record</div>
                    <div className="text-xs text-muted-foreground">Action Gate review request lifecycle</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {decision.approval ? (
                    getApprovalStatusBadge(decision.approval.status)
                  ) : (
                    getEvidenceStatusBadge(decision.evidence_status?.approval)
                  )}
                  {expandedSection === "approval" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "approval" && (
                <div className="p-4 border-t border-border bg-background space-y-3 text-xs">
                  {decision.approval ? (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-muted-foreground">Approval ID:</span>
                          <div className="font-mono text-foreground font-medium mt-0.5 select-all">{decision.approval.id}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Approval Status:</span>
                          <div className="font-semibold text-foreground mt-0.5">
                            {getApprovalStatusBadge(decision.approval.status)}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Requested By:</span>
                          <div className="text-foreground font-mono mt-0.5">{decision.approval.requested_by}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Bound Amount & Currency:</span>
                          <div className="text-foreground font-mono font-medium mt-0.5">
                            {decision.approval.amount ? `${decision.approval.currency || 'INR'} ${decision.approval.amount.toLocaleString()}` : '-'}
                          </div>
                        </div>
                        {decision.approval.approved_by && (
                          <div>
                            <span className="text-muted-foreground">Approved By:</span>
                            <div className="text-safe font-mono mt-0.5">{decision.approval.approved_by}</div>
                          </div>
                        )}
                        {decision.approval.approved_at && (
                          <div>
                            <span className="text-muted-foreground">Approved At:</span>
                            <div className="text-muted-foreground mt-0.5">{format(new Date(decision.approval.approved_at), 'MMM d, h:mm a')}</div>
                          </div>
                        )}
                        {decision.approval.rejected_by && (
                          <div>
                            <span className="text-muted-foreground">Rejected By:</span>
                            <div className="text-danger font-mono mt-0.5">{decision.approval.rejected_by}</div>
                          </div>
                        )}
                        {decision.approval.rejected_at && (
                          <div>
                            <span className="text-muted-foreground">Rejected At:</span>
                            <div className="text-muted-foreground mt-0.5">{format(new Date(decision.approval.rejected_at), 'MMM d, h:mm a')}</div>
                          </div>
                        )}
                      </div>
                      {decision.approval.reason && (
                        <div className="mt-2 p-2.5 bg-surface-highlight rounded border border-border text-muted-foreground">
                          <span className="font-medium text-foreground">Trigger Reason:</span> {decision.approval.reason}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-muted-foreground italic">
                      {decision.required_approval ? "Approval record was expected but not found in workspace." : "This gate decision did not require human approval."}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 2. Agent & Execution */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("agent")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                    <Bot className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Agent & Runtime Action</div>
                    <div className="text-xs text-muted-foreground">Autonomous actor & action identifier</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getEvidenceStatusBadge(decision.evidence_status?.agent)}
                  {expandedSection === "agent" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "agent" && (
                <div className="p-4 border-t border-border bg-background space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-muted-foreground">Agent Name:</span>
                      <div className="font-semibold text-foreground mt-0.5">{decision.agent?.name || decision.agent_id}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Agent ID:</span>
                      <div className="text-foreground mt-0.5 font-mono select-all">{decision.agent_id}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Run ID:</span>
                      <div className="font-mono text-foreground mt-0.5 select-all">{decision.agent_run_id}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Action Tool:</span>
                      <div className="font-mono text-foreground font-semibold mt-0.5 text-primary">
                        {decision.agent_action?.tool_name || decision.agent_action_id}
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Action ID:</span>
                      <div className="font-mono text-foreground mt-0.5 select-all">{decision.agent_action_id}</div>
                    </div>
                    {decision.agent_action?.alignment_result && (
                      <div>
                        <span className="text-muted-foreground">Intent Alignment:</span>
                        <div className="font-mono font-medium text-foreground mt-0.5 flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            decision.agent_action.alignment_result === 'ALIGNED' ? 'bg-safe/10 text-safe' : 'bg-danger/10 text-danger'
                          }`}>
                            {decision.agent_action.alignment_result}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {decision.agent_action?.input && (
                    <div className="mt-2">
                      <span className="text-muted-foreground font-medium">Action Input Payload:</span>
                      <pre className="mt-1 p-2.5 bg-surface-highlight rounded border border-border text-[11px] font-mono text-foreground overflow-x-auto max-h-36">
                        {JSON.stringify(decision.agent_action.input, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 3. Intent Enforcement */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("intent")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                    <FileText className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Intent & Constraints</div>
                    <div className="text-xs text-muted-foreground">User request and verified hard constraints</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getEvidenceStatusBadge(decision.evidence_status?.intent)}
                  {expandedSection === "intent" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "intent" && (
                <div className="p-4 border-t border-border bg-background space-y-3 text-xs">
                  {decision.intent ? (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-muted-foreground">Intent ID:</span>
                          <div className="font-mono text-foreground mt-0.5 select-all">{decision.intent.id}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Version:</span>
                          <div className="font-mono text-foreground mt-0.5">v{decision.intent.version}</div>
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Intent Title:</span>
                        <div className="font-semibold text-foreground mt-0.5">{decision.intent.title}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">User Natural Language Request:</span>
                        <div className="p-2.5 bg-surface-highlight rounded border border-border text-foreground italic mt-1">
                          "{decision.intent.natural_language_request}"
                        </div>
                      </div>
                      {decision.intent.structured_constraints && Object.keys(decision.intent.structured_constraints).length > 0 && (
                        <div>
                          <span className="text-muted-foreground">Structured Hard Constraints:</span>
                          <pre className="mt-1 p-2 bg-surface-highlight rounded border border-border text-[11px] font-mono text-foreground overflow-x-auto">
                            {JSON.stringify(decision.intent.structured_constraints, null, 2)}
                          </pre>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-muted-foreground italic">
                      No Intent was attached to this run or decision. Action Gate evaluated execution with unconstrained defaults.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 4. Delegated Authority */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("authority")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                    <Scale className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Delegated Authority</div>
                    <div className="text-xs text-muted-foreground">Monetary limits and prohibited capabilities</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getEvidenceStatusBadge(decision.evidence_status?.authority)}
                  {expandedSection === "authority" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "authority" && (
                <div className="p-4 border-t border-border bg-background space-y-3 text-xs">
                  {decision.authority ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-muted-foreground">Authority ID:</span>
                        <div className="font-mono text-foreground mt-0.5 select-all">{decision.authority.id}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Authority Status:</span>
                        <div className="font-semibold text-foreground mt-0.5">{decision.authority.status}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Monetary Limit:</span>
                        <div className="font-mono text-foreground mt-0.5">
                          {decision.authority.monetary_limit !== null ? `${decision.authority.currency} ${decision.authority.monetary_limit}` : 'Unlimited'}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Approval Threshold:</span>
                        <div className="font-mono text-foreground mt-0.5">
                          {decision.authority.approval_threshold !== null ? `${decision.authority.currency} ${decision.authority.approval_threshold}` : 'None'}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Authority Version:</span>
                        <div className="font-mono text-foreground mt-0.5">v{decision.authority.version}</div>
                      </div>
                      {decision.authority.prohibited_actions?.length > 0 && (
                        <div className="col-span-2">
                          <span className="text-muted-foreground">Prohibited Actions:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {decision.authority.prohibited_actions.map((act, i) => (
                              <span key={i} className="px-2 py-0.5 rounded bg-danger/10 text-danger border border-danger/20 font-mono text-[11px]">
                                {act}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-muted-foreground italic">
                      No Delegated Authority record bound to this agent or run. Default workspace limits were applied.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 5. Risk Assessment */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("risk")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                    <Shield className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Risk Assessment</div>
                    <div className="text-xs text-muted-foreground">ML scoring & real-time risk indicators</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getEvidenceStatusBadge(decision.evidence_status?.risk_assessment)}
                  {expandedSection === "risk" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "risk" && (
                <div className="p-4 border-t border-border bg-background space-y-3 text-xs">
                  {decision.risk_assessment ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-muted-foreground">Assessment ID:</span>
                        <div className="font-mono text-foreground mt-0.5 select-all">{decision.risk_assessment.id}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Risk Score:</span>
                        <div className="text-lg font-bold font-mono text-foreground mt-0.5">
                          {decision.risk_assessment.risk_score} / 100
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Risk Level:</span>
                        <div className="mt-0.5">
                          <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                            decision.risk_assessment.risk_level === 'CRITICAL' ? 'bg-danger/20 text-danger' :
                            decision.risk_assessment.risk_level === 'HIGH' ? 'bg-danger/10 text-danger' :
                            decision.risk_assessment.risk_level === 'MEDIUM' ? 'bg-warn/10 text-warn' :
                            'bg-safe/10 text-safe'
                          }`}>
                            {decision.risk_assessment.risk_level}
                          </span>
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Assessment Type:</span>
                        <div className="font-mono text-foreground mt-0.5">{decision.risk_assessment.assessment_type}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Scoring Engine:</span>
                        <div className="font-mono text-foreground mt-0.5">{decision.risk_assessment.model_version}</div>
                      </div>
                    </div>
                  ) : decision.evaluation_snapshot?.risk ? (
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground">Snapshot metrics captured at evaluation time:</div>
                      <pre className="p-2.5 bg-surface-highlight rounded border border-border text-[11px] font-mono text-foreground overflow-x-auto">
                        {JSON.stringify(decision.evaluation_snapshot.risk, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div className="text-muted-foreground italic">
                      No standalone risk assessment record was registered for this action.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 6. Linked Order & Payment */}
            <div className="border border-border rounded-lg bg-surface overflow-hidden shadow-sm">
              <div 
                className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-surface-highlight/40 transition-colors"
                onClick={() => toggleSection("commerce")}
              >
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded-md bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                    <ShoppingBag className="size-3.5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">Linked Order & Payment</div>
                    <div className="text-xs text-muted-foreground">Commerce sandbox transaction records</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {decision.order || decision.payment ? (
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-safe/10 text-safe border border-safe/20 flex items-center gap-1">
                      <CheckCircle2 className="size-3" /> Linked
                    </span>
                  ) : (
                    getEvidenceStatusBadge(decision.evidence_status?.order || "NONE_LINKED")
                  )}
                  {expandedSection === "commerce" ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
                </div>
              </div>

              {expandedSection === "commerce" && (
                <div className="p-4 border-t border-border bg-background space-y-4 text-xs">
                  {/* Order */}
                  {decision.order ? (
                    <div className="p-3 bg-surface rounded-lg border border-border space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground flex items-center gap-1.5">
                          <ShoppingBag className="size-3.5 text-primary" />
                          Order {decision.order.id}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-surface-highlight text-foreground border border-border">
                          {decision.order.status}
                        </span>
                      </div>
                      <div className="text-muted-foreground">
                        Total:{' '}
                        <span className="font-mono font-bold text-foreground">
                          {decision.order.currency === 'INR' ? '₹' : (decision.order.currency === 'USD' ? '$' : `${decision.order.currency} `)}
                          {decision.order.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      {decision.order.items && decision.order.items.length > 0 && (
                        <div className="mt-2 space-y-1">
                          <div className="text-[11px] text-muted-foreground font-medium">Order Items:</div>
                          {decision.order.items.map((item, idx) => (
                            <div key={idx} className="flex justify-between text-[11px] bg-background p-1.5 rounded border border-border">
                              <span className="text-foreground">{item.product_name} × {item.quantity}</span>
                              <span className="font-mono text-foreground font-medium">
                                {decision.order?.currency === 'INR' ? '₹' : '$'}{item.total.toLocaleString()}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}

                  {/* Payment */}
                  {decision.payment ? (
                    <div className="p-3 bg-surface rounded-lg border border-border space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground flex items-center gap-1.5">
                          <CreditCard className="size-3.5 text-primary" />
                          Payment {decision.payment.id}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          decision.payment.status === 'CAPTURED' ? 'bg-safe/10 text-safe border border-safe/20' :
                          decision.payment.status === 'FAILED' ? 'bg-danger/10 text-danger border border-danger/20' :
                          'bg-warn/10 text-warn border border-warn/20'
                        }`}>
                          {decision.payment.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-muted-foreground">Amount:</span>{' '}
                          <span className="font-mono font-semibold text-foreground">
                            {decision.payment.currency === 'INR' ? '₹' : '$'}{decision.payment.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Idempotency:</span>{' '}
                          <span className="font-mono text-foreground">{decision.payment.idempotency_key}</span>
                        </div>
                      </div>
                      {decision.payment.failure_reason && (
                        <div className="p-2 bg-danger/10 text-danger rounded border border-danger/20 text-[11px]">
                          <span className="font-semibold">Failure:</span> {decision.payment.failure_reason}
                        </div>
                      )}
                    </div>
                  ) : null}

                  {!decision.order && !decision.payment && (
                    <div className="text-muted-foreground italic">
                      No order or payment is linked to this gate decision (e.g., search, query, or pre-checkout action).
                    </div>
                  )}
                </div>
              )}
            </div>

          </div>

        </div>
      )}

      {/* Footer */}
      <div className="h-14 border-t border-border px-5 bg-surface flex items-center justify-between shrink-0">
        <span className="text-xs text-muted-foreground font-mono">FINSHIELD Trust Infrastructure</span>
        <Button variant="outline" size="sm" onClick={onClose} className="border-border">
          Close
        </Button>
      </div>

    </div>
  );
}
