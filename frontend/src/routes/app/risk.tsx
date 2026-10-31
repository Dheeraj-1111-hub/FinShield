import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { 
  ShieldAlert, ShieldCheck, Download, Filter, TrendingDown,
  ArrowRight, XCircle, AlertTriangle, CheckCircle2, MoreHorizontal, Activity, Bot
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { agentsApi } from "@/api/agents";
import { ThreatDetailsDrawer } from "@/components/risk/ThreatDetailsDrawer";
import { RiskSimulator } from "@/components/risk/RiskSimulator";
import { useQuery } from "@tanstack/react-query";
import { riskApi, RiskAssessment } from "@/api/risk";

export const Route = createFileRoute("/app/risk")({
  component: RiskCenterPage,
});

function RiskCenterPage() {
  const [selectedThreat, setSelectedThreat] = useState<RiskAssessment | null>(null);

  const { data: assessments = [] } = useQuery({
    queryKey: ['risk_assessments'],
    queryFn: () => riskApi.getAssessments()
  });

  const { data: summary } = useQuery({
    queryKey: ['risk-summary'],
    queryFn: riskApi.getSummary
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list
  });

  // Group events by severity
  const activeThreats = assessments.filter(a => a.risk_level === 'CRITICAL' || a.risk_level === 'HIGH');

  // Helper for agent names
  const getAgentName = (id?: string | null) => {
    if (!id) return 'Unknown Agent';
    const agent = agents.find(a => a.id === id);
    return agent ? agent.name : id;
  };

  const getRiskColor = (level: string) => {
    switch(level) {
      case 'CRITICAL': return "text-danger bg-danger/10 border-danger/20";
      case 'HIGH': return "text-warn bg-warn/10 border-warn/20";
      case 'MEDIUM': return "text-blue-500 bg-blue-500/10 border-blue-500/20";
      default: return "text-safe bg-safe/10 border-safe/20";
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2">Risk Center</h1>
          <p className="text-muted-foreground font-medium">Deterministic evaluation engine monitoring transaction and behavioral risk.</p>
        </div>
        <div className="flex items-center gap-3">
          <RiskSimulator />
          <Button variant="outline" className="border-border bg-background">
            <Download className="size-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" className="border-border bg-background">
            <Filter className="size-4 mr-2" />
            Filter
          </Button>
        </div>
      </div>

      {/* 2. Security Summary (KPI Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Total Assessments</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">
            {summary?.total_assessments || 0}
          </div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            Engine active
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm cursor-pointer hover:border-primary/50 transition-colors">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Active Threats</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{(summary?.critical || 0) + (summary?.high || 0)}</div>
          <div className="text-sm text-muted-foreground">
            <span className="text-danger font-medium">{summary?.critical || 0} critical</span>, <span className="text-warn font-medium">{summary?.high || 0} high</span>
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">High Risk Rate</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{summary?.high_risk_rate || 0}%</div>
          <div className="text-sm text-muted-foreground font-medium">
            of recent transactions
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Average Risk Score</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">
            {summary?.average_score || 0}
          </div>
          <div className="text-sm text-muted-foreground font-medium">
            Out of 100
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (2/3 width) */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Active Threats */}
          {activeThreats.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <ShieldAlert className="size-5 text-danger" />
                Active Threats
              </h2>
              
              <div className="grid gap-3">
                {activeThreats.map((assessment) => (
                  <div 
                    key={assessment.id} 
                    onClick={() => setSelectedThreat(assessment)}
                    className="flex flex-col sm:flex-row gap-4 p-4 border border-danger/30 bg-danger/5 rounded-lg hover:bg-danger/10 cursor-pointer transition-colors"
                  >
                    <div className="mt-1">
                      {assessment.risk_level === 'CRITICAL' ? (
                        <XCircle className="size-6 text-danger" />
                      ) : (
                        <AlertTriangle className="size-6 text-warn" />
                      )}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-foreground flex items-center gap-2">
                          {getAgentName(assessment.agent_id)}
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${getRiskColor(assessment.risk_level)}`}>
                            {assessment.risk_level}
                          </span>
                        </div>
                        <div className="text-sm font-mono text-muted-foreground">
                          Score: {assessment.risk_score}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {assessment.decision_hint === 'BLOCK_AND_ALERT' ? 'Action blocked due to critical risk.' : 'Action flagged for human review.'}
                      </p>
                    </div>
                    <div className="flex items-center">
                      <ArrowRight className="size-5 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assessment Log */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Activity className="size-5 text-muted-foreground" />
              Risk Engine Log
            </h2>
            <Card className="border-border bg-surface overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/20">
                      <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase text-xs tracking-wider">Timestamp</th>
                      <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase text-xs tracking-wider">Agent</th>
                      <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase text-xs tracking-wider">Type</th>
                      <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase text-xs tracking-wider">Level</th>
                      <th className="px-4 py-3 text-left font-semibold text-muted-foreground uppercase text-xs tracking-wider">Score</th>
                      <th className="px-4 py-3 text-right"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {assessments.map((a) => (
                      <tr 
                        key={a.id} 
                        onClick={() => setSelectedThreat(a)}
                        className="hover:bg-muted/10 transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">
                          {new Date(a.created_at).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-3 font-medium">
                          {getAgentName(a.agent_id)}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {a.assessment_type}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${getRiskColor(a.risk_level)}`}>
                            {a.risk_level}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-muted-foreground">
                          {a.risk_score}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {assessments.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                          No risk assessments logged yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

        </div>
        
        {/* Right Column (1/3 width) - Posture & Rules */}
        <div className="space-y-6">
          <Card className="p-5 border-border bg-surface shadow-sm">
            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <ShieldCheck className="size-5 text-safe" />
              Engine Subsystems
            </h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-5 text-safe shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-sm">Intent Alignment</div>
                  <div className="text-xs text-muted-foreground mt-1">Evaluating actions against delegated intents (Phase 8).</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-5 text-safe shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-sm">Authority Bounds</div>
                  <div className="text-xs text-muted-foreground mt-1">Verifying limits and transactional capacities.</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-5 text-safe shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-sm">Transaction Assessment</div>
                  <div className="text-xs text-muted-foreground mt-1">Analyzing absolute sizes against dynamic heuristics.</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="size-5 text-safe shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-sm">Velocity & Behavior</div>
                  <div className="text-xs text-muted-foreground mt-1">Detecting high-frequency or erratic agent sequences.</div>
                </div>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <div className="text-xs font-mono text-muted-foreground">
                Engine version: det-1.0.0
                <br/>Scoring version: v1
              </div>
            </div>
          </Card>
        </div>

      </div>

      <ThreatDetailsDrawer 
        open={selectedThreat !== null} 
        onOpenChange={(open) => !open && setSelectedThreat(null)}
        assessment={selectedThreat}
      />
    </div>
  );
}
