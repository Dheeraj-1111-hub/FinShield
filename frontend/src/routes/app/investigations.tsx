import { useState, useEffect } from "react";
import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { 
  Sparkles, Filter, ArrowUpRight, ArrowRight, ShieldCheck, Clock, CheckCircle2, AlertTriangle, AlertCircle, Search
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { investigationsApi } from "@/api/investigations";
import { agentsApi } from "@/api/agents";
import { InvestigationDetailsDrawer } from "@/components/investigations/InvestigationDetailsDrawer";
import { AIInvestigatorDrawer } from "@/components/investigations/AIInvestigatorDrawer";

interface InvestigationsSearch {
  id?: string | undefined;
  run_id?: string | undefined;
}

export const Route = createFileRoute("/app/investigations")({
  validateSearch: (search: Record<string, unknown>): InvestigationsSearch => {
    return {
      id: typeof search['id'] === 'string' ? search['id'] : undefined,
      run_id: typeof search['run_id'] === 'string' ? search['run_id'] : undefined,
    };
  },
  component: InvestigationsPage,
});

function InvestigationsPage() {
  const routerState = useRouterState();
  const search = Route.useSearch();
  const pathname = routerState.location.pathname;

  // Support child route rendering (e.g. /app/investigations/$id)
  if (pathname !== "/app/investigations" && pathname !== "/app/investigations/") {
    return <Outlet />;
  }

  const { data: investigations = [] } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => investigationsApi.getInvestigations(),
    refetchInterval: 3000,
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list
  });

  const [selectedInvestigation, setSelectedInvestigation] = useState<any | null>(null);
  const [isAIOpen, setIsAIOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'IN_REVIEW' | 'RESOLVED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (investigations.length > 0 && !selectedInvestigation) {
      if (search.id) {
        const found = investigations.find(i => i.id === search.id);
        if (found) setSelectedInvestigation(found);
      } else if (search.run_id) {
        const found = investigations.find(i => i.agent_run_id === search.run_id);
        if (found) setSelectedInvestigation(found);
      }
    }
  }, [investigations, search.id, search.run_id, selectedInvestigation]);

  const openCount = investigations.filter(i => i.status === 'OPEN').length;
  const criticalCount = investigations.filter(i => i.priority === 'CRITICAL').length;
  const highRiskCount = investigations.filter(i => i.priority === 'HIGH' || (i as any).severity === 'HIGH').length;
  const resolvedCount = investigations.filter(i => i.status === 'RESOLVED').length;

  const filteredInvestigations = investigations.filter(inv => {
    if (statusFilter === 'OPEN' && inv.status !== 'OPEN') return false;
    if (statusFilter === 'IN_REVIEW' && inv.status !== 'IN_REVIEW') return false;
    if (statusFilter === 'RESOLVED' && inv.status !== 'RESOLVED') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = inv.id?.toLowerCase().includes(q);
      const matchTitle = inv.title?.toLowerCase().includes(q);
      const matchDesc = inv.description?.toLowerCase().includes(q);
      const matchAgent = inv.agent_id?.toLowerCase().includes(q);
      if (!matchId && !matchTitle && !matchDesc && !matchAgent) return false;
    }
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2">Investigations</h1>
          <p className="text-muted-foreground font-medium">
            Investigate suspicious autonomous activity, trace agent decisions, and understand exactly why FINSHIELD allowed, reviewed, or blocked an action.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button variant="outline" className="border-border bg-background">
            <Filter className="size-4 mr-2" />
            Filter
          </Button>
          <Button onClick={() => setIsAIOpen(true)} className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_15px_rgba(var(--primary),0.3)]">
            <Sparkles className="size-4 mr-2" />
            AI Investigator
          </Button>
        </div>
      </div>

      {/* 2. KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Open Cases</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{openCount}</div>
          <div className="text-sm text-danger font-medium flex items-center gap-1">
            <AlertCircle className="size-4" /> {criticalCount} critical
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">High Risk</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{highRiskCount}</div>
          <div className="text-sm text-warn font-medium flex items-center gap-1">
            <ArrowUpRight className="size-4" /> active
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Resolved</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{resolvedCount}</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <CheckCircle2 className="size-4" /> completed
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Total Investigations</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">
            {investigations.length}
          </div>
          <div className="text-sm text-safe font-medium">
            total tracked
          </div>
        </Card>
      </div>

      {/* 3. Investigation Queue */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-bold tracking-tight uppercase tracking-wider">Investigation Queue</h2>
            <div className="flex bg-surface border border-border rounded-md text-sm font-medium p-0.5">
              <button
                type="button"
                onClick={() => setStatusFilter('ALL')}
                className={`px-3 py-1 rounded transition-colors ${statusFilter === 'ALL' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                All {investigations.length}
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('OPEN')}
                className={`px-3 py-1 rounded transition-colors ${statusFilter === 'OPEN' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Open {openCount}
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('IN_REVIEW')}
                className={`px-3 py-1 rounded transition-colors ${statusFilter === 'IN_REVIEW' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Investigating
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter('RESOLVED')}
                className={`px-3 py-1 rounded transition-colors ${statusFilter === 'RESOLVED' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Resolved {resolvedCount}
              </button>
            </div>
          </div>
          <div className="relative">
            <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search investigations..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 bg-surface border border-border rounded-md pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:border-primary transition-colors"
            />
          </div>
        </div>

        <Card className="bg-surface border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-raised border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground w-12">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Investigation</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Agent</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Event</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Value</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredInvestigations.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-muted-foreground">
                    {searchQuery || statusFilter !== 'ALL' ? 'No matching investigations found.' : 'No activity yet.'}
                  </td>
                </tr>
              ) : filteredInvestigations.map((inv) => {
                const agent = agents.find(a => a.id === inv.agent_id);
                return (
                  <tr key={inv.id} className="hover:bg-surface-raised transition-colors cursor-pointer group" onClick={() => setSelectedInvestigation(inv)}>
                    <td className="px-4 py-3 text-center">
                      <div className={`size-2.5 rounded-full mx-auto shadow-[0_0_8px_currentColor] ${
                        inv.priority === 'CRITICAL' ? 'bg-danger text-danger' :
                        inv.priority === 'HIGH' ? 'bg-warn text-warn' :
                        inv.priority === 'MEDIUM' ? 'bg-yellow-500 text-yellow-500' :
                        'bg-safe text-safe'
                      }`} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold font-mono text-muted-foreground group-hover:text-primary transition-colors">{inv.id}</div>
                      <div className="font-medium text-foreground">{inv.title}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-muted-foreground">{agent?.name || inv.agent_id || 'Unknown'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-muted-foreground max-w-[200px] truncate">{inv.description}</div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                      -
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                        inv.status === 'OPEN' ? 'bg-danger/10 text-danger border-danger/20' :
                        inv.status === 'IN_REVIEW' ? 'bg-warn/10 text-warn border-warn/20' :
                        inv.status === 'RESOLVED' ? 'bg-safe/10 text-safe border-safe/20' :
                        'bg-surface-raised text-muted-foreground border-border'
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground whitespace-nowrap">
                      {inv.updated_at ? new Date(inv.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Just now'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* 4. Recent Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recent Investigation Activity</h2>
            <Button variant="link" className="text-primary text-xs h-auto p-0">View all →</Button>
          </div>
            <Card className="bg-surface border-border overflow-hidden p-0">
            <div className="divide-y divide-border text-sm">
              {[] as any[]}
              <div className="p-4 text-center text-muted-foreground text-sm">
                No recent activity.
              </div>
            </div>
          </Card>
        </div>

        {/* 5. Performance Metrics */}
        <div className="space-y-4">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Investigation Performance</h2>
          <div className="grid grid-cols-2 gap-4">
            <Card className="p-4 bg-surface border-border flex flex-col gap-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Clock className="size-3.5" /> Avg investigation</div>
              <div className="text-xl font-bold font-mono">0m</div>
            </Card>
            <Card className="p-4 bg-surface border-border flex flex-col gap-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Sparkles className="size-3.5" /> AI-assisted</div>
              <div className="text-xl font-bold font-mono">0%</div>
            </Card>
            <Card className="p-4 bg-surface border-border flex flex-col gap-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5"><CheckCircle2 className="size-3.5" /> Avg resolution</div>
              <div className="text-xl font-bold font-mono">0m</div>
            </Card>
            <Card className="p-4 bg-surface border-border flex flex-col gap-1">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5"><ShieldCheck className="size-3.5" /> Containment</div>
              <div className="text-xl font-bold font-mono text-safe">100%</div>
            </Card>
          </div>
        </div>

      </div>

      {/* Drawers */}
      {selectedInvestigation && (
        <InvestigationDetailsDrawer 
          investigation={{
            ...selectedInvestigation,
            severity: selectedInvestigation.severity || selectedInvestigation.priority || 'CRITICAL',
            agentName: agents.find(a => a.id === selectedInvestigation.agent_id)?.name || selectedInvestigation.agent_id || 'Finshield Agent',
            agentId: selectedInvestigation.agent_id || 'AGT-SYSTEM',
            value: selectedInvestigation.value || 0,
            detectedAt: selectedInvestigation.created_at || new Date().toISOString(),
            riskScore: selectedInvestigation.risk_score || (selectedInvestigation.priority === 'CRITICAL' ? 85 : 45),
            confidence: selectedInvestigation.confidence || 98,
            intentAlignment: typeof selectedInvestigation.intent_alignment === 'number'
              ? selectedInvestigation.intent_alignment
              : (selectedInvestigation.divergence_signals && selectedInvestigation.divergence_signals.length > 0 ? 0 : 100),
            originalIntent: selectedInvestigation.original_intent || 'Intent context not recorded',
            executedIntent: selectedInvestigation.executed_intent || selectedInvestigation.proposed_action || 'pay_order for bound order',
            proposedAction: selectedInvestigation.proposed_action || selectedInvestigation.executed_intent || 'pay_order',
            decisionReason: selectedInvestigation.decision_reason || selectedInvestigation.description || 'Action was rejected by approver.',
            outcome: selectedInvestigation.outcome || (selectedInvestigation.description?.includes('rejected by approver') ? 'REJECTED' : 'BLOCKED'),
            divergenceSignals: selectedInvestigation.divergence_signals || [],
            alignmentSignals: selectedInvestigation.alignment_signals || [],
            trajectory: selectedInvestigation.trajectory || [
              {
                time: new Date(selectedInvestigation.created_at || Date.now()).toLocaleTimeString(),
                source: 'FINSHIELD EVALUATION',
                description: selectedInvestigation.title || 'Action Blocked by Gate',
                status: 'BLOCKED',
                isTerminal: true
              }
            ],
            policiesTriggered: selectedInvestigation.policies_triggered || [
              {
                name: 'Action Gate Enforcement',
                decision: 'BLOCK'
              }
            ],
            evidence: selectedInvestigation.evidence || [
              {
                id: selectedInvestigation.source_id || selectedInvestigation.id,
                type: 'GATE_DECISION',
                description: selectedInvestigation.description || 'Action Gate Block'
              }
            ]
          }} 
          onClose={() => setSelectedInvestigation(null)} 
        />
      )}
      
      {isAIOpen && (
        <AIInvestigatorDrawer 
          onClose={() => setIsAIOpen(false)} 
        />
      )}

    </div>
  );
}
