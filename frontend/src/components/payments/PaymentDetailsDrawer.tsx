import { useState } from "react";
import { 
  X, CheckCircle2, ShieldAlert, XCircle, Play, Ban, ShieldCheck, Activity
} from "lucide-react";
import { Payment, paymentsApi } from "@/api/payments";
import { Button } from "@/components/ui/button";
import { GateDecisionDrawer } from "@/components/gate/GateDecisionDrawer";

interface PaymentDetailsDrawerProps {
  payment: Payment;
  onClose: () => void;
}

export function PaymentDetailsDrawer({ payment: initialPayment, onClose }: PaymentDetailsDrawerProps) {
  const [payment, setPayment] = useState<Payment>(initialPayment);
  const [inspectDecisionId, setInspectDecisionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isFailed = payment.status === 'FAILED' || payment.status === 'CANCELLED';
  const isCaptured = payment.status === 'CAPTURED';
  const isAuthorized = payment.status === 'AUTHORIZED';
  
  return (
    <div className="absolute inset-y-0 right-0 w-[500px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Drawer Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="font-semibold">PAYMENT DETAILS</div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        
        {/* Hero Section */}
        <div className="p-6 border-b border-border">
          <div className="text-sm font-mono text-muted-foreground mb-4">{payment.id}</div>
          
          <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold tracking-wider mb-6 ${
            isCaptured || isAuthorized ? 'bg-safe/10 text-safe border border-safe/20' :
            payment.status === 'REQUIRES_AUTHORIZATION' ? 'bg-warn/10 text-warn border border-warn/20' :
            isFailed ? 'bg-danger/10 text-danger border border-danger/20' :
            'bg-surface-raised text-foreground border border-border'
          }`}>
            {isCaptured && <CheckCircle2 className="size-3" />}
            {payment.status === 'REQUIRES_AUTHORIZATION' && <ShieldAlert className="size-3" />}
            {isFailed && <XCircle className="size-3" />}
            {payment.status.replace(/_/g, ' ')}
          </div>
          
          <div className="text-4xl font-bold tracking-tight mb-2">
            {payment.currency === 'INR' ? '₹' : (payment.currency === 'USD' ? '$' : `${payment.currency} `)}
            {payment.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
          <div className="text-lg text-muted-foreground">Sandbox Transaction</div>
          {error && <div className="mt-4 p-3 bg-danger/10 border border-danger/20 text-danger text-sm rounded-lg">{error}</div>}
        </div>

        {/* Entities */}
        <div className="grid grid-cols-2 gap-px bg-border border-b border-border">
          <div className="bg-background p-6">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Agent ID</div>
            <div className="font-mono text-sm">{payment.agent_id || 'Direct'}</div>
          </div>
          <div className="bg-background p-6">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Merchant Ref</div>
            <div className="font-medium text-sm">{payment.merchant_reference || 'Sandbox Merchant'}</div>
          </div>
          <div className="bg-background p-6">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Intent ID</div>
            <div className="text-sm font-mono">{payment.payment_intent_id}</div>
          </div>
          <div className="bg-background p-6">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Created At</div>
            <div className="text-sm">{new Date(payment.created_at).toLocaleString()}</div>
          </div>
        </div>

        {/* Payment Lifecycle */}
        {payment.failure_reason && (
          <div className="p-6 border-b border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Failure Reason</div>
            <div className="p-4 bg-danger/10 border border-danger/20 rounded-lg">
              <div className="text-danger font-medium mb-1">{payment.failure_code}</div>
              <div className="text-sm text-danger/80">{payment.failure_reason}</div>
            </div>
          </div>
        )}
        
        {/* FINSHIELD PROVENANCE */}
        <div className="p-6 border-b border-border">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" />
            FINSHIELD Provenance
          </div>
          
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Gate Decision</span>
                {payment.gate_decision_id && (
                  <button 
                    onClick={() => setInspectDecisionId(payment.gate_decision_id || null)}
                    className="text-[11px] text-primary hover:underline font-medium flex items-center gap-1"
                  >
                    Inspect Decision &rarr;
                  </button>
                )}
              </div>
              <div className={`font-semibold ${payment.gate_decision === 'ALLOW' ? 'text-safe' : payment.gate_decision === 'BLOCK' ? 'text-danger' : 'text-warn'}`}>
                {payment.gate_decision || "N/A"}
              </div>
              {payment.gate_decision_id ? (
                <div 
                  onClick={() => setInspectDecisionId(payment.gate_decision_id || null)}
                  className="text-xs font-mono text-muted-foreground hover:text-foreground cursor-pointer underline decoration-dotted mt-0.5"
                  title="Click to inspect this Gate Decision"
                >
                  {payment.gate_decision_id}
                </div>
              ) : (
                <div className="text-xs font-mono text-muted-foreground mt-0.5">-</div>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Risk Assessment</div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{payment.risk_assessment_id || "N/A"}</span>
                  {payment.risk_level && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                      payment.risk_level === 'HIGH' || payment.risk_level === 'CRITICAL' ? 'bg-danger/10 text-danger' : 
                      payment.risk_level === 'MEDIUM' ? 'bg-warn/10 text-warn' : 'bg-safe/10 text-safe'
                    }`}>
                      {payment.risk_level}{payment.risk_score !== undefined && payment.risk_score !== null ? ` (${payment.risk_score.toFixed(1)})` : ''}
                    </span>
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Intent ID</div>
                <div className="font-mono text-sm">{payment.intent_id || "N/A"}</div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Agent Run</div>
                <div className="font-mono text-sm">{payment.run_id || "N/A"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Agent Action</div>
                <div className="font-mono text-sm">{payment.action_id || "N/A"}</div>
              </div>
            </div>
          </div>
        </div>

      </div>
      
      {/* Gate Decision Drawer overlay */}
      <GateDecisionDrawer
        decisionId={inspectDecisionId}
        onClose={() => setInspectDecisionId(null)}
      />
      
      {/* Footer Actions */}
      <div className="p-5 border-t border-border bg-surface shrink-0 flex gap-3">
        {payment.status === 'CREATED' && (
          <>
            <Button variant="outline" className="flex-1 hover:bg-danger/10 hover:text-danger" disabled={isSubmitting} onClick={async () => {
              setIsSubmitting(true); setError(null);
              try { setPayment(await paymentsApi.cancel(payment.id)); } catch (e: any) { setError(e.response?.data?.error?.message || "Action failed"); }
              finally { setIsSubmitting(false); }
            }}>
              Cancel
            </Button>
            <Button className="flex-1 bg-primary" disabled={isSubmitting} onClick={async () => {
              setIsSubmitting(true); setError(null);
              try { setPayment(await paymentsApi.authorize(payment.id)); } catch (e: any) { setError(e.response?.data?.error?.message || "Action failed"); }
              finally { setIsSubmitting(false); }
            }}>
              Sandbox Authorize
            </Button>
          </>
        )}
        
        {payment.status === 'AUTHORIZED' && (
          <Button className="w-full bg-safe text-safe-foreground hover:bg-safe/90" disabled={isSubmitting} onClick={async () => {
            setIsSubmitting(true); setError(null);
            try { setPayment(await paymentsApi.capture(payment.id)); } catch (e: any) { setError(e.response?.data?.error?.message || "Action failed"); }
            finally { setIsSubmitting(false); }
          }}>
            <Play className="mr-2 size-4" /> Sandbox Capture
          </Button>
        )}

        {(isCaptured || isFailed) && (
          <Button variant="outline" className="w-full" onClick={onClose}>Close</Button>
        )}
      </div>

    </div>
  );
}
