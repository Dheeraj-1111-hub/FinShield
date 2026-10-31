import { Key, Webhook, Activity, ArrowUpRight, ArrowDownRight, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { DEV_STATS } from "@/data/mock-developers";

export function KpiCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* API Keys */}
      <Card className="p-5 border-border bg-surface shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">API Keys</span>
          <Key className="size-4 text-muted-foreground" />
        </div>
        <div className="text-3xl font-bold font-mono text-foreground mb-1">{DEV_STATS.activeKeys}</div>
        <div className="text-sm text-muted-foreground">active keys</div>
        {DEV_STATS.expiringKeys > 0 && (
          <div className="mt-3 text-xs text-warn font-medium">
            ⚠ {DEV_STATS.expiringKeys} key expires within 30 days
          </div>
        )}
      </Card>

      {/* Webhooks */}
      <Card className="p-5 border-border bg-surface shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Webhooks</span>
          <Webhook className="size-4 text-muted-foreground" />
        </div>
        <div className="text-3xl font-bold font-mono text-foreground mb-1">{DEV_STATS.webhooks}</div>
        <div className="text-sm text-muted-foreground">configured</div>
        <div className="mt-3 flex items-center gap-1.5 text-xs text-safe font-medium">
          <span className="size-1.5 rounded-full bg-safe" />
          {DEV_STATS.healthyWebhooks} healthy
        </div>
      </Card>

      {/* API Health */}
      <Card className="p-5 border-border bg-surface shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">API Health</span>
          <Activity className="size-4 text-muted-foreground" />
        </div>
        <div className="text-3xl font-bold font-mono text-foreground mb-1">{DEV_STATS.apiUptime}%</div>
        <div className="text-sm text-muted-foreground">uptime</div>
        <div className="mt-3 text-xs text-muted-foreground">
          {DEV_STATS.avgLatencyMs}ms avg latency
        </div>
      </Card>

      {/* Requests */}
      <Card className="p-5 border-border bg-surface shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Requests · 24h</span>
          <TrendingUp className="size-4 text-muted-foreground" />
        </div>
        <div className="text-3xl font-bold font-mono text-foreground mb-1">{DEV_STATS.requests24h.toLocaleString()}</div>
        <div className="flex items-center gap-1 text-sm text-safe font-medium">
          <ArrowUpRight className="size-4" />
          {DEV_STATS.requests24hDelta}%
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          {DEV_STATS.errors24h} errors · {DEV_STATS.successRate}% success
        </div>
      </Card>
    </div>
  );
}
