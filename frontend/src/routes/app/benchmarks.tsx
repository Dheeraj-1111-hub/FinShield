import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { 
  BarChart4, ArrowUpRight, ArrowDownRight, Download, Play, CheckCircle2, ShieldAlert, Sparkles, ChevronDown, Activity
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { BENCHMARK_KPI, COMPARISON_METRICS, SCENARIO_BREAKDOWN, ERROR_ANALYSIS, VERSION_EVOLUTION, RECENT_RUN } from "@/data/mock-benchmarks";
import { BenchmarkRunnerModal } from "@/components/benchmarks/BenchmarkRunnerModal";

export const Route = createFileRoute("/app/benchmarks")({
  component: BenchmarkLabPage,
});

function BenchmarkLabPage() {
  const [isRunnerOpen, setIsRunnerOpen] = useState(false);

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2 flex items-center gap-2">
            <BarChart4 className="size-6 text-primary" />
            Benchmark Lab
          </h1>
          <p className="text-muted-foreground font-medium max-w-2xl">
            Empirical evaluation of FINSHIELD across autonomous financial agent scenarios. Compare its risk detection, decision quality, latency, and financial protection against alternative approaches.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button variant="outline" className="border-border bg-background h-10">
            Dataset: FS-BENCH-v3 (10k) <ChevronDown className="size-4 ml-2 text-muted-foreground" />
          </Button>
          <Button variant="outline" className="border-border bg-background h-10">
            <Download className="size-4 mr-2" /> Export
          </Button>
          <Button onClick={() => setIsRunnerOpen(true)} className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_15px_rgba(var(--primary),0.3)] h-10">
            <Play className="size-4 mr-2" />
            Run Benchmark
          </Button>
        </div>
      </div>

      {/* 2. Executive KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Scenarios Tested</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{BENCHMARK_KPI.scenariosTested.toLocaleString()}</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <ArrowUpRight className="size-4" /> {BENCHMARK_KPI.scenariosDelta.toLocaleString()} this run
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm relative overflow-hidden">
          <div className="absolute right-0 top-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none" />
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Safety Accuracy</div>
          <div className="text-3xl font-bold font-mono text-primary mb-1">{BENCHMARK_KPI.safetyAccuracy}%</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <ArrowUpRight className="size-4" /> {BENCHMARK_KPI.safetyDelta}% vs baseline
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">False Positives</div>
          <div className="text-3xl font-bold font-mono text-foreground mb-1">{BENCHMARK_KPI.falsePositives}%</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <ArrowDownRight className="size-4" /> {Math.abs(BENCHMARK_KPI.falsePositivesDelta)}% vs baseline
          </div>
        </Card>

        <Card className="p-5 border-border bg-surface shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Financial Exposure</div>
          <div className="text-3xl font-bold font-mono text-danger mb-1">₹{BENCHMARK_KPI.financialExposure}L</div>
          <div className="text-sm text-safe font-medium flex items-center gap-1">
            <ArrowDownRight className="size-4" /> {Math.abs(BENCHMARK_KPI.exposureDelta)}% vs baseline
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (Span 2): Benchmark Comparison & Scenario Breakdown */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* 3. FINSHIELD vs Alternatives (Hero Section) */}
          <div>
            <h2 className="text-xl font-bold tracking-tight mb-4">FINSHIELD vs Alternatives</h2>
            <Card className="bg-surface border-border overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-surface-raised border-b border-border">
                  <tr>
                    <th className="px-5 py-4 text-left font-medium text-muted-foreground">Metric</th>
                    <th className="px-5 py-4 text-center font-bold text-primary text-base">FINSHIELD</th>
                    <th className="px-5 py-4 text-center font-medium text-muted-foreground">Rule Engine</th>
                    <th className="px-5 py-4 text-center font-medium text-muted-foreground">LLM Judge</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono">
                  {COMPARISON_METRICS.map((row, idx) => (
                    <tr key={idx} className="hover:bg-surface-raised/50 transition-colors">
                      <td className="px-5 py-4 font-sans font-medium text-muted-foreground">{row.metric}</td>
                      <td className={`px-5 py-4 text-center font-bold ${row.best === 'finshield' ? 'text-safe bg-safe/5' : 'text-foreground bg-primary/5'}`}>
                        {row.finshield}
                      </td>
                      <td className={`px-5 py-4 text-center ${row.best === 'ruleEngine' ? 'font-bold text-safe bg-safe/5' : 'text-muted-foreground'}`}>
                        {row.ruleEngine}
                      </td>
                      <td className={`px-5 py-4 text-center ${row.best === 'llmJudge' ? 'font-bold text-safe bg-safe/5' : 'text-muted-foreground'}`}>
                        {row.llmJudge}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
            <p className="text-sm text-muted-foreground mt-3 italic">
              * FINSHIELD provides substantially stronger safety coverage at an acceptable latency cost compared to pure rule engines.
            </p>
          </div>

          {/* 5. Decision Quality vs Latency */}
          <div>
            <h2 className="text-xl font-bold tracking-tight mb-4">Decision Quality vs Latency</h2>
            <Card className="bg-surface border-border p-6 h-[300px] relative">
              <div className="absolute left-10 top-6 bottom-10 w-px bg-border/50 border-dashed border-l border-border" />
              <div className="absolute left-10 right-6 bottom-10 h-px bg-border/50 border-dashed border-b border-border" />
              
              <div className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] font-bold tracking-widest text-muted-foreground uppercase">Decision Quality</div>
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[10px] font-bold tracking-widest text-muted-foreground uppercase">Latency (ms)</div>

              <div className="absolute left-6 top-[20px] text-[10px] text-muted-foreground">100%</div>
              <div className="absolute left-8 bottom-6 text-[10px] text-muted-foreground">0ms</div>
              <div className="absolute right-4 bottom-6 text-[10px] text-muted-foreground">800ms</div>

              {/* Data Points */}
              <div className="absolute left-[30%] top-[10%] flex flex-col items-center group">
                <div className="size-4 rounded-full bg-primary shadow-[0_0_12px_rgba(var(--primary),0.8)] border-2 border-background z-10" />
                <div className="text-xs font-bold text-primary mt-2 group-hover:scale-110 transition-transform">FINSHIELD</div>
              </div>
              <div className="absolute left-[10%] top-[40%] flex flex-col items-center group opacity-80">
                <div className="size-3 rounded-full bg-muted-foreground border-2 border-background z-10" />
                <div className="text-xs font-medium text-muted-foreground mt-2">Rule Engine</div>
              </div>
              <div className="absolute left-[85%] top-[25%] flex flex-col items-center group opacity-80">
                <div className="size-3 rounded-full bg-muted-foreground border-2 border-background z-10" />
                <div className="text-xs font-medium text-muted-foreground mt-2">LLM Judge</div>
              </div>

              {/* Tradeoff Region */}
              <div className="absolute left-[20%] right-[40%] top-[5%] bottom-[50%] bg-primary/5 border border-primary/20 rounded-xl rounded-bl-none -z-10" />
              <div className="absolute top-[8%] left-[22%] text-[10px] font-bold text-primary/50 uppercase tracking-wider">Optimal Safety Region</div>
            </Card>
          </div>

          {/* 6. Benchmark by Scenario */}
          <div>
            <h2 className="text-xl font-bold tracking-tight mb-4">Benchmark by Scenario</h2>
            <Card className="bg-surface border-border overflow-hidden">
              <div className="flex bg-surface-raised border-b border-border text-sm font-medium p-1">
                <button className="px-4 py-1.5 bg-background text-foreground rounded shadow-sm">All</button>
                <button className="px-4 py-1.5 text-muted-foreground hover:text-foreground">Shopping</button>
                <button className="px-4 py-1.5 text-muted-foreground hover:text-foreground">Finance</button>
                <button className="px-4 py-1.5 text-muted-foreground hover:text-foreground">Adversarial</button>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-surface border-b border-border/50">
                  <tr>
                    <th className="px-5 py-3 text-left font-medium text-muted-foreground">Scenario</th>
                    <th className="px-5 py-3 text-right font-medium text-muted-foreground">FINSHIELD</th>
                    <th className="px-5 py-3 text-right font-medium text-muted-foreground">Rule Engine</th>
                    <th className="px-5 py-3 text-right font-medium text-muted-foreground">LLM Judge</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 font-mono">
                  {SCENARIO_BREAKDOWN.map((row, idx) => (
                    <tr key={idx} className="hover:bg-surface-raised/50 transition-colors cursor-pointer group">
                      <td className="px-5 py-3 font-sans font-medium text-foreground group-hover:text-primary transition-colors">{row.name}</td>
                      <td className="px-5 py-3 text-right font-bold text-safe">{row.finshield}%</td>
                      <td className="px-5 py-3 text-right text-muted-foreground">{row.ruleEngine}%</td>
                      <td className="px-5 py-3 text-right text-muted-foreground">{row.llmJudge}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
          
        </div>

        {/* Right Column: Error Analysis, Financial, Evolution */}
        <div className="space-y-8">
          
          {/* 4. Overall Benchmark Score */}
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Benchmark Score</h2>
            <Card className="bg-surface border-border p-5">
              <div className="flex items-baseline justify-between mb-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold font-mono text-primary">94.7</span>
                  <span className="text-sm text-muted-foreground">/ 100</span>
                </div>
                <div className="text-xs text-safe font-bold flex items-center gap-1 bg-safe/10 px-2 py-1 rounded">
                  <ArrowUpRight className="size-3" /> 6.8% vs v1.8
                </div>
              </div>
              
              <div className="w-full h-2 bg-surface-raised rounded-full mb-6 overflow-hidden flex">
                <div className="h-full bg-primary" style={{ width: '94.7%' }} />
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Safety</span>
                  <span className="font-mono font-medium text-safe">97.8</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Intent Integrity</span>
                  <span className="font-mono font-medium">96.4</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Policy Compliance</span>
                  <span className="font-mono font-medium">98.9</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Latency</span>
                  <span className="font-mono font-medium text-warn">87.2</span>
                </div>
              </div>
            </Card>
          </div>

          {/* 7. Error Analysis */}
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Error Analysis</h2>
            <div className="space-y-4">
              <Card className="bg-surface border-border p-5">
                <div className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase mb-1">False Negatives</div>
                <div className="font-bold text-danger mb-4 flex items-center justify-between">
                  {ERROR_ANALYSIS.falseNegatives.total} scenarios missed
                </div>
                <div className="space-y-3">
                  {ERROR_ANALYSIS.falseNegatives.breakdown.map((item, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-foreground/80">{item.cause}</span>
                        <span className="font-mono text-danger font-bold">{item.count}</span>
                      </div>
                      <div className="w-full h-1.5 bg-danger/10 rounded-full overflow-hidden">
                        <div className="h-full bg-danger" style={{ width: item.width }} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="bg-surface border-border p-5">
                <div className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase mb-1">False Positives</div>
                <div className="font-bold text-warn mb-4 flex items-center justify-between">
                  {ERROR_ANALYSIS.falsePositives.total} scenarios blocked incorrectly
                </div>
                <div className="space-y-3">
                  {ERROR_ANALYSIS.falsePositives.breakdown.map((item, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-foreground/80">{item.cause}</span>
                        <span className="font-mono text-warn font-bold">{item.count}</span>
                      </div>
                      <div className="w-full h-1.5 bg-warn/10 rounded-full overflow-hidden">
                        <div className="h-full bg-warn" style={{ width: item.width }} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          {/* 8. Financial Impact */}
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Financial Protection Simulation</h2>
            <Card className="bg-surface border-border p-5 overflow-hidden relative">
              <div className="absolute -right-10 -bottom-10 opacity-5 pointer-events-none">
                <ShieldAlert className="size-48" />
              </div>
              
              <div className="flex justify-between items-baseline mb-6 border-b border-border/50 pb-4">
                <div>
                  <div className="text-4xl font-bold font-mono text-safe">97.1%</div>
                  <div className="text-[10px] font-bold text-safe uppercase tracking-wider mt-1">Reduction in financial exposure</div>
                </div>
              </div>

              <div className="space-y-4 text-sm relative z-10">
                <div className="flex justify-between items-center text-muted-foreground text-xs uppercase tracking-wider font-semibold border-b border-border/30 pb-2">
                  <span></span>
                  <span className="w-20 text-right">Without</span>
                  <span className="w-20 text-right text-primary">With FS</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Unsafe transactions</span>
                  <span className="font-mono w-20 text-right text-danger">₹18.4L</span>
                  <span className="font-mono w-20 text-right text-safe font-bold">₹2.8L</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">Prevented loss</span>
                  <span className="font-mono w-20 text-right text-muted-foreground">—</span>
                  <span className="font-mono w-20 text-right text-safe font-bold">₹15.6L</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-medium">False intervention</span>
                  <span className="font-mono w-20 text-right text-warn">₹1.92L</span>
                  <span className="font-mono w-20 text-right">₹0.61L</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-border/50">
                  <span className="font-bold">Net Protection</span>
                  <span className="font-mono w-20 text-right text-muted-foreground">—</span>
                  <span className="font-mono w-20 text-right text-safe font-bold bg-safe/10 px-1 py-0.5 rounded">₹14.9L</span>
                </div>
              </div>
            </Card>
          </div>

          {/* 11. Version Evolution */}
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Version Evolution</h2>
            <Card className="bg-surface border-border overflow-hidden p-5">
              <table className="w-full text-xs text-left">
                <thead className="text-muted-foreground border-b border-border/50">
                  <tr>
                    <th className="pb-2 font-medium">Version</th>
                    <th className="pb-2 font-medium text-right">Safety</th>
                    <th className="pb-2 font-medium text-right">FPs</th>
                    <th className="pb-2 font-medium text-right">Exposure</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 font-mono">
                  {VERSION_EVOLUTION.map((ver, idx) => (
                    <tr key={idx} className={idx === VERSION_EVOLUTION.length - 1 ? "bg-primary/5 font-bold text-primary" : "text-muted-foreground"}>
                      <td className="py-2.5">{ver.version}</td>
                      <td className="py-2.5 text-right">{ver.safety}%</td>
                      <td className="py-2.5 text-right">{ver.falsePositives}%</td>
                      <td className="py-2.5 text-right">₹{ver.exposure}L</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          {/* AI Benchmark Analyst & Methodology */}
          <div className="space-y-4">
            <Card className="bg-primary/5 border border-primary/20 p-5">
              <div className="flex items-center gap-2 text-primary font-bold text-sm mb-3 uppercase tracking-wider">
                <Sparkles className="size-4" /> AI Benchmark Analyst
              </div>
              <p className="text-sm leading-relaxed text-foreground/90 mb-4">
                The largest improvement in v1.9 came from intent-transition verification. False negatives decreased from 4.7% → 1.8%.
                <br/><br/>
                However, FINSHIELD remains slower than the traditional rule engine by 142ms on average. The tradeoff is concentrated in high-risk transactions.
              </p>
              <div className="flex gap-2 flex-wrap">
                <span className="text-[10px] border border-primary/30 text-primary px-2 py-1 rounded cursor-pointer hover:bg-primary/10">Where is FINSHIELD weakest?</span>
                <span className="text-[10px] border border-primary/30 text-primary px-2 py-1 rounded cursor-pointer hover:bg-primary/10">How to reduce latency?</span>
              </div>
            </Card>

            <Button variant="outline" className="w-full justify-between border-border bg-surface hover:bg-surface-raised h-12">
              <span className="flex items-center"><Activity className="size-4 mr-2 text-muted-foreground" /> View Full Methodology</span>
              <ArrowUpRight className="size-4 text-muted-foreground" />
            </Button>
          </div>

        </div>
      </div>

      {isRunnerOpen && (
        <BenchmarkRunnerModal onClose={() => setIsRunnerOpen(false)} />
      )}

    </div>
  );
}
