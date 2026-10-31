import { useState, useEffect } from "react";
import { X, ArrowRight, Play, AlertTriangle, Activity } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useRunSecurityTest } from "@/hooks/useSecurityLab";
import { SecurityScenario } from "@/api/security_lab";
import { agentsApi, Agent } from "@/api/agents";

interface SecurityTestDrawerProps {
  scenarioSlug: string;
  scenarios: SecurityScenario[];
  onClose: () => void;
}

export function SecurityTestDrawer({ scenarioSlug, scenarios, onClose }: SecurityTestDrawerProps) {
  const navigate = useNavigate();
  const runTestMutation = useRunSecurityTest();
  
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');

  const { data: agents = [], isLoading: loadingAgents } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  useEffect(() => {
    const s = scenarios.find(s => s.slug === scenarioSlug);
    if (s) {
      setSelectedScenarioId(s.id);
    } else if (scenarios.length > 0) {
      setSelectedScenarioId(scenarios[0].id);
    }
  }, [scenarioSlug, scenarios]);

  useEffect(() => {
    if (agents.length > 0 && !selectedAgentId) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  const handleLaunch = () => {
    runTestMutation.mutate({
      scenarioId: selectedScenarioId,
      targetAgentId: selectedAgentId || undefined,
      configuration: selectedAgentId ? { target_agent_id: selectedAgentId } : {}
    }, {
      onSuccess: (data) => {
        onClose();
        navigate({ to: `/app/lab/${data.id}` });
      }
    });
  };

  const selectedScenario = scenarios.find(s => s.id === selectedScenarioId);

  return (
    <div className="absolute inset-y-0 right-0 w-[600px] bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={onClose} className="size-6 -ml-2 rounded-full">
              <ArrowRight className="size-3.5 rotate-180" />
            </Button>
            Security Lab
          </div>
          <span className="text-muted-foreground">/</span>
          <div className="font-mono text-sm font-bold">
            NEW TEST
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="size-8 rounded-full">
          <X className="size-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        
        <div className="animate-in fade-in">
          <h2 className="text-2xl font-bold tracking-tight mb-6">Configure Security Test</h2>
          
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold">Scenario</label>
              <select 
                className="w-full bg-surface border border-border rounded-md px-3 py-2 text-sm focus:border-primary focus:outline-none"
                value={selectedScenarioId}
                onChange={e => setSelectedScenarioId(e.target.value)}
              >
                {scenarios.map(s => (
                  <option key={s.id} value={s.id}>{s.name} ({s.category})</option>
                ))}
              </select>
              {selectedScenario && (
                <p className="text-xs text-muted-foreground mt-1">{selectedScenario.description}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold">Target Agent</label>
              {loadingAgents ? (
                <div className="text-xs text-muted-foreground py-2">Loading workspace agents...</div>
              ) : agents.length === 0 ? (
                <div className="p-3 bg-surface border border-border rounded-md text-xs text-muted-foreground">
                  No active agents found in workspace. The sandbox will provision an ephemeral test agent fixture automatically.
                </div>
              ) : (
                <select 
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-sm focus:border-primary focus:outline-none"
                  value={selectedAgentId}
                  onChange={e => setSelectedAgentId(e.target.value)}
                >
                  {agents.map((a: Agent) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.type} - {a.status})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="pt-4 border-t border-border flex justify-end gap-3">
              <Button variant="outline" onClick={onClose} disabled={runTestMutation.isPending}>Cancel</Button>
              <Button onClick={handleLaunch} disabled={runTestMutation.isPending} className="bg-primary text-primary-foreground shadow-[0_0_15px_rgba(var(--primary),0.3)]">
                {runTestMutation.isPending ? <Activity className="size-4 mr-2 animate-spin" /> : <Play className="size-4 mr-2" />} 
                Launch Test
              </Button>
            </div>

            <div className="bg-warn/10 border border-warn/20 rounded-xl p-4 flex items-start gap-3 mt-4">
              <AlertTriangle className="size-4 text-warn shrink-0 mt-0.5" />
              <div className="text-sm text-warn/90">
                <strong>Isolated Sandbox.</strong> This scenario executes against genuine FINSHIELD services in a safe, isolated workspace sandbox. No external networks or live financial rails are contacted.
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
