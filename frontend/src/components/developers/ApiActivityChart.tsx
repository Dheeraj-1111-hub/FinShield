import { Activity } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ACTIVITY_BARS, DEV_STATS } from "@/data/mock-developers";

export function ApiActivityChart() {
  return (
    <Card className="border-border bg-surface shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <Activity className="size-4 text-primary" />
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Last 24 Hours</div>
            <div className="font-bold text-foreground">API Activity</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 bg-safe/10 border border-safe/20 rounded text-safe text-xs font-bold uppercase tracking-wider">
          <span className="size-1.5 rounded-full bg-safe animate-pulse" /> Live
        </div>
      </div>

      {/* Sparkline */}
      <div className="relative h-28 flex items-end gap-[3px] mb-4">
        {ACTIVITY_BARS.map(bar => (
          <div key={bar.hour} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full rounded-sm bg-primary/30 hover:bg-primary/60 transition-colors cursor-default relative"
              style={{ height: `${bar.heightPct}%` }}
            >
              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border border-border rounded text-xs font-mono text-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                {bar.hour}:00 — {bar.requests.toLocaleString()} req
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Hour labels */}
      <div className="flex justify-between text-xs text-muted-foreground font-mono mb-5">
        {["00", "06", "12", "18", "24"].map(h => <span key={h}>{h}</span>)}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
        {[
          { label: "Requests",    value: DEV_STATS.requests24h.toLocaleString(),       color: "text-foreground" },
          { label: "Success rate", value: `${DEV_STATS.successRate}%`,                  color: "text-safe" },
          { label: "p50 latency", value: `${DEV_STATS.p50Ms}ms`,                        color: "text-foreground" },
          { label: "p95 latency", value: `${DEV_STATS.p95Ms}ms`,                        color: "text-warn" },
        ].map(stat => (
          <div key={stat.label} className="text-center">
            <div className={`text-xl font-bold font-mono ${stat.color}`}>{stat.value}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{stat.label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
