import { useState } from "react";
import { createFileRoute, useNavigate, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { 
  ShieldAlert, Activity, ArrowUpRight, Plus, FlaskConical, AlertTriangle, CheckCircle2, ArrowRight,
  ShieldCheck, MinusCircle, Shield, Eye, Layers, BarChart3, RefreshCw
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSecurityScenarios, useSecurityTestRuns, useSecurityBenchmark } from "@/hooks/useSecurityLab";
import { SecurityTestDrawer } from "@/components/lab/SecurityTestDrawer";

export const Route = createFileRoute("/app/lab")({
  component: SecurityLabPage,
});

function SecurityLabPage() {
  const routerState = useRouterState();
  const pathname = routerState.location.pathname;

  // Support child route rendering (e.g. /app/lab/$runId)
  if (pathname !== "/app/lab" && pathname !== "/app/lab/") {
    return <Outlet />;
  }

  const [selectedScenarioSlug, setSelectedScenarioSlug] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'benchmark' | 'scenarios'>('benchmark');
  
  const navigate = useNavigate();

  const { 
    data: scenarios = [], 
    isLoading: loadingScenarios, 
    isError: isScenariosError, 
    error: scenariosError,
    refetch: refetchScenarios 
  } = useSecurityScenarios();

  const { 
    data: testRuns = [], 
    isLoading: loadingRuns, 
    isError: isRunsError, 
    error: runsError,
    refetch: refetchRuns 
  } = useSecurityTestRuns();

  const {
    data: benchmark,
    isLoading: loadingBenchmark,
    isError: isBenchmarkError,
    refetch: refetchBenchmark
  } = useSecurityBenchmark();

  const handleRunTest = (slug: string) => {
    setSelectedScenarioSlug(slug);
  };

  const handleCloseDrawer = () => {
    setSelectedScenarioSlug(null);
  };

  // Derive verified metrics from the benchmark layer (with fallback to client calculations)
  const totalRuns = benchmark?.total_runs ?? testRuns.length;
  const verifiedRuns = benchmark?.verified_runs ?? testRuns.filter(r => r.status === 'PASSED' || r.status === 'FAILED').length;
  const passedDefenses = benchmark?.passed_defenses ?? testRuns.filter(r => r.status === 'PASSED').length;
  const failedDefenses = benchmark?.failed_defenses ?? testRuns.filter(r => r.status === 'FAILED').length;
  const inconclusiveRuns = benchmark?.inconclusive_runs ?? testRuns.filter(r => r.status === 'ERROR').length;
  const activeRuns = benchmark?.active_runs ?? testRuns.filter(r => r.status === 'QUEUED' || r.status === 'RUNNING').length;
  
  // Defense Rate formula = PASSED / (PASSED + FAILED), excluding inconclusive runs.
  // When verifiedRuns is 0, defenseRate is null to avoid misleading 0% or 100%.
  const defenseRatePercentage = benchmark?.defense_rate_percentage ?? (
    verifiedRuns > 0 ? Math.round((passedDefenses / verifiedRuns) * 100) : null
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2 flex items-center gap-2">
            <FlaskConical className="size-6 text-primary" />
            Security Lab & Benchmark
          </h1>
          <p className="text-muted-foreground font-medium max-w-2xl text-sm">
            Adversarial evaluation layer for autonomous financial agents. Validates deterministic enforcement boundaries, verifies database side effects, and measures real agent resilience.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => { refetchBenchmark(); refetchRuns(); }}
            className="text-xs"
            title="Refresh Benchmark"
          >
            <RefreshCw className="size-3.5 mr-1.5" /> Refresh
          </Button>
          <Button 
            onClick={() => handleRunTest(scenarios[0]?.slug ?? '')} 
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_15px_rgba(var(--primary),0.3)] text-xs"
          >
            <Plus className="size-4 mr-1.5" />
            New Security Test
          </Button>
        </div>
      </div>

      {/* 2. KPI Cards - Evidence-Derived Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Verified Executions</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{verifiedRuns}</div>
          <div className="text-xs text-muted-foreground font-medium flex items-center gap-1">
            <ArrowUpRight className="size-3.5 text-safe" />
            <span>{totalRuns} total initiated</span>
            {inconclusiveRuns > 0 && (
              <span className="text-amber-500"> · {inconclusiveRuns} inconclusive</span>
            )}
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Defenses Verified</div>
          <div className="text-3xl font-bold font-mono text-safe mb-1">{passedDefenses}</div>
          <div className="text-xs font-medium flex items-center gap-1 text-muted-foreground">
            <ShieldCheck className="size-3.5 text-safe" />
            <span className={failedDefenses > 0 ? "text-danger font-semibold" : "text-muted-foreground"}>
              {failedDefenses} vulnerable / breached
            </span>
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm relative overflow-hidden">
          <div className="absolute right-0 top-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none" />
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Benchmark Defense Rate</div>
          <div className="text-3xl font-bold font-mono text-primary mb-1">
            {defenseRatePercentage !== null ? `${defenseRatePercentage}%` : '—'}
          </div>
          <div className="text-xs text-muted-foreground font-medium">
            {verifiedRuns > 0 ? (
              <span className="text-safe">{passedDefenses}/{verifiedRuns} attacks blocked & verified</span>
            ) : inconclusiveRuns > 0 ? (
              <span className="text-amber-500">{inconclusiveRuns} runs inconclusive (0 verified)</span>
            ) : (
              <span>No verified executions yet</span>
            )}
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Active Evaluations</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{activeRuns}</div>
          <div className="text-xs text-warn font-medium flex items-center gap-1">
            {activeRuns > 0 ? (
              <><Activity className="size-3.5 animate-pulse text-warn" /> Executing in sandbox</>
            ) : (
              <span className="text-muted-foreground">Idle</span>
            )}
          </div>
        </Card>
      </div>

      {/* 3. Navigation View Switcher */}
      <div className="flex border-b border-border gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab('benchmark')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'benchmark'
              ? 'border-primary text-primary font-bold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <BarChart3 className="size-4" />
          Security Benchmark & Invariant Evaluation
          {benchmark?.scenario_evaluations && (
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-surface-raised text-foreground border border-border">
              {benchmark.scenarios_evaluated}/{benchmark.total_scenarios}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('scenarios')}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'scenarios'
              ? 'border-primary text-primary font-bold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Layers className="size-4" />
          Attack Scenario Library
          <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-surface-raised text-muted-foreground border border-border">
            {scenarios.length}
          </span>
        </button>
      </div>

      {/* 4. Main Body: Left Content + Right History Column */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">

          {/* TAB 1: BENCHMARK & INVARIANT EVALUATION */}
          {activeTab === 'benchmark' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold tracking-tight text-foreground">
                    Scenario Defense Verification Matrix
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Verified security invariants, observed enforcement boundaries, and database side-effect diffs.
                  </p>
                </div>
              </div>

              {loadingBenchmark && !benchmark ? (
                <div className="text-center text-muted-foreground py-12 text-sm">
                  Loading benchmark evaluation data...
                </div>
              ) : isBenchmarkError ? (
                <div className="border border-danger/30 bg-danger/5 rounded-xl p-6 text-center space-y-3">
                  <AlertTriangle className="size-6 text-danger mx-auto" />
                  <div className="text-sm font-semibold text-danger">Failed to Load Benchmark Evaluation</div>
                  <Button variant="outline" size="sm" onClick={() => refetchBenchmark()} className="text-xs">
                    Retry
                  </Button>
                </div>
              ) : benchmark?.scenario_evaluations?.length === 0 ? (
                <div className="text-center text-muted-foreground py-12 text-sm border border-border rounded-xl">
                  No scenarios available in the registry.
                </div>
              ) : (
                <div className="space-y-4">
                  {benchmark?.scenario_evaluations?.map((item) => (
                    <Card key={item.scenario_id} className="p-5 border-border bg-surface hover:border-primary/40 transition-colors">
                      
                      {/* Top Header */}
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <h3 className="font-bold text-sm text-foreground">{item.scenario_name}</h3>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                              item.severity === 'CRITICAL' ? 'bg-danger/10 text-danger border-danger/20' : 'bg-warn/10 text-warn border-warn/20'
                            }`}>
                              {item.severity}
                            </span>
                            <span className="text-xs text-muted-foreground font-mono">
                              ({item.category})
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Target: <span className="font-mono text-foreground font-medium">{item.target_component}</span>
                          </div>
                        </div>

                        {/* Defense Status Badge */}
                        <div className="shrink-0">
                          {item.attack_outcome === 'ATTACK_BLOCKED' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-safe/10 text-safe border border-safe/30">
                              <ShieldCheck className="size-3.5" /> Attack Blocked
                            </span>
                          )}
                          {(item.attack_outcome === 'ATTACK_PREVENTED_BY_IMMUTABILITY' || item.attack_outcome === 'TAMPER_DETECTED') && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-safe/10 text-safe border border-safe/30">
                              <ShieldCheck className="size-3.5" /> {item.attack_outcome === 'TAMPER_DETECTED' ? 'Tamper Detected' : 'Immutability Enforced'}
                            </span>
                          )}
                          {item.attack_outcome === 'ATTACK_SUCCEEDED' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-danger/10 text-danger border border-danger/30">
                              <ShieldAlert className="size-3.5" /> Attack Succeeded (Vulnerable)
                            </span>
                          )}
                          {item.attack_outcome === 'INCONCLUSIVE' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                              <AlertTriangle className="size-3.5" /> Inconclusive (Error)
                            </span>
                          )}
                          {item.attack_outcome === 'EVALUATING' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-warn/10 text-warn border border-warn/30 animate-pulse">
                              <Activity className="size-3.5 animate-spin" /> Evaluating...
                            </span>
                          )}
                          {item.attack_outcome === 'UNKNOWN' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                              <AlertTriangle className="size-3.5" /> Unknown Outcome
                            </span>
                          )}
                          {item.attack_outcome === 'UNTESTED' && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">
                              <MinusCircle className="size-3.5" /> Untested
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Expected Security Invariant */}
                      <div className="bg-surface-raised/60 border border-border/60 rounded-md p-3 mb-3 text-xs space-y-1">
                        <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                          <Shield className="size-3 text-primary" /> Expected Security Invariant
                        </div>
                        <div className="text-foreground font-medium leading-relaxed">
                          {item.expected_security_invariant}
                        </div>
                      </div>

                      {/* Observed Enforcement & Evidence */}
                      <div className="text-xs space-y-2 mb-4">
                        {item.observed_result ? (
                          <div>
                            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                              Observed Result & Enforcement
                            </div>
                            <p className="text-foreground/90 font-mono text-[11px] bg-black/20 p-2.5 rounded border border-border/40">
                              {item.observed_result}
                            </p>
                          </div>
                        ) : (
                          <p className="text-muted-foreground italic text-[11px]">
                            No execution observed yet. Launch this scenario to verify enforcement boundary and database invariants.
                          </p>
                        )}

                        {item.evidence_summary && (
                          <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                            {item.enforcement_boundary && (
                              <span className="bg-surface-raised px-2 py-0.5 rounded text-muted-foreground border border-border/50">
                                Boundary: <strong className="text-foreground">{item.enforcement_boundary}</strong>
                              </span>
                            )}
                            {item.evidence_summary.defense_layer && (
                              <span className="bg-surface-raised px-2 py-0.5 rounded text-muted-foreground border border-border/50">
                                Defense Layer: <strong className="text-foreground">{item.evidence_summary.defense_layer}</strong>
                              </span>
                            )}
                            {item.evidence_summary.assertions && (
                              <span className="bg-surface-raised px-2 py-0.5 rounded text-muted-foreground border border-border/50">
                                Invariants: <strong className="text-safe">{Object.values(item.evidence_summary.assertions).filter(Boolean).length}/{Object.keys(item.evidence_summary.assertions).length} verified</strong>
                              </span>
                            )}
                            {item.evidence_summary.database_evidence?.new_unauthorized_payments !== undefined && (
                              <span className="bg-surface-raised px-2 py-0.5 rounded text-muted-foreground border border-border/50">
                                New Payments: <strong className={item.evidence_summary.database_evidence.new_unauthorized_payments === 0 ? "text-safe" : "text-danger"}>{item.evidence_summary.database_evidence.new_unauthorized_payments}</strong>
                              </span>
                            )}
                            {item.evidence_summary.database_evidence?.new_unauthorized_carts !== undefined && (
                              <span className="bg-surface-raised px-2 py-0.5 rounded text-muted-foreground border border-border/50">
                                New Carts: <strong className={item.evidence_summary.database_evidence.new_unauthorized_carts === 0 ? "text-safe" : "text-danger"}>{item.evidence_summary.database_evidence.new_unauthorized_carts}</strong>
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Footer: Runs count, Latest execution time, and Actions */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-border/50 text-xs">
                        <div className="flex items-center gap-3 text-muted-foreground text-[11px]">
                          <span>Verified Runs: <strong className="text-foreground">{item.verified_runs}</strong></span>
                          {item.inconclusive_runs > 0 && <span>Inconclusive: <strong className="text-amber-500">{item.inconclusive_runs}</strong></span>}
                          {item.latest_execution_time && (
                            <span>Latest: <strong className="text-foreground">{new Date(item.latest_execution_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></span>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          {item.latest_run_id && (
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground" asChild>
                              <Link to="/app/lab/$runId" params={{ runId: item.latest_run_id }}>
                                <Eye className="size-3.5 mr-1" /> View Run Evidence
                              </Link>
                            </Button>
                          )}
                          <Button 
                            size="sm" 
                            className="h-7 text-xs bg-surface-raised border border-border text-foreground hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
                            onClick={() => handleRunTest(item.scenario_slug)}
                          >
                            {item.total_runs > 0 ? "Re-evaluate" : "Run Test"} <ArrowRight className="size-3.5 ml-1" />
                          </Button>
                        </div>
                      </div>

                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ATTACK SCENARIO LIBRARY */}
          {activeTab === 'scenarios' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold tracking-tight text-foreground">
                    Available Attack Scenarios
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Select a scenario to configure parameters and launch an isolated test run in the sandbox.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {loadingScenarios ? (
                  <div className="col-span-2 text-center text-muted-foreground py-8 text-sm">Loading scenarios...</div>
                ) : isScenariosError ? (
                  <div className="col-span-2 border border-danger/30 bg-danger/5 rounded-xl p-6 text-center space-y-3">
                    <AlertTriangle className="size-6 text-danger mx-auto" />
                    <div className="text-sm font-semibold text-danger">Failed to Load Security Scenarios</div>
                    <Button variant="outline" size="sm" onClick={() => refetchScenarios()} className="text-xs">
                      Retry
                    </Button>
                  </div>
                ) : scenarios.length === 0 ? (
                  <div className="col-span-2 text-center text-muted-foreground py-8 text-sm">No scenarios available.</div>
                ) : scenarios.map((scenario) => (
                  <Card key={scenario.id} className="p-5 border-border bg-surface hover:border-primary/50 transition-colors flex flex-col justify-between group">
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-bold uppercase tracking-wider text-sm">{scenario.name}</h3>
                        <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                          scenario.severity === 'CRITICAL' ? 'bg-danger/10 text-danger border-danger/20' : 'bg-warn/10 text-warn border-warn/20'
                        }`}>
                          {scenario.severity}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mb-6">
                        {scenario.description}
                      </p>
                    </div>
                    
                    <div className="mt-auto">
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
                        <div>Target: <span className="font-mono text-foreground">{scenario.target_component}</span></div>
                        <div>{scenario.category}</div>
                      </div>
                      <Button 
                        className="w-full bg-surface-raised border border-border text-foreground hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
                        onClick={() => handleRunTest(scenario.slug)}
                      >
                        Run Test <ArrowRight className="size-4 ml-2 group-hover:translate-x-1 transition-transform" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Right Column: Benchmark Summary & Test History */}
        <div className="space-y-8">
          
          {/* Credible Benchmark Defense Score */}
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
              Benchmark Evaluation Index
            </h2>
            <Card className="bg-surface border-border p-5">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-4xl font-bold font-mono text-primary">
                  {defenseRatePercentage !== null ? `${defenseRatePercentage}%` : '—'}
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  {defenseRatePercentage !== null ? `(${passedDefenses}/${verifiedRuns} defenses)` : '(No verified runs)'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mb-4">
                {verifiedRuns > 0 ? (
                  <span>Derived from real database state assertions across {verifiedRuns} verified adversarial tests.</span>
                ) : inconclusiveRuns > 0 ? (
                  <span className="text-amber-500">All {inconclusiveRuns} runs resulted in execution errors and are excluded from the defense rate.</span>
                ) : (
                  <span>Run scenarios to compute evidence-backed defense index. Inconclusive runs are never counted as defenses.</span>
                )}
              </p>
              
              <div className="w-full h-2 bg-surface-raised rounded-full mb-3 overflow-hidden flex">
                <div 
                  className="h-full bg-primary transition-all duration-500" 
                  style={{ width: `${defenseRatePercentage ?? 0}%` }} 
                />
              </div>
              <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
                <span>0% Vulnerable</span>
                <span>100% Defended</span>
              </div>
            </Card>
          </div>

          {/* Recent Test History */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Test History</h2>
              <span className="text-xs text-muted-foreground font-mono">{testRuns.length} runs</span>
            </div>
            
            <div className="space-y-3">
              {loadingRuns ? (
                <div className="text-center text-sm text-muted-foreground py-4">Loading runs...</div>
              ) : isRunsError ? (
                <div className="border border-danger/30 bg-danger/5 rounded-lg p-4 text-center space-y-2">
                  <div className="text-xs font-semibold text-danger">Failed to Load Test History</div>
                  <Button variant="ghost" size="sm" onClick={() => refetchRuns()} className="text-xs h-7">
                    Retry
                  </Button>
                </div>
              ) : testRuns.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground py-4">No recent test runs.</div>
              ) : testRuns.slice(0, 8).map((test) => (
                <Link
                  key={test.id}
                  to="/app/lab/$runId"
                  params={{ runId: test.id }}
                  className="block group"
                >
                  <Card 
                    className={`bg-surface border-border p-4 hover:bg-surface-raised transition-colors cursor-pointer ${
                      test.status === 'FAILED' ? 'border-danger/30 bg-danger/5 hover:bg-danger/10' :
                      test.status === 'ERROR' ? 'border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {test.status === 'PASSED' ? <CheckCircle2 className="size-4 text-safe" /> : 
                         test.status === 'FAILED' ? <AlertTriangle className="size-4 text-danger" /> :
                         test.status === 'ERROR' ? <AlertTriangle className="size-4 text-amber-500" /> :
                         <Activity className="size-4 text-warn animate-pulse" />}
                        <span className="font-mono text-xs font-bold text-muted-foreground">#{test.id.slice(0,8)}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(test.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </span>
                    </div>
                    <div className="text-sm font-medium mb-1 group-hover:text-primary transition-colors">{test.scenario?.name || test.scenario_id}</div>
                    <div className="flex justify-between items-center text-xs font-mono mt-3">
                      <span className={
                        test.status === 'PASSED' ? 'text-safe font-bold' : 
                        test.status === 'FAILED' ? 'text-danger font-bold' : 
                        test.status === 'ERROR' ? 'text-amber-500 font-bold' : 
                        'text-warn'
                      }>
                        {test.status === 'ERROR' ? 'ERROR (INCONCLUSIVE)' : test.status === 'FAILED' ? 'FAILED (VULNERABLE)' : test.status}
                      </span>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Drawer */}
      {selectedScenarioSlug && (
        <SecurityTestDrawer 
          scenarioSlug={selectedScenarioSlug}
          scenarios={scenarios}
          onClose={handleCloseDrawer} 
        />
      )}

    </div>
  );
}
