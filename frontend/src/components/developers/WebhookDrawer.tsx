import { useState } from "react";
import { X, Webhook, Send, Eye, EyeOff, RotateCcw, PowerOff, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WebhookEndpoint } from "@/data/mock-developers";

interface Props {
  webhook: WebhookEndpoint | null;
  onClose: () => void;
}

const ALL_EVENTS = [
  "payment.blocked", "payment.allowed", "policy.review", "agent.action",
  "investigation.created", "security.alert", "audit.event", "agent.registered",
];

export function WebhookDrawer({ webhook, onClose }: Props) {
  const [showSecret, setShowSecret] = useState(false);
  const [testSent, setTestSent] = useState(false);

  if (!webhook) return null;

  const handleTest = () => {
    setTestSent(true);
    setTimeout(() => setTestSent(false), 3000);
  };

  const healthColor = webhook.health === 'HEALTHY'
    ? 'text-safe bg-safe/10 border-safe/20'
    : webhook.health === 'DEGRADED'
    ? 'text-warn bg-warn/10 border-warn/20'
    : 'text-danger bg-danger/10 border-danger/20';

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="ml-auto relative w-full max-w-md h-full bg-surface border-l border-border overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-surface border-b border-border px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-primary/15 flex items-center justify-center">
              <Webhook className="size-4 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-foreground text-sm">Webhook Endpoint</h2>
              <div className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">{webhook.url}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="size-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status */}
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-bold uppercase tracking-wider ${healthColor}`}>
            <span className="size-1.5 rounded-full bg-current animate-pulse" />
            {webhook.health}
          </span>

          {/* Events */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Subscribed Events</div>
            <div className="space-y-1.5">
              {ALL_EVENTS.map(ev => {
                const active = webhook.events.includes(ev);
                return (
                  <div key={ev} className="flex items-center gap-2.5 px-3 py-2 rounded-lg border border-border bg-muted text-sm">
                    <div className={`size-4 rounded border-2 flex items-center justify-center shrink-0 ${active ? "bg-primary border-primary" : "border-muted-foreground/30"}`}>
                      {active && <Check className="size-3 text-primary-foreground" strokeWidth={3} />}
                    </div>
                    <code className={`text-xs font-mono ${active ? "text-foreground" : "text-muted-foreground"}`}>{ev}</code>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Delivery stats */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Delivery</div>
            <div className="space-y-0 divide-y divide-border border border-border rounded-xl overflow-hidden">
              {[
                { label: "Successful",    value: webhook.deliveries.toLocaleString(), color: "text-safe" },
                { label: "Failed",        value: webhook.failures.toString(),          color: "text-danger" },
                { label: "Retry queue",   value: webhook.retryQueue.toString(),        color: "text-foreground" },
                { label: "Last delivery", value: webhook.lastDelivery,                  color: "text-foreground" },
                { label: "Response",      value: webhook.lastStatus,                    color: "text-safe" },
                { label: "Success rate",  value: `${webhook.deliverySuccessRate}%`,     color: "text-safe" },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between px-4 py-3 bg-muted text-sm">
                  <span className="text-muted-foreground">{row.label}</span>
                  <span className={`font-medium font-mono ${row.color}`}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Signing secret */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Signing Secret</div>
            <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-4 py-3">
              <code className="flex-1 text-sm font-mono text-primary">
                {showSecret ? "whsec_4a7f3c9d2e1b8044f6a2c890" : "whsec_••••••••••••••••••••••••"}
              </code>
              <button
                onClick={() => setShowSecret(s => !s)}
                className="shrink-0 size-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors bg-muted"
              >
                {showSecret ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
              </button>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Signature</span><span className="text-foreground font-medium">HMAC-SHA256</span></div>
              <div className="flex justify-between"><span>Replay protection</span><span className="text-safe font-medium">Enabled</span></div>
              <div className="flex justify-between"><span>Timestamp tolerance</span><span className="text-foreground font-medium">300 seconds</span></div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2 pt-2">
            <Button
              className={`w-full gap-2 ${testSent ? "bg-safe/15 text-safe border-safe/20" : "bg-primary hover:bg-primary/90 text-primary-foreground"}`}
              variant={testSent ? "outline" : "default"}
              onClick={handleTest}
            >
              {testSent ? <><Check className="size-4" /> Test Event Sent</> : <><Send className="size-4" /> Send Test Event</>}
            </Button>
            <Button variant="outline" className="w-full border-border bg-background gap-2">
              <RotateCcw className="size-4" /> Rotate Secret
            </Button>
            <Button variant="outline" className="w-full border-danger/30 bg-danger/5 text-danger hover:bg-danger/10 gap-2">
              <PowerOff className="size-4" /> Disable Endpoint
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
