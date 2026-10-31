import { Bot, Plus, ExternalLink, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CONNECTED_AGENTS, ConnectedAgent } from "@/data/mock-developers";

interface Props {
  onRegisterAgent: () => void;
}

const statusStyle = (status: ConnectedAgent["status"]) => {
  switch (status) {
    case "CONNECTED":    return "text-safe bg-safe/10 border-safe/20";
    case "DISCONNECTED": return "text-muted-foreground bg-muted border-border";
    case "SUSPENDED":    return "text-danger bg-danger/10 border-danger/20";
  }
};

export function AgentsSection({ onRegisterAgent }: Props) {
  return (
    <Card className="border-border bg-surface shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Bot className="size-4 text-primary" />
          <div>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Connected</div>
            <div className="font-bold text-foreground">Agents</div>
          </div>
        </div>
        <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5" onClick={onRegisterAgent}>
          <Plus className="size-3.5" /> Register Agent
        </Button>
      </div>

      <div className="divide-y divide-border">
        {CONNECTED_AGENTS.map(agent => (
          <div key={agent.id} className="px-6 py-5 hover:bg-muted/30 transition-colors group">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div className="size-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                  <Bot className="size-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-foreground">{agent.name}</div>
                  <code className="text-xs font-mono text-muted-foreground">{agent.agentId}</code>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {agent.capabilities.map(cap => (
                      <span key={cap} className="text-xs px-2 py-0.5 rounded-md bg-muted border border-border text-muted-foreground font-medium">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-bold uppercase ${statusStyle(agent.status)}`}>
                  <span className="size-1.5 rounded-full bg-current animate-pulse" />
                  {agent.status}
                </span>
                <Button size="sm" variant="outline" className="border-border bg-background gap-1.5 text-xs opacity-0 group-hover:opacity-100 transition-opacity">
                  <ExternalLink className="size-3" /> View Agent
                </Button>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              {[
                { label: "Last request", value: agent.lastRequest },
                { label: "API version",  value: agent.apiVersion },
                { label: "Requests",     value: agent.requests.toLocaleString() },
              ].map(stat => (
                <div key={stat.label} className="bg-muted rounded-lg p-2.5 text-center">
                  <div className="text-xs text-muted-foreground mb-0.5">{stat.label}</div>
                  <div className="text-sm font-semibold font-mono text-foreground">{stat.value}</div>
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <Zap className="size-3 text-primary" />
              Policy: <code className="text-primary font-mono">{agent.policyId}</code>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
