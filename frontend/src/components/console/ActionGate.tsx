import { useState } from "react";
import { CheckCircle2, ShieldAlert, XCircle, ChevronDown, ArrowDown, Loader2, CircleDot } from "lucide-react";
import { FinshieldEvaluation } from "@/data/mock-console";
import { Button } from "@/components/ui/button";
import { useNavigate } from "@tanstack/react-router";
import { investigationsApi } from "@/api/investigations";

export function ActionGate({ 
  evaluation,
  onInspectDecisionTrace 
}: { 
  evaluation: FinshieldEvaluation;
  onInspectDecisionTrace?: () => void;
}) {
  const isBlock = evaluation.decision === 'BLOCK';
  const isReview = evaluation.decision === 'REVIEW_REQUIRED';
  const isAllow = evaluation.decision === 'ALLOW';
  const isFailed = evaluation.decision === 'FAILED';
  const isUnavailable = evaluation.decision === 'UNAVAILABLE';
  const isReadOnly = evaluation.decision === 'NOT EVALUATED';
  const navigate = useNavigate();
  const [isInvestigating, setIsInvestigating] = useState(false);

  const handleInvestigate = async () => {
    if (!evaluation.runId) {
      navigate({ to: "/app/investigations" });
      return;
    }
    setIsInvestigating(true);
    try {
      const inv = await investigationsApi.getInvestigationByRun(evaluation.runId);
      if (inv && inv.id) {
        navigate({ to: "/app/investigations", search: { id: inv.id } as any });
      } else {
        navigate({ to: "/app/investigations", search: { run_id: evaluation.runId } as any });
      }
    } catch (e) {
      navigate({ to: "/app/investigations" });
    } finally {
      setIsInvestigating(false);
    }
  };

  return (
    <div className="w-full rounded-xl border border-border bg-surface overflow-hidden shadow-sm animate-in fade-in zoom-in-95 duration-500">
      {/* Header Context */}
      <div className="p-4 border-b border-border bg-background/50 text-center">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
          {isReadOnly ? "Read-Only Operation" : isUnavailable ? "Action Unavailable / Blocked" : isFailed ? "Execution Failed" : "Action Proposed"}
        </div>
        <div className="font-medium">{evaluation.actionContext.type} {evaluation.actionContext.target}</div>
        {evaluation.actionContext.amount && (
          <div className="text-xl font-bold mt-1">₹{evaluation.actionContext.amount.toLocaleString()}</div>
        )}
      </div>

      <div className="py-2 flex justify-center">
        <ArrowDown className="size-4 text-muted-foreground" />
      </div>

      <div className="text-center pb-2">
        <div className="text-xs font-bold tracking-widest text-primary">FINSHIELD</div>
      </div>

      {/* Evaluation Scores */}
      <div className="px-5 pb-5 space-y-3">
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Intent Alignment</span>
          <span className={`font-mono font-medium flex items-center gap-1.5 ${
            evaluation.intentAlignment === 'ALIGNED' ? 'text-safe' : 
            evaluation.intentAlignment === 'MISALIGNED' ? 'text-danger' : 
            evaluation.intentAlignment === 'PARTIAL' ? 'text-warn' : 'text-muted-foreground'
          }`}>
            {evaluation.intentAlignment === 'ALIGNED' ? <CheckCircle2 className="size-3.5" /> : 
             evaluation.intentAlignment === 'MISALIGNED' ? <XCircle className="size-3.5" /> : 
             evaluation.intentAlignment === 'PARTIAL' ? <ShieldAlert className="size-3.5" /> : null}
            {evaluation.intentAlignment}
          </span>
        </div>
        
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Transaction Risk</span>
          <span className={`font-mono font-medium flex items-center gap-1.5 ${
            evaluation.transactionRisk === 'LOW' ? 'text-safe' : (evaluation.transactionRisk === 'NOT EVALUATED' ? 'text-muted-foreground' : 'text-danger')
          }`}>
            {evaluation.transactionRisk === 'LOW' ? <CheckCircle2 className="size-3.5" /> : (evaluation.transactionRisk === 'NOT EVALUATED' ? null : <ShieldAlert className="size-3.5" />)}
            {evaluation.transactionRisk}
          </span>
        </div>

        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Policy Evaluation</span>
          <span className={`font-mono font-medium flex items-center gap-1.5 ${
            evaluation.policyResult === 'PASS' ? 'text-safe' : evaluation.policyResult === 'REVIEW' ? 'text-warn' : (evaluation.policyResult === 'NOT EVALUATED' ? 'text-muted-foreground' : 'text-danger')
          }`}>
            {evaluation.policyResult === 'PASS' ? <CheckCircle2 className="size-3.5" /> : 
             evaluation.policyResult === 'REVIEW' ? <ShieldAlert className="size-3.5" /> : (evaluation.policyResult === 'NOT EVALUATED' ? null : <XCircle className="size-3.5" />)}
            {evaluation.policyResult}
          </span>
        </div>
        
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Authority Check</span>
          <span className={`font-mono font-medium flex items-center gap-1.5 ${
            evaluation.authorityCheck === 'PASS' ? 'text-safe' : (evaluation.authorityCheck === 'NOT EVALUATED' ? 'text-muted-foreground' : 'text-danger')
          }`}>
            {evaluation.authorityCheck === 'PASS' ? <CheckCircle2 className="size-3.5" /> : (evaluation.authorityCheck === 'NOT EVALUATED' ? null : <XCircle className="size-3.5" />)}
            {evaluation.authorityCheck}
          </span>
        </div>
      </div>

      <div className="h-px bg-border w-full" />

      {/* Final Decision */}
      <div className={`p-5 ${
        isAllow ? 'bg-safe/5' : isReview ? 'bg-warn/5' : isReadOnly ? 'bg-primary/5' : 'bg-danger/10'
      }`}>
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 text-center">
          {isReadOnly 
            ? "Execution Step Classification" 
            : (evaluation.isLatestAuthoritative 
                ? "Latest Authoritative Decision" 
                : (evaluation.actionContext.type === 'checkout' 
                    ? `Step ${evaluation.stepNumber || 1} Decision (Intermediate Checkout)` 
                    : `Step ${evaluation.stepNumber || 1} Decision (Prior Step)`))}
        </div>
        
        <div className={`flex items-center justify-center gap-2 text-xl font-bold mb-2 ${
          isAllow ? 'text-safe' : isReview ? 'text-warn' : isReadOnly ? 'text-primary' : 'text-danger'
        }`}>
          {isAllow ? <CheckCircle2 className="size-6" /> : isReview ? <ShieldAlert className="size-6" /> : isReadOnly ? <CircleDot className="size-6 text-primary" /> : <XCircle className="size-6" />}
          {isReadOnly ? "READ-ONLY (NO FINANCIAL GATE)" : evaluation.decision}
        </div>

        {isReadOnly && (
          <div className="text-xs text-center text-muted-foreground mb-3 leading-relaxed">
            Permitted read-only operation. No cart, checkout, or monetary transaction gated or authorized.
          </div>
        )}
        {isUnavailable && (
          <div className="text-xs text-center text-danger/90 mb-3 leading-relaxed">
            Protected financial action unavailable or blocked before execution.
          </div>
        )}
        {isFailed && (
          <div className="text-xs text-center text-danger/90 mb-3 leading-relaxed">
            Execution halted. Financial action could not be completed.
          </div>
        )}

        {evaluation.actionContext.type === 'checkout' && isAllow && (
          <div className="text-xs text-center text-amber-500 font-medium mb-3 bg-amber-500/10 py-1.5 px-2.5 rounded border border-amber-500/20">
            Intermediate Step: Order created in PENDING_PAYMENT. Checkout ALLOW does not authorize or capture funds.
          </div>
        )}

        {evaluation.actionContext.type === 'pay_order' && isAllow && (
          <div className="text-xs text-center text-safe font-medium mb-3 bg-safe/10 py-1.5 px-2.5 rounded border border-safe/20">
            Authoritative Post-Approval Decision: Payment authorized and captured.
          </div>
        )}

        {!evaluation.isLatestAuthoritative && evaluation.runStatus === 'WAITING_FOR_APPROVAL' && (
          <div className="text-xs text-center text-amber-500 font-semibold mb-3 bg-amber-500/10 py-1 px-2 rounded border border-amber-500/20">
            Run requires review at subsequent step — Latest Authoritative Decision is REVIEW_REQUIRED
          </div>
        )}

        {!evaluation.isLatestAuthoritative && evaluation.runStatus === 'BLOCKED' && (
          <div className="text-xs text-center text-red-500 font-semibold mb-3 bg-red-500/10 py-1 px-2 rounded border border-red-500/20">
            Run blocked at subsequent step — Final Authoritative Decision is BLOCK
          </div>
        )}

        {evaluation.runStatus === 'FAILED' && (
          <div className="text-xs text-center text-red-500 font-semibold mb-3 bg-red-500/10 py-1 px-2 rounded border border-red-500/20">
            Execution halted — Run Status: FAILED. Payment was not authorized or captured.
          </div>
        )}

        {!evaluation.isLatestAuthoritative && evaluation.runStatus && evaluation.runStatus !== 'COMPLETED' && evaluation.runStatus !== 'WAITING_FOR_APPROVAL' && evaluation.runStatus !== 'BLOCKED' && evaluation.runStatus !== 'FAILED' && (
          <div className="text-[11px] text-center text-muted-foreground/80 mb-3 font-medium">
            (Earlier Step Evaluation — Run Status: {evaluation.runStatus.replace(/_/g, ' ')})
          </div>
        )}

        {(isBlock || isFailed || isUnavailable) && (
          <div className="text-sm text-center mb-4 text-danger/90">
            {evaluation.reasoning}
          </div>
        )}

        {!isReadOnly && <Button 
          variant={isBlock || isFailed || isUnavailable ? "destructive" : "outline"} 
          className={`w-full ${isBlock || isFailed || isUnavailable ? '' : 'bg-background hover:bg-surface-raised'}`}
          disabled={isInvestigating}
          onClick={() => {
            if (isReview) {
              navigate({ to: "/app/approvals" });
            } else if (isBlock || isFailed || isUnavailable) {
              handleInvestigate();
            } else if (onInspectDecisionTrace) {
              onInspectDecisionTrace();
            }
          }}
        >
          {isInvestigating ? (
            <span className="flex items-center gap-2">
              <Loader2 className="size-4 animate-spin" />
              Loading Incident...
            </span>
          ) : (
            isBlock || isFailed || isUnavailable ? 'Investigate Incident' : isReview ? 'Review & Approve' : 'Inspect Decision Trace'
          )}
        </Button>}
      </div>
    </div>
  );
}
