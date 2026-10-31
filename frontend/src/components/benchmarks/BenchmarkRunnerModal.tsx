import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ChevronDown, Play, CheckCircle2, ShieldAlert, XCircle, AlertTriangle } from "lucide-react";

interface BenchmarkRunnerModalProps {
  onClose: () => void;
}

export function BenchmarkRunnerModal({ onClose }: BenchmarkRunnerModalProps) {
  const [stage, setStage] = useState<'config' | 'running' | 'complete'>('config');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (stage === 'running') {
      const interval = setInterval(() => {
        setProgress(p => {
          if (p >= 100) {
            clearInterval(interval);
            setTimeout(() => setStage('complete'), 500);
            return 100;
          }
          // Simulate variable speed
          return Math.min(100, p + (Math.random() * 4 + 1));
        });
      }, 200);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [stage]);

  const currentScenarios = Math.floor((progress / 100) * 10000);

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl bg-background border-border p-0 overflow-hidden shadow-[0_0_50px_rgba(var(--primary),0.1)]">
        
        {stage === 'config' && (
          <div className="p-6">
            <DialogHeader className="mb-6">
              <DialogTitle className="text-xl font-bold flex items-center gap-2">
                <Play className="size-5 text-primary" /> Run Benchmark
              </DialogTitle>
            </DialogHeader>
            
            <div className="grid grid-cols-2 gap-8 mb-8">
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Benchmark Suite</h3>
                  <div className="space-y-3">
                    <div className="flex items-start gap-2">
                      <Checkbox id="full-suite" checked disabled className="data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground border-primary" />
                      <Label htmlFor="full-suite" className="font-bold opacity-100">Full Safety Suite</Label>
                    </div>
                    <div className="pl-6 space-y-2">
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-border" /> Intent Integrity
                      </div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-border" /> Financial Safety
                      </div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-border" /> Tool Authorization
                      </div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-border" /> Prompt Injection
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Environment</h3>
                  <div className="flex items-center gap-2">
                    <div className="size-2 rounded-full bg-safe shadow-[0_0_8px_rgba(var(--safe),0.8)]" />
                    <span className="text-sm font-medium">Sandbox Simulation</span>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Dataset</h3>
                  <Button variant="outline" className="w-full justify-between bg-surface border-border">
                    FS-BENCH-v3 <ChevronDown className="size-4 text-muted-foreground" />
                  </Button>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Scenarios</h3>
                  <Button variant="outline" className="w-full justify-between bg-surface border-border">
                    10,000 <ChevronDown className="size-4 text-muted-foreground" />
                  </Button>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Compare Against</h3>
                  <div className="space-y-3 bg-surface border border-border p-3 rounded-md">
                    <div className="flex items-center gap-2">
                      <Checkbox id="c-fin" checked disabled className="data-[state=checked]:bg-primary" />
                      <Label htmlFor="c-fin" className="text-sm">FINSHIELD</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Checkbox id="c-rules" checked disabled className="data-[state=checked]:bg-muted-foreground" />
                      <Label htmlFor="c-rules" className="text-sm">Traditional Rules</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Checkbox id="c-llm" checked disabled className="data-[state=checked]:bg-muted-foreground" />
                      <Label htmlFor="c-llm" className="text-sm">LLM Judge</Label>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-border">
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button onClick={() => setStage('running')} className="bg-primary hover:bg-primary/90">
                Start Benchmark
              </Button>
            </div>
          </div>
        )}

        {stage === 'running' && (
          <div className="p-8">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-lg font-bold tracking-tight mb-1 flex items-center gap-2">
                  <div className="size-2 rounded-full bg-warn animate-pulse shadow-[0_0_8px_rgba(var(--warn),0.8)]" />
                  BENCHMARK RUNNING
                </h2>
                <div className="text-sm font-mono text-muted-foreground">BENCH-2026-0902-001</div>
              </div>
              <div className="text-4xl font-bold font-mono text-primary">{Math.floor(progress)}%</div>
            </div>

            <div className="w-full h-2 bg-surface rounded-full mb-8 overflow-hidden">
              <div className="h-full bg-primary transition-all duration-200" style={{ width: `${progress}%` }} />
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div>
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Current Scenario</div>
                <div className="font-medium mb-1">Financial Manipulation #{currentScenarios}</div>
                <div className="text-sm text-muted-foreground mb-4">{currentScenarios.toLocaleString()} / 10,000 scenarios</div>

                <div className="space-y-2 text-sm font-mono border border-border bg-surface p-3 rounded-md">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">FINSHIELD</span>
                    <span className="text-safe flex items-center gap-1"><CheckCircle2 className="size-3" /> BLOCKED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Rule Engine</span>
                    <span className="text-danger flex items-center gap-1"><XCircle className="size-3" /> MISSED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">LLM Judge</span>
                    <span className="text-safe flex items-center gap-1"><CheckCircle2 className="size-3" /> BLOCKED</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Live Metrics</div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Safety</div>
                    <div className="font-mono text-lg font-bold">{(94 + (progress/100)*3.8).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">FP Rate</div>
                    <div className="font-mono text-lg font-bold">{(5 - (progress/100)*2.9).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">FN Rate</div>
                    <div className="font-mono text-lg font-bold">{(4 - (progress/100)*2.2).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Latency</div>
                    <div className="font-mono text-lg font-bold">184ms</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {stage === 'complete' && (
          <div className="p-8 text-center space-y-6">
            <div className="mx-auto size-16 rounded-full bg-safe/10 flex items-center justify-center mb-4">
              <CheckCircle2 className="size-8 text-safe" />
            </div>
            
            <div>
              <h2 className="text-2xl font-bold tracking-tight mb-2">BENCHMARK COMPLETE</h2>
              <p className="text-primary font-medium tracking-wide">FINSHIELD OUTPERFORMED 2 / 3 BASELINES</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 border border-border bg-surface rounded-lg text-left">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Safety</div>
                <div className="font-mono text-xl font-bold">97.8%</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">False Negatives</div>
                <div className="font-mono text-xl font-bold text-safe">1.8%</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Exposure</div>
                <div className="font-mono text-xl font-bold text-safe">₹2.84L</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Median Latency</div>
                <div className="font-mono text-xl font-bold">184ms</div>
              </div>
            </div>

            <div className="flex justify-center gap-3 pt-4">
              <Button onClick={onClose} className="bg-primary hover:bg-primary/90">
                View Full Results
              </Button>
            </div>
          </div>
        )}

      </DialogContent>
    </Dialog>
  );
}
