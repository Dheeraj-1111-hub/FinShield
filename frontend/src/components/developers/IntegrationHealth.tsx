import { Shield } from "lucide-react";
import { Card } from "@/components/ui/card";
import { DEV_STATS } from "@/data/mock-developers";

const SERVICES = [
  { label: "API",           status: "OPERATIONAL", detail: `${DEV_STATS.apiUptime}% uptime`,       color: "text-safe bg-safe/10 border-safe/20" },
  { label: "Webhooks",      status: "OPERATIONAL", detail: "99.9% delivery",                          color: "text-safe bg-safe/10 border-safe/20" },
  { label: "Policy Engine", status: "OPERATIONAL", detail: `${DEV_STATS.avgLatencyMs}ms avg`,       color: "text-safe bg-safe/10 border-safe/20" },
  { label: "Risk Engine",   status: "OPERATIONAL", detail: "Real-time scoring",                       color: "text-safe bg-safe/10 border-safe/20" },
  { label: "Audit Log",     status: "OPERATIONAL", detail: "100% integrity",                          color: "text-safe bg-safe/10 border-safe/20" },
  { label: "SDK",           status: "OPERATIONAL", detail: "v1.9 — current",                         color: "text-safe bg-safe/10 border-safe/20" },
];

export function IntegrationHealth() {
  return (
    <Card className="border-border bg-surface shadow-sm p-6">
      <div className="flex items-center gap-3 mb-5">
        <Shield className="size-4 text-primary" />
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Platform</div>
          <div className="font-bold text-foreground">Integration Health</div>
        </div>
        <div className="ml-auto flex items-center gap-2 px-3 py-1 bg-safe/10 border border-safe/20 rounded-lg text-xs font-bold text-safe uppercase tracking-wider">
          <span className="size-1.5 rounded-full bg-safe animate-pulse" /> All Systems Operational
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {SERVICES.map(s => (
          <div key={s.label} className={`flex flex-col items-center text-center p-4 rounded-xl border ${s.color}`}>
            <div className="size-2 rounded-full bg-current mb-2 animate-pulse" />
            <div className="text-sm font-bold text-foreground">{s.label}</div>
            <div className="text-xs font-medium mt-0.5" style={{ color: "inherit" }}>{s.status}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.detail}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
