import { Webhook, Plus, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WEBHOOKS, WebhookEndpoint } from "@/data/mock-developers";

interface Props {
  onSelectWebhook: (wh: WebhookEndpoint) => void;
}

const healthStyle = (h: WebhookEndpoint["health"]) => {
  switch (h) {
    case "HEALTHY":  return "text-safe bg-safe/10 border-safe/20";
    case "DEGRADED": return "text-warn bg-warn/10 border-warn/20";
    case "FAILING":  return "text-danger bg-danger/10 border-danger/20";
  }
};

export function WebhooksSection({ onSelectWebhook }: Props) {
  return (
    <Card className="border-border bg-surface shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Webhook className="size-4 text-primary" />
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Events</div>
            <div className="font-bold text-foreground">Webhooks</div>
          </div>
        </div>
        <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5">
          <Plus className="size-3.5" /> Add Endpoint
        </Button>
      </div>

      <div className="px-6 pb-2 pt-3">
        <p className="text-xs text-muted-foreground">Receive real-time FINSHIELD events in your infrastructure.</p>
      </div>

      <div className="divide-y divide-border">
        {WEBHOOKS.map(wh => (
          <div
            key={wh.id}
            className="px-6 py-4 hover:bg-muted/40 transition-colors cursor-pointer group"
            onClick={() => onSelectWebhook(wh)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <code className="text-sm font-mono text-foreground break-all">{wh.url}</code>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {wh.events.slice(0, 4).map(e => (
                    <span key={e} className="text-xs px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground font-mono">
                      {e}
                    </span>
                  ))}
                  {wh.events.length > 4 && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground">
                      +{wh.events.length - 4} more
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-bold uppercase ${healthStyle(wh.health)}`}>
                  <span className="size-1.5 rounded-full bg-current animate-pulse" />
                  {wh.health}
                </span>
                <ChevronRight className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-6 text-xs text-muted-foreground">
              <span className="text-safe font-medium">{wh.deliveries.toLocaleString()} deliveries</span>
              <span>{wh.deliverySuccessRate}% success rate</span>
              <span>Last: {wh.lastDelivery}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
