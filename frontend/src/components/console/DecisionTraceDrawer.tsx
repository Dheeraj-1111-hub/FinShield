import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { agentRuntimeApi, DecisionTraceResponse } from "@/api/agent_runtime";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { 
  CheckCircle2, 
  ShieldAlert, 
  XCircle, 
  Clock, 
  ArrowRight, 
  AlertTriangle,
  Loader2,
  FileText,
  CreditCard,
  ShoppingCart,
  UserCheck,
  ShieldCheck,
  History,
  Info
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";

interface DecisionTraceDrawerProps {
  runId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DecisionTraceDrawer({ runId, isOpen, onClose }: DecisionTraceDrawerProps) {
  const { data: trace, isLoading, error } = useQuery<DecisionTraceResponse>({
    queryKey: ["agent_run_decision_trace", runId],
    queryFn: () => agentRuntimeApi.runs.getDecisionTrace(runId!),
    enabled: !!runId && isOpen,
    retry: 1,
  });

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl lg:max-w-3xl overflow-y-auto p-0 flex flex-col bg-background border-border">
        <SheetHeader className="p-6 border-b border-border bg-surface/50 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-5 text-primary" />
              <SheetTitle className="text-lg font-bold">Decision Trace & Evidence</SheetTitle>
            </div>
            {trace && (
              <Badge 
                variant="outline" 
                className={`font-mono text-xs ${
                  trace.run_status === "COMPLETED" ? "bg-safe/10 text-safe border-safe/30" :
                  trace.run_status === "FAILED" ? "bg-danger/10 text-danger border-danger/30" :
                  "bg-warn/10 text-warn border-warn/30"
                }`}
              >
                {trace.run_status}
              </Badge>
            )}
          </div>
          <SheetDescription className="font-mono text-xs text-muted-foreground mt-1">
            Run ID: {runId || "Unavailable"}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading && (
            <div className="flex flex-col items-center justify-center p-16 text-muted-foreground space-y-3">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="text-sm">Retrieving authoritative decision trace...</p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-danger/10 border border-danger/20 rounded-lg text-danger space-y-2">
              <div className="flex items-center gap-2 font-semibold text-sm">
                <AlertTriangle className="size-4 shrink-0" />
                <span>Failed to load decision trace</span>
              </div>
              <p className="text-xs opacity-90">
                {(error as any)?.response?.data?.detail || (error as any)?.message || "Decision evidence unavailable for this run."}
              </p>
            </div>
          )}

          {!isLoading && !error && !trace && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              Unavailable: No trace data found for run.
            </div>
          )}

          {trace && (() => {
            const authoritativeDecision = trace.final_gate_decision || (
              trace.run_status === "WAITING_FOR_APPROVAL" ? "REVIEW_REQUIRED" :
              trace.run_status === "BLOCKED" ? "BLOCK" :
              trace.run_status === "FAILED" ? "FAILED" :
              trace.run_status === "COMPLETED" ? "ALLOW" :
              (trace.gate_decisions && trace.gate_decisions.length > 0
                ? (trace.gate_decisions[trace.gate_decisions.length - 1].decision === "REVIEW" ? "REVIEW_REQUIRED" : trace.gate_decisions[trace.gate_decisions.length - 1].decision)
                : "NOT EVALUATED")
            );

            return (
            <>
              {/* 1. Authoritative Gate Decision Banner */}
              <div className={`p-4 rounded-lg border flex flex-col gap-2 ${
                authoritativeDecision === "ALLOW" ? "bg-safe/10 border-safe/30 text-safe" :
                authoritativeDecision === "REVIEW_REQUIRED" || authoritativeDecision === "REVIEW" ? "bg-warn/10 border-warn/30 text-warn" :
                "bg-danger/10 border-danger/30 text-danger"
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Latest Authoritative Decision</div>
                    <div className="text-xl font-bold flex items-center gap-2 mt-0.5">
                      {authoritativeDecision === "ALLOW" && <CheckCircle2 className="size-5" />}
                      {(authoritativeDecision === "REVIEW_REQUIRED" || authoritativeDecision === "REVIEW") && <ShieldAlert className="size-5" />}
                      {(authoritativeDecision === "BLOCK" || authoritativeDecision === "FAILED") && <XCircle className="size-5" />}
                      <span>{authoritativeDecision}</span>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">
                    Run: {trace.run_status.replace(/_/g, ' ')}
                  </Badge>
                </div>
                {trace.run_status === "WAITING_FOR_APPROVAL" && (
                  <div className="text-xs text-foreground/80 pt-1">
                    This run is paused waiting for manual review. Earlier evaluations (e.g. cart/checkout) were allowed, but the run cannot proceed until payment is approved.
                  </div>
                )}
                {(trace.run_status === "BLOCKED" || trace.run_status === "FAILED") && (
                  <div className="text-xs text-foreground/80 pt-1">
                    Authoritative final outcome of this run is {authoritativeDecision}. Individual step approvals from earlier actions do not override this decision.
                  </div>
                )}
              </div>

              {/* 2. Run Summary Card */}
              <Card className="bg-surface border-border">
                <CardHeader className="py-3 px-4 border-b border-border bg-background/30">
                  <CardTitle className="text-xs uppercase tracking-wider font-semibold text-muted-foreground flex items-center gap-2">
                    <Info className="size-3.5" /> Run Context
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-3 text-sm">
                  <div>
                    <span className="text-xs text-muted-foreground">Intent Input:</span>
                    <div className="mt-1 p-2 bg-background border border-border rounded text-xs font-mono">
                      {trace.input}
                    </div>
                  </div>
                  {trace.output && (
                    <div>
                      <span className="text-xs text-muted-foreground">Execution Output:</span>
                      <div className="mt-1 p-2 bg-background border border-border rounded text-xs whitespace-pre-wrap">
                        {trace.output}
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between text-xs text-muted-foreground pt-1">
                    <span>Started: {new Date(trace.created_at).toLocaleString()}</span>
                  </div>
                </CardContent>
              </Card>

              {/* 3. Action Gate Decisions (Distinguishing REVIEW_REQUIRED vs ALLOW) */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <ShieldAlert className="size-4 text-primary" /> Gate Decisions & Chronology
                </h4>
                {trace.gate_decisions.length === 0 ? (
                  <div className="p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground">
                    Unavailable: No authoritative Gate Decisions recorded for this run.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {trace.gate_decisions.map((dec, idx) => {
                      const isLatest = idx === trace.gate_decisions.length - 1;
                      const linkedAction = trace.actions.find(a => a.id === dec.agent_action_id);
                      const actionLabel = linkedAction ? `Action: ${linkedAction.tool_name}` : `Step ${idx + 1}`;

                      return (
                      <div 
                        key={dec.id} 
                        className={`p-4 rounded-lg border text-sm space-y-3 ${
                          dec.decision === "ALLOW" ? "bg-safe/5 border-safe/20" :
                          dec.decision === "REVIEW" ? "bg-warn/5 border-warn/20" :
                          "bg-danger/5 border-danger/20"
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-2">
                            {dec.decision === "ALLOW" ? <CheckCircle2 className="size-4 text-safe" /> :
                             dec.decision === "REVIEW" ? <ShieldAlert className="size-4 text-warn" /> :
                             <XCircle className="size-4 text-danger" />}
                            <span className="font-bold">{dec.decision === "REVIEW" ? "REVIEW_REQUIRED" : dec.decision}</span>
                            <span className="text-xs text-muted-foreground">({actionLabel} — {isLatest ? "Latest Evaluated" : "Earlier Step"})</span>
                          </div>
                          <span className="text-xs text-muted-foreground font-mono">{new Date(dec.created_at).toLocaleTimeString()}</span>
                        </div>

                        <div className="text-xs space-y-1">
                          <div>
                            <span className="text-muted-foreground">Decision ID: </span>
                            <span className="font-mono">{dec.id}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Explanation: </span>
                            <span>{dec.explanation || "Unavailable"}</span>
                          </div>
                          {dec.reason_codes && dec.reason_codes.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {dec.reason_codes.map((rc, rIdx) => (
                                <Badge key={rIdx} variant="outline" className="text-[10px] px-1.5 py-0">
                                  {rc}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Snapshot details: Risk, Policy, Authority */}
                        {dec.evaluation_snapshot && Object.keys(dec.evaluation_snapshot).length > 0 && (
                          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/50 text-xs">
                            <div className="bg-background/80 p-2 rounded border border-border/50">
                              <div className="text-muted-foreground text-[10px]">Policy</div>
                              <div className="font-semibold text-safe">
                                {dec.evaluation_snapshot.policy?.decision || "PASS"}
                              </div>
                            </div>
                            <div className="bg-background/80 p-2 rounded border border-border/50">
                              <div className="text-muted-foreground text-[10px]">Risk Tier / Score</div>
                              <div className="font-semibold">
                                {dec.evaluation_snapshot.risk?.level || "LOW"} 
                                {dec.evaluation_snapshot.risk?.score ? ` (${dec.evaluation_snapshot.risk.score})` : ""}
                              </div>
                            </div>
                            <div className="bg-background/80 p-2 rounded border border-border/50">
                              <div className="text-muted-foreground text-[10px]">Authority Check</div>
                              <div className="font-semibold text-safe">
                                {dec.evaluation_snapshot.authority?.status === "ACTIVE" ? "PASS" : "EXCEEDED"}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  </div>
                )}
              </div>

              {/* 3. Approvals & Human Review Evidence */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <UserCheck className="size-4 text-primary" /> Approval Linkage & Verification
                </h4>
                {trace.approvals.length === 0 ? (
                  <div className="p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground">
                    Unavailable: No approval requests bound to this run.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {trace.approvals.map((appr) => (
                      <Card key={appr.id} className="bg-surface border-border">
                        <CardContent className="p-4 space-y-2 text-xs">
                          <div className="flex justify-between items-center">
                            <span className="font-semibold text-foreground">Approval ID: {appr.id}</span>
                            <Badge 
                              variant="outline" 
                              className={`text-[10px] ${
                                appr.status === "CONSUMED" ? "bg-safe/10 text-safe border-safe/30" :
                                appr.status === "APPROVED" ? "bg-primary/10 text-primary border-primary/30" :
                                "bg-warn/10 text-warn border-warn/30"
                              }`}
                            >
                              {appr.status}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-2 pt-1 text-muted-foreground">
                            <div>
                              <span>Approved Amount: </span>
                              <strong className="text-foreground">
                                {appr.amount != null ? formatCurrency(appr.amount, appr.currency || "INR") : "Unavailable"}
                              </strong>
                            </div>
                            <div>
                              <span>Order Bound: </span>
                              <strong className="text-foreground font-mono">
                                {appr.transaction_data?.order_id || "Unavailable"}
                              </strong>
                            </div>
                            <div>
                              <span>Approver: </span>
                              <strong className="text-foreground">
                                {appr.approver_name || appr.approved_by || "Unavailable"}
                              </strong>
                            </div>
                            <div>
                              <span>Approval Timestamp: </span>
                              <strong className="text-foreground">
                                {appr.approved_at ? new Date(appr.approved_at).toLocaleString() : "Pending"}
                              </strong>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              {/* 4. Payment Execution & Orders Linkage */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <CreditCard className="size-4 text-primary" /> Payment Execution & Orders
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {trace.orders.map((ord) => (
                    <div key={ord.id} className="p-3 bg-surface border border-border rounded-lg text-xs space-y-1">
                      <div className="flex justify-between items-center font-medium">
                        <span className="font-mono">{ord.id}</span>
                        <Badge 
                          variant="outline" 
                          className={`text-[10px] ${
                            ord.status === "PAID" || ord.status === "FULFILLED" 
                              ? "text-safe bg-safe/10 border-safe/20" 
                              : ord.status === "PENDING_PAYMENT" 
                                ? "text-warn bg-warn/10 border-warn/20" 
                                : "text-danger bg-danger/10 border-danger/20"
                          }`}
                        >
                          {ord.status}
                        </Badge>
                      </div>
                      <div className="text-muted-foreground flex justify-between pt-1">
                        <span>Total:</span>
                        <span className="font-semibold text-foreground">{formatCurrency(ord.total, ord.currency)}</span>
                      </div>
                    </div>
                  ))}
                  {trace.payments.map((pmt) => (
                    <div key={pmt.id} className="p-3 bg-surface border border-border rounded-lg text-xs space-y-1">
                      <div className="flex justify-between items-center font-medium">
                        <span className="font-mono">{pmt.id}</span>
                        <Badge variant="outline" className="text-[10px] text-safe bg-safe/10 border-safe/20">{pmt.status}</Badge>
                      </div>
                      <div className="text-muted-foreground flex justify-between pt-1">
                        <span>Captured:</span>
                        <span className="font-semibold text-foreground">{formatCurrency(pmt.amount, pmt.currency)}</span>
                      </div>
                    </div>
                  ))}
                  {trace.orders.length === 0 && trace.payments.length === 0 && (
                    <div className="col-span-2 p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground">
                      Unavailable: No payment execution or order records linked.
                    </div>
                  )}
                </div>
              </div>

              {/* 5. Related Audit Log Trail */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <History className="size-4 text-primary" /> Tamper-Evident Audit Events ({trace.audit_events.length})
                </h4>
                {trace.audit_events.length === 0 ? (
                  <div className="p-4 border border-dashed border-border rounded-lg text-center text-xs text-muted-foreground">
                    Unavailable: No audit events recorded for this run.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {trace.audit_events.map((evt) => (
                      <div key={evt.id} className="p-2.5 bg-background border border-border rounded text-xs flex items-center justify-between">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-foreground">{evt.event_type}</span>
                            <Badge variant="outline" className="text-[9px] px-1 py-0">{evt.event_category}</Badge>
                          </div>
                          <div className="text-muted-foreground text-[11px] font-mono">
                            {evt.entity_id ? `Target: ${evt.entity_id}` : `ID: ${evt.id}`}
                          </div>
                        </div>
                        <div className="text-right text-[11px] text-muted-foreground">
                          {new Date(evt.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
            );
          })()}
        </div>
      </SheetContent>
    </Sheet>
  );
}
