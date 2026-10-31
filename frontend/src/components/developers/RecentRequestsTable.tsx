import { Terminal, ExternalLink } from "lucide-react";
import { Card } from "@/components/ui/card";
import { RECENT_REQUESTS, RecentRequest } from "@/data/mock-developers";

const methodStyle = (m: string) =>
  m === "POST" ? "text-primary bg-primary/10" : "text-info bg-info/10";

const decisionStyle = (d: RecentRequest["decision"]) => {
  switch (d) {
    case "BLOCKED":  return "text-danger";
    case "ALLOWED":  return "text-safe";
    case "REVIEW":   return "text-warn";
    case "EXECUTED": return "text-primary";
  }
};

export function RecentRequestsTable() {
  return (
    <Card className="border-border bg-surface shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Terminal className="size-4 text-primary" />
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Request Log</div>
            <div className="font-bold text-foreground">Recent Requests</div>
          </div>
        </div>
      </div>

      <div className="divide-y divide-border">
        {RECENT_REQUESTS.map(req => (
          <div key={req.id} className="px-6 py-3.5 hover:bg-muted/40 transition-colors cursor-pointer group flex items-center gap-4">
            {/* Time */}
            <span className="text-xs font-mono text-muted-foreground shrink-0 w-16">{req.time}</span>

            {/* Method badge */}
            <span className={`text-xs font-bold font-mono px-1.5 py-0.5 rounded shrink-0 ${methodStyle(req.method)}`}>
              {req.method}
            </span>

            {/* Path */}
            <code className="text-xs font-mono text-foreground flex-1 truncate">{req.path}</code>

            {/* Agent */}
            <span className="text-xs text-muted-foreground shrink-0 hidden md:block">{req.agent}</span>

            {/* Status */}
            <span className="text-xs font-mono text-muted-foreground shrink-0">{req.statusCode}</span>

            {/* Decision */}
            <span className={`text-xs font-bold shrink-0 w-16 text-right ${decisionStyle(req.decision)}`}>
              {req.decision}
            </span>

            {/* Latency */}
            <span className="text-xs font-mono text-muted-foreground shrink-0 w-12 text-right">{req.latencyMs}ms</span>

            {/* Link */}
            <ExternalLink className="size-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
          </div>
        ))}
      </div>
    </Card>
  );
}
