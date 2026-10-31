import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, CheckCircle2, AlertTriangle, ShieldAlert, Activity, Bug, Database, ShieldCheck, Terminal, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSecurityTestRun } from "@/hooks/useSecurityLab";

export const Route = createFileRoute("/app/lab/$runId")({
  component: SecurityTestDetailsPage,
});

function SecurityTestDetailsPage() {
  const { runId } = Route.useParams();
  const { data: testRun, isLoading, isError: isQueryError, error: queryError, refetch } = useSecurityTestRun(runId);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 p-8">
        <Button variant="ghost" className="w-fit -ml-4 text-muted-foreground" asChild>
          <Link to="/app/lab">
            <ArrowLeft className="size-4 mr-2" /> Back to Security Lab
          </Link>
        </Button>
        <div className="p-12 text-center text-muted-foreground animate-pulse">Loading test run {runId}...</div>
      </div>
    );
  }

  if (isQueryError) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 p-8">
        <Button variant="ghost" className="w-fit -ml-4 text-muted-foreground" asChild>
          <Link to="/app/lab">
            <ArrowLeft className="size-4 mr-2" /> Back to Security Lab
          </Link>
        </Button>
        <Card className="p-8 border-danger/30 bg-danger/5 text-center space-y-3">
          <AlertTriangle className="size-8 text-danger mx-auto" />
          <h2 className="text-lg font-bold text-danger">Failed to Load Test Run Details</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            {(queryError as any)?.response?.data?.error?.message || (queryError as any)?.message || "Could not retrieve details for this test run."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-2">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  if (!testRun) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 p-8">
        <Button variant="ghost" className="w-fit -ml-4 text-muted-foreground" asChild>
          <Link to="/app/lab">
            <ArrowLeft className="size-4 mr-2" /> Back to Security Lab
          </Link>
        </Button>
        <Card className="p-8 text-center text-muted-foreground">Test run #{runId} not found.</Card>
      </div>
    );
  }

  const isFailedOrPartial = testRun.status === 'FAILED' || testRun.status === 'PARTIAL';
  const isRunning = testRun.status === 'QUEUED' || testRun.status === 'RUNNING';
  const isError = testRun.status === 'ERROR';
  const isPassed = testRun.status === 'PASSED';

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12">
      
      {/* Header */}
      <div className="flex flex-col gap-4">
        <Button variant="ghost" className="w-fit -ml-4 text-muted-foreground" asChild>
          <Link to="/app/lab">
            <ArrowLeft className="size-4 mr-2" /> Back to Security Lab
          </Link>
        </Button>
        <div>
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold tracking-wider border uppercase ${
              isFailedOrPartial ? 'bg-danger/10 text-danger border-danger/30' : 
              isError ? 'bg-amber-500/10 text-amber-500 border-amber-500/30' :
              isRunning ? 'bg-warn/10 text-warn border-warn/20' :
              'bg-safe/10 text-safe border-safe/20'
            }`}>
              {isFailedOrPartial ? <AlertTriangle className="size-3" /> : 
               isError ? <AlertTriangle className="size-3 text-amber-500" /> :
               isRunning ? <Activity className="size-3 animate-pulse" /> : 
               <CheckCircle2 className="size-3" />}
              {isFailedOrPartial ? 'FAILED (VULNERABILITY DETECTED)' : 
               isError ? 'ERROR (INCONCLUSIVE)' : 
               isPassed ? 'PASSED (DEFENSE VERIFIED)' : 
               testRun.status}
            </div>
            <div className="text-xs font-bold tracking-wider text-muted-foreground uppercase font-mono">
              {testRun.id}
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            {testRun.scenario?.name || testRun.scenario_id}
          </h1>
          <p className="text-muted-foreground mt-1 text-sm max-w-2xl">
            {testRun.scenario?.description}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Target Component</div>
          <div className="font-mono text-sm">{testRun.scenario?.target_component || 'Unknown'}</div>
        </Card>
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Target Agent</div>
          <div className="font-mono text-sm">{testRun.target_agent_id ? `#${testRun.target_agent_id.slice(0, 12)}` : 'Auto-provisioned'}</div>
        </Card>
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Initiated By</div>
          <div className="font-mono text-sm">#{testRun.initiated_by.slice(0, 12)}</div>
        </Card>
      </div>

      {/* Summary Banner with explicit PASSED / FAILED / ERROR semantic separation */}
      {!isRunning && testRun.summary && (
        <div className={`border rounded-xl p-6 text-center ${
          isFailedOrPartial ? 'bg-danger/5 border-danger/30' : 
          isError ? 'bg-amber-500/5 border-amber-500/30' : 
          'bg-safe/5 border-safe/20'
        }`}>
          <div className={`text-xs font-bold tracking-wider uppercase mb-2 ${
            isFailedOrPartial ? 'text-danger' : 
            isError ? 'text-amber-500' : 
            'text-safe'
          }`}>
            {isFailedOrPartial ? 'Vulnerability Detected (FAILED)' : 
             isError ? 'Execution Inconclusive (ERROR) — Defense Invariants Not Proven' : 
             'Defense Verified (PASSED)'}
          </div>
          <div className="text-3xl font-bold font-mono mb-4 flex justify-center items-center gap-2">
            {isFailedOrPartial ? <AlertTriangle className="size-7 text-danger" /> : 
             isError ? <AlertTriangle className="size-7 text-amber-500" /> : 
             <ShieldAlert className="size-7 text-safe" />}
            {testRun.status}
          </div>
          <p className="text-sm text-foreground/90 max-w-2xl mx-auto leading-relaxed">
            {testRun.summary}
          </p>
        </div>
      )}

      {/* Security Findings Banner if present */}
      {testRun.findings && testRun.findings.length > 0 && (
        <div className="space-y-4">
          <div className="text-xs font-semibold text-danger uppercase tracking-wider flex items-center gap-2">
            <Bug className="size-4" /> Detected Security Findings ({testRun.findings.length})
          </div>
          {testRun.findings.map(finding => (
            <Card key={finding.id} className="p-5 border-danger/30 bg-danger/5">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-sm text-danger">{finding.title}</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-danger/20 text-danger">
                  {finding.severity}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">{finding.description}</p>
              <div className="text-xs font-mono space-y-1">
                <div><strong>Component:</strong> {finding.affected_component}</div>
                <div><strong>Observed:</strong> {finding.observed_behavior}</div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Trajectory / Execution Steps with Evidence Matrix */}
      <div>
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center justify-between">
          <span>Execution Trajectory & Evidence Matrix</span>
          <span className="text-[11px] text-muted-foreground font-normal">Derived from verified database state & enforcement telemetry</span>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6 relative">
          <div className="absolute left-[79px] top-8 bottom-8 w-px bg-border z-0" />
          
          <div className="space-y-6 relative z-10">
            {testRun.steps && testRun.steps.length > 0 ? (
              testRun.steps.map((step) => {
                const stepFailed = step.result === 'FAIL';
                const stepError = step.result === 'ERROR';
                const stepPassed = step.result === 'PASS';
                const stepMeta = (step as any).metadata_ || (step as any).metadata || {};
                const dbEvidence = stepMeta.database_evidence;
                const assertions = stepMeta.assertions;
                const boundary = stepMeta.enforcement_boundary;
                const attack = stepMeta.attack_attempted;
                const observedResp = stepMeta.observed_response;
                const cleanup = stepMeta.cleanup_result;

                return (
                  <div key={step.id} className="flex gap-4 group">
                    <div className="w-12 text-right pt-1 shrink-0">
                      <div className="text-xs font-mono text-muted-foreground">
                        {step.started_at ? new Date(step.started_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}) : '--:--'}
                      </div>
                    </div>
                    <div className="pt-1.5 shrink-0">
                      <div className={`size-3 rounded-full border-2 bg-background ${
                        stepFailed ? 'border-danger shadow-[0_0_8px_rgba(239,68,68,0.5)]' :
                        stepError ? 'border-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]' :
                        stepPassed ? 'border-safe shadow-[0_0_8px_rgba(34,197,94,0.5)]' :
                        'border-primary animate-pulse'
                      }`} />
                    </div>
                    <div className="flex-1 pb-2 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-sm ${
                          stepFailed ? 'font-bold text-danger' : 
                          stepError ? 'font-bold text-amber-500' :
                          stepPassed ? 'font-bold text-safe' : 
                          'font-medium text-muted-foreground'
                        }`}>
                          {step.step_type}
                        </span>
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase font-bold ${
                          stepPassed ? 'text-safe border-safe/30 bg-safe/10' :
                          stepFailed ? 'text-danger border-danger/30 bg-danger/10' :
                          stepError ? 'text-amber-500 border-amber-500/30 bg-amber-500/10' :
                          'text-muted-foreground border-border'
                        }`}>
                          {step.result}
                        </span>
                        {boundary && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">
                            <Layers className="size-3" /> Boundary: {boundary}
                          </span>
                        )}
                      </div>

                      <div className="text-xs text-muted-foreground">
                        <strong>Expected:</strong> {step.expected_behavior}
                      </div>

                      {step.observed_behavior && (
                        <div className={`text-xs ${stepError ? 'text-amber-500 font-medium' : stepFailed ? 'text-danger font-medium' : 'text-muted-foreground'}`}>
                          <strong>Observed:</strong> {step.observed_behavior}
                        </div>
                      )}

                      {/* Attack Payload & Target Details */}
                      {attack && (
                        <div className="p-2.5 bg-surface-raised rounded text-[11px] font-mono border border-border/60">
                          <div className="flex items-center gap-1.5 text-foreground/80 font-semibold mb-1">
                            <Terminal className="size-3 text-primary" />
                            <span>Attack Vector Attempted:</span>
                          </div>
                          <div className="text-muted-foreground overflow-x-auto">
                            {typeof attack === 'object' ? JSON.stringify(attack, null, 2) : String(attack)}
                          </div>
                        </div>
                      )}

                      {/* Observed Response Telemetry */}
                      {observedResp && (
                        <div className="p-2.5 bg-surface-raised rounded text-[11px] font-mono border border-border/60">
                          <span className="text-foreground/80 font-semibold block mb-1">Enforcement Boundary Response:</span>
                          <div className="text-muted-foreground overflow-x-auto">
                            {typeof observedResp === 'object' ? JSON.stringify(observedResp, null, 2) : String(observedResp)}
                          </div>
                        </div>
                      )}

                      {/* Database State Evidence (Pre vs Post State Diffs) */}
                      {dbEvidence && (dbEvidence.baseline_state || dbEvidence.diff) && (
                        <div className="p-3 bg-surface-raised rounded text-[11px] font-mono border border-border/60 space-y-2">
                          <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
                            <span className="text-foreground/90 font-semibold flex items-center gap-1.5">
                              <Database className="size-3.5 text-primary" /> Database State Differential Evidence:
                            </span>
                            <span className="text-[10px] text-muted-foreground">Pre-Attack vs Post-Attack</span>
                          </div>
                          <div className="grid grid-cols-4 gap-2 text-center text-[10px] bg-background/50 p-2 rounded border border-border/30">
                            <div className="font-semibold text-muted-foreground text-left">Entity</div>
                            <div className="font-semibold text-muted-foreground">Baseline</div>
                            <div className="font-semibold text-muted-foreground">Post-Attack</div>
                            <div className="font-semibold text-muted-foreground">Leaked (Δ)</div>
                            
                            <div className="text-left font-sans text-muted-foreground">Payment Intents</div>
                            <div>{dbEvidence.baseline_state?.payments_count ?? '-'}</div>
                            <div>{dbEvidence.post_attack_state?.payments_count ?? '-'}</div>
                            <div className={(dbEvidence.diff?.payments_leaked ?? 0) > 0 ? "text-danger font-bold" : "text-safe font-semibold"}>
                              +{dbEvidence.diff?.payments_leaked ?? 0}
                            </div>

                            <div className="text-left font-sans text-muted-foreground">Carts</div>
                            <div>{dbEvidence.baseline_state?.carts_count ?? '-'}</div>
                            <div>{dbEvidence.post_attack_state?.carts_count ?? '-'}</div>
                            <div className={(dbEvidence.diff?.carts_leaked ?? 0) > 0 ? "text-danger font-bold" : "text-safe font-semibold"}>
                              +{dbEvidence.diff?.carts_leaked ?? 0}
                            </div>

                            <div className="text-left font-sans text-muted-foreground">Orders Created</div>
                            <div>{dbEvidence.baseline_state?.orders_count ?? '-'}</div>
                            <div>{dbEvidence.post_attack_state?.orders_count ?? '-'}</div>
                            <div className={(dbEvidence.diff?.orders_created ?? 0) > 0 ? "text-warn font-semibold" : "text-safe font-semibold"}>
                              +{dbEvidence.diff?.orders_created ?? 0}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Security Invariant Assertions Checklist */}
                      {assertions && Object.keys(assertions).length > 0 && (
                        <div className="p-3 bg-surface-raised rounded text-[11px] font-mono border border-border/60">
                          <span className="text-foreground/90 font-semibold flex items-center gap-1.5 mb-2">
                            <ShieldCheck className="size-3.5 text-safe" /> Verified Security Invariants:
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                            {Object.entries(assertions).map(([k, v]) => (
                              <div key={k} className="flex items-center gap-1.5 text-[11px] p-1 rounded bg-background/40">
                                <span className={v ? "text-safe font-bold" : "text-danger font-bold"}>
                                  {v ? "✓" : "✗"}
                                </span>
                                <span className="text-muted-foreground truncate">{k.replace(/_/g, ' ')}:</span>
                                <span className={v ? "text-safe font-semibold ml-auto" : "text-danger font-semibold ml-auto"}>
                                  {String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Cleanup / Teardown Verification */}
                      {cleanup && (
                        <div className="p-2 bg-surface-raised rounded text-[11px] font-mono border border-border/40 flex items-center justify-between text-muted-foreground">
                          <span>Teardown Cleanup:</span>
                          <span className={cleanup.cleanup_ok ? "text-safe font-semibold" : "text-danger font-semibold"}>
                            {cleanup.cleanup_ok ? "✓ Purged sandbox fixtures (historical data preserved)" : "✗ Teardown warning"}
                          </span>
                        </div>
                      )}

                      {/* Execution Error Details */}
                      {stepMeta.error && (
                        <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded text-[11px] font-mono text-amber-500 overflow-x-auto">
                          <span className="font-semibold uppercase tracking-wider text-[10px] block mb-1">Execution / Diagnostic Error</span>
                          {String(stepMeta.error)}
                        </div>
                      )}

                      {step.input_data && Object.keys(step.input_data).length > 0 && (
                        <div className="p-2 bg-surface-raised rounded text-[11px] font-mono text-muted-foreground overflow-x-auto">
                          <span className="text-foreground/70 font-semibold">Inputs:</span> {JSON.stringify(step.input_data)}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center text-sm text-muted-foreground py-4">No steps recorded yet.</div>
            )}
            
            {isRunning && (
               <div className="flex gap-4 group">
                 <div className="w-12 text-right pt-1 shrink-0"></div>
                 <div className="pt-1.5 shrink-0">
                   <div className="size-3 rounded-full border-2 bg-background border-border animate-pulse" />
                 </div>
                 <div className="flex-1 pb-2 text-sm font-medium text-muted-foreground">
                   Executing genuine sandbox security verification...
                 </div>
               </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
