import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { RiskAssessment } from "@/api/risk";
import { XCircle, AlertTriangle, ArrowUpRight, Activity, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ThreatDetailsDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assessment: RiskAssessment | null;
}

export function ThreatDetailsDrawer({ open, onOpenChange, assessment }: ThreatDetailsDrawerProps) {
  if (!assessment) return null;

  const getRiskColor = (level: string) => {
    switch(level) {
      case 'CRITICAL': return "text-danger bg-danger/10 border-danger/20";
      case 'HIGH': return "text-warn bg-warn/10 border-warn/20";
      case 'MEDIUM': return "text-blue-500 bg-blue-500/10 border-blue-500/20";
      default: return "text-safe bg-safe/10 border-safe/20";
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto border-l border-border bg-background p-0">
        <div className="p-6 space-y-8">
          
          {/* Header */}
          <SheetHeader className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {assessment.risk_level === 'CRITICAL' ? (
                  <div className="p-2 bg-danger/10 text-danger rounded-lg">
                    <XCircle className="size-6" />
                  </div>
                ) : (
                  <div className="p-2 bg-warn/10 text-warn rounded-lg">
                    <AlertTriangle className="size-6" />
                  </div>
                )}
                <div>
                  <SheetTitle className="text-xl">Risk Assessment Details</SheetTitle>
                  <SheetDescription>
                    ID: {assessment.id}
                  </SheetDescription>
                </div>
              </div>
              <span className={`text-xs uppercase font-bold px-3 py-1 rounded-full border ${getRiskColor(assessment.risk_level)}`}>
                {assessment.risk_level}
              </span>
            </div>
          </SheetHeader>

          {/* Top Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Final Risk Score</div>
              <div className="font-mono text-2xl font-semibold">{assessment.risk_score}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Decision Hint</div>
              <div className="font-medium text-foreground">{assessment.decision_hint}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Timestamp</div>
              <div className="font-medium text-muted-foreground">{new Date(assessment.created_at).toLocaleString()}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Agent ID</div>
              <div className="font-medium text-muted-foreground">{assessment.agent_id || "System"}</div>
            </div>
          </div>

          <div className="h-px bg-border w-full my-4" />

          {/* Signals Breakdown */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Activity className="size-5 text-muted-foreground" />
              Evaluation Signals
            </h3>
            
            <div className="space-y-3">
              {assessment.signals.map((signal, idx) => (
                <div key={idx} className="p-4 rounded-md border border-border bg-surface space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {signal.signal_type}
                        <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${getRiskColor(signal.severity)}`}>
                          {signal.severity}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1 font-mono">{signal.reason_code}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono font-semibold">{signal.contribution.toFixed(1)} <span className="text-xs text-muted-foreground font-sans">pts</span></div>
                      <div className="text-xs text-muted-foreground">weight: {signal.weight}</div>
                    </div>
                  </div>
                  <div className="text-sm text-foreground/90 bg-muted/20 p-2 rounded border border-border/50">
                    {signal.explanation}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Feature Snapshot */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Cpu className="size-5 text-muted-foreground" />
              Feature Snapshot
            </h3>
            <p className="text-sm text-muted-foreground">The exact data context captured by the engine at evaluation time.</p>
            <pre className="p-4 rounded-md border border-border bg-black text-green-400 font-mono text-xs overflow-x-auto">
              {JSON.stringify(assessment.feature_snapshot, null, 2)}
            </pre>
          </div>

          {/* Action Links */}
          <div className="flex flex-col gap-2 pt-4">
            {assessment.agent_run_id && (
              <Button variant="outline" className="justify-between">
                View Agent Session
                <ArrowUpRight className="size-4 text-muted-foreground" />
              </Button>
            )}
            {assessment.intent_id && (
              <Button variant="outline" className="justify-between">
                View Intent {assessment.intent_version && `(v${assessment.intent_version})`}
                <ArrowUpRight className="size-4 text-muted-foreground" />
              </Button>
            )}
            {assessment.authority_id && (
              <Button variant="outline" className="justify-between">
                View Delegated Authority {assessment.authority_version && `(v${assessment.authority_version})`}
                <ArrowUpRight className="size-4 text-muted-foreground" />
              </Button>
            )}
          </div>

        </div>
      </SheetContent>
    </Sheet>
  );
}
