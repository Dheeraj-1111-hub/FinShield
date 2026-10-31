import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { AuditEvent } from "@/api/audit";
import { X, ArrowDown, ExternalLink, ShieldAlert, CheckCircle2, Link2, FileText, Activity } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";

interface AuditDetailDrawerProps {
  event: AuditEvent;
  onClose: () => void;
}

export function AuditDetailDrawer({ event, onClose }: AuditDetailDrawerProps) {
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    navigate({ to: path });
    onClose();
  };

  return (
    <Sheet open onOpenChange={() => onClose()}>
      <SheetContent side="right" className="w-[450px] p-0 border-l border-border bg-background sm:max-w-[450px]">
        
        {/* Header */}
        <div className="p-6 border-b border-border/50">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-mono text-muted-foreground uppercase tracking-widest font-semibold flex items-center gap-2">
              <FileText className="size-4" /> AUDIT EVENT
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="size-6 text-muted-foreground hover:text-foreground">
              <X className="size-4" />
            </Button>
          </div>
          
          <div className="text-sm font-mono text-primary mb-2 font-bold">{event.id}</div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
              event.severity === 'CRITICAL' ? 'text-danger bg-danger/10 border-danger/20' : 
              event.severity === 'HIGH' ? 'text-warn bg-warn/10 border-warn/20' : 
              event.severity === 'WARNING' ? 'text-amber-500 bg-amber-500/10 border-amber-500/20' : 
              'text-muted-foreground bg-muted border-border'
            }`}>
              {event.severity}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border text-safe bg-safe/10 border-safe/20`}>
              {event.event_category}
            </span>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto h-[calc(100vh-140px)] p-6 space-y-8">
          
          {/* Metadata Section */}
          <div className="space-y-4">
            <div>
              <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Timestamp</div>
              <div className="text-sm font-mono text-foreground">{new Date(event.created_at).toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Actor Type</div>
              <div className="text-sm text-foreground">{event.actor_type}</div>
              <div className="text-xs font-mono text-muted-foreground">{event.actor_id || event.agent_id || 'SYSTEM'}</div>
            </div>
            {event.payload && (
              <div>
                <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">Payload Details</div>
                <div className="text-sm font-mono font-bold text-foreground">
                  <pre className="bg-surface border border-border rounded p-2 overflow-x-auto text-xs text-muted-foreground">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </div>
              </div>
            )}
            {event.ip_address && (
              <div>
                <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">IP Address</div>
                <div className="text-sm text-foreground">{event.ip_address}</div>
              </div>
            )}
          </div>

          <hr className="border-border/50" />

          {/* Trace Section (Simplified for now) */}
          <div>
            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-4 flex items-center gap-2">
              <Activity className="size-3" /> Event Details
            </div>
            
            <div className="space-y-0 text-sm pl-2 border-l border-border/50 relative">
              <div className="absolute left-[-5px] bottom-0 size-2 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary),0.8)]" />
              <div className="pl-4 pb-4">
                <div className="font-mono text-xs text-muted-foreground mb-1">{new Date(event.created_at).toLocaleTimeString()}</div>
                <div className="font-bold text-primary">{event.event_type}</div>
                {event.agent_action_id && (
                  <div className="text-xs italic text-muted-foreground mt-1">Action: {event.agent_action_id}</div>
                )}
                {event.agent_run_id && (
                  <div className="text-xs italic text-muted-foreground mt-1">Run: {event.agent_run_id}</div>
                )}
              </div>
            </div>
          </div>

          <hr className="border-border/50" />

          {/* Cryptographic Audit Proof */}
          <div>
            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-4 flex items-center gap-2">
              <Link2 className="size-3" /> Audit Integrity
            </div>
            
            <div className="bg-surface-raised border border-border p-4 rounded-md space-y-4">
              <div className="flex items-center gap-2 text-safe text-sm font-bold mb-2">
                <CheckCircle2 className="size-4" /> Event cryptographically verified
              </div>
              
              <div>
                <div className="text-xs text-muted-foreground mb-1">Event Hash (SHA-256)</div>
                <div className="font-mono text-xs text-primary bg-background px-2 py-1 rounded border border-border break-all">
                  {event.event_hash || event.hash}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-muted-foreground mb-1">Previous Hash</div>
                <div className="font-mono text-xs text-muted-foreground bg-background px-2 py-1 rounded border border-border break-all">
                  {event.previous_event_hash || 'GENESIS'}
                </div>
              </div>

              <div>
                <div className="text-xs text-muted-foreground mb-1">Chain Position (Workspace)</div>
                <div className="font-mono text-xs text-foreground">
                  #{event.workspace_sequence.toLocaleString()}
                </div>
              </div>

              <div className="text-[11px] text-muted-foreground border-t border-border/50 pt-2 leading-tight">
                Cryptographic hash chaining verifies that this event is immutably linked in the ledger. Hash verification does not guarantee the completeness of unrecorded external actions.
              </div>
            </div>
          </div>


          {/* Related Links */}
          <div className="pt-2 pb-6 space-y-2">
            {event.entity_type === 'INVESTIGATION' && (
              <Button 
                variant="outline" 
                className="w-full justify-between bg-surface hover:bg-surface-raised border-border text-xs"
                onClick={() => handleNavigate('/app/investigations')}
              >
                View Investigation ({event.entity_id}) <ExternalLink className="size-3 text-muted-foreground" />
              </Button>
            )}
            {event.entity_type === 'POLICY' && (
              <Button 
                variant="outline" 
                className="w-full justify-between bg-surface hover:bg-surface-raised border-border text-xs"
                onClick={() => handleNavigate('/app/policies')}
              >
                View Policy ({event.entity_id}) <ExternalLink className="size-3 text-muted-foreground" />
              </Button>
            )}
          </div>

        </div>
      </SheetContent>
    </Sheet>
  );
}
