import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useBenchmarkSuites, useCreateBenchmarkExperiment, useRunBenchmarkExperiment } from '@/hooks/useBenchmark';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { ArrowLeft, Play, Beaker } from 'lucide-react';

export const Route = createFileRoute('/app/benchmark/builder')({
  component: BenchmarkBuilderComponent,
});

function BenchmarkBuilderComponent() {
  const navigate = useNavigate();
  const { data: suites } = useBenchmarkSuites();
  const createExperiment = useCreateBenchmarkExperiment();
  const runExperiment = useRunBenchmarkExperiment();

  const [name, setName] = useState('');
  const [suiteId, setSuiteId] = useState<string>('');
  const [repetitions, setRepetitions] = useState<number>(1);
  const [includeBaseline, setIncludeBaseline] = useState(true);

  const handleRun = async () => {
    if (!suiteId || !name) return;
    
    const suite = suites?.find(s => s.id === suiteId);
    if (!suite) return;

    try {
      // 1. Create the experiment configuration
      const experiment = await createExperiment.mutateAsync({
        name,
        suite_id: suite.id,
        suite_version: suite.version,
        repetitions,
        baseline_configuration: includeBaseline ? { engine: 'sandbox_direct' } : null,
        protected_configuration: { engine: 'finshield_protected' }
      });

      // 2. Queue the run
      const run = await runExperiment.mutateAsync(experiment.id);
      
      // 3. Navigate to results
      navigate({ to: `/app/benchmark/${run.id}` });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/app/benchmark">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Experiment Builder</h2>
          <p className="text-muted-foreground mt-1">Configure and launch a new comparative benchmark test.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Experiment Configuration</CardTitle>
          <CardDescription>Select the evaluation suite and parameters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>Experiment Name</Label>
            <Input 
              placeholder="e.g. Safety Evaluation v1.0" 
              value={name} 
              onChange={e => setName(e.target.value)} 
            />
          </div>

          <div className="space-y-2">
            <Label>Benchmark Suite</Label>
            <Select value={suiteId} onValueChange={setSuiteId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a suite..." />
              </SelectTrigger>
              <SelectContent>
                {suites?.map(suite => (
                  <SelectItem key={suite.id} value={suite.id}>{suite.name} (v{suite.version})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Repetitions per Case</Label>
            <Input 
              type="number" 
              min={1} 
              max={100} 
              value={repetitions} 
              onChange={e => setRepetitions(parseInt(e.target.value) || 1)} 
            />
            <p className="text-xs text-muted-foreground">Increases statistical significance but takes longer.</p>
          </div>

          <div className="flex items-center justify-between border p-4 rounded-lg">
            <div className="space-y-0.5">
              <Label>Include Baseline Execution</Label>
              <p className="text-sm text-muted-foreground">
                Run cases without FINSHIELD to measure overhead and false block rate.
              </p>
            </div>
            <Switch checked={includeBaseline} onCheckedChange={setIncludeBaseline} />
          </div>
        </CardContent>
        <CardFooter className="flex justify-between border-t p-6">
          <div className="text-sm text-muted-foreground flex items-center">
            <Beaker className="h-4 w-4 mr-2" />
            Execution runs asynchronously in the Sandbox.
          </div>
          <Button 
            onClick={handleRun} 
            disabled={!name || !suiteId || createExperiment.isPending || runExperiment.isPending}
          >
            {runExperiment.isPending ? "Starting..." : <><Play className="mr-2 h-4 w-4" /> Run Experiment</>}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
