import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Terminal, ArrowRight, ShieldCheck, CheckCircle2, AlertTriangle, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { agentsApi } from "@/api/agents";

export const Route = createFileRoute("/app/console/")({
  component: ConsoleLandingRoute,
});

function ConsoleLandingRoute() {
  const navigate = useNavigate();

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list
  });

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-12rem)] animate-in zoom-in-95 duration-500 max-w-3xl mx-auto text-center px-4">
      <div className="size-16 rounded-2xl bg-surface border border-border flex items-center justify-center mb-8 shadow-sm">
        <Terminal className="size-8 text-primary" />
      </div>
      
      <h1 className="text-3xl font-bold tracking-tight mb-4">AGENT CONSOLE</h1>
      
      <p className="text-lg text-muted-foreground mb-12 max-w-xl">
        Operate your autonomous financial agents. Every consequential action is evaluated by FINSHIELD before it reaches execution.
      </p>

      <div className="w-full grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
        {agents.length === 0 ? (
          <div className="col-span-full text-center p-8 text-muted-foreground border border-dashed border-border rounded-xl">
            No agents available. Register an agent to get started.
          </div>
        ) : agents.map((agent) => (
          <Button 
            key={agent.id}
            variant="outline" 
            className="h-auto p-4 flex flex-col items-start text-left bg-surface hover:bg-surface-raised border-border transition-all"
            onClick={() => navigate({ to: `/app/console/${agent.id}` })}
          >
            <div className="font-semibold mb-1">{agent.name}</div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-safe animate-pulse-dot" />
              Active session
              <ArrowRight className="size-3 ml-auto opacity-50" />
            </div>
          </Button>
        ))}
      </div>

      <div className="w-full text-left max-w-2xl">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-2">Recent Sessions</h3>
        <div className="space-y-3">
          <div className="p-8 text-center text-muted-foreground border border-border bg-surface rounded-xl">
            No recent sessions.
          </div>
        </div>
      </div>
    </div>
  );
}
