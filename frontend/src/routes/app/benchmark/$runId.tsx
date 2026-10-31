import { createFileRoute, Link, useParams } from '@tanstack/react-router';
import { useBenchmarkRunDetail } from '@/hooks/useBenchmark';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Play, ShieldAlert, BarChart3, Database } from 'lucide-react';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';

export const Route = createFileRoute('/app/benchmark/$runId')({
  component: BenchmarkResultDashboard,
});

function BenchmarkResultDashboard() {
  const { runId } = useParams({ from: '/app/benchmark/$runId' });
  const { data: run, isLoading } = useBenchmarkRunDetail(runId, { refetchInterval: 2000 });

  if (isLoading) {
    return <div className="p-8 text-center animate-pulse">Loading execution results...</div>;
  }

  if (!run) {
    return <div className="p-8 text-center text-red-500">Run not found.</div>;
  }

  const isRunning = run.status === 'RUNNING' || run.status === 'QUEUED';

  // Extract metrics
  const getMetric = (name: string, isBaseline: boolean) => 
    run.metrics?.find(m => m.metric_name === name && m.is_baseline === isBaseline)?.metric_value;

  const finshieldFAR = getMetric('false_allow_rate', false);
  const baselineFAR = getMetric('false_allow_rate', true);
  
  const finshieldCompletion = getMetric('task_completion_rate', false);
  const baselineCompletion = getMetric('task_completion_rate', true);
  
  const finshieldOverhead = getMetric('latency_overhead_ms', false);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/app/benchmark">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Experiment Results</h2>
          <p className="text-muted-foreground mt-1">Run ID: {run.id}</p>
        </div>
        <div className="ml-auto flex gap-3">
          <Badge variant={isRunning ? "secondary" : (run.status === 'COMPLETED' ? "default" : "destructive")} className="text-sm px-3 py-1">
            {run.status}
          </Badge>
          <Button variant="outline"><Database className="h-4 w-4 mr-2" /> Export JSON</Button>
        </div>
      </div>

      {isRunning && (
        <Card className="border-blue-200 bg-blue-50/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4 mb-2">
              <Play className="h-5 w-5 text-blue-500 animate-pulse" />
              <div className="font-medium">Execution in progress...</div>
            </div>
            <div className="w-full bg-blue-100 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${Math.max(5, (run.completed_cases / run.total_cases) * 100)}%` }}></div>
            </div>
            <div className="text-sm text-muted-foreground mt-2 text-right">
              {run.completed_cases} / {run.total_cases} cases completed
            </div>
          </CardContent>
        </Card>
      )}

      {!isRunning && run.status === 'COMPLETED' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title="False Allow Rate" 
              value={finshieldFAR !== undefined ? `${(finshieldFAR * 100).toFixed(1)}%` : 'N/A'}
              baselineValue={baselineFAR !== undefined ? `${(baselineFAR * 100).toFixed(1)}%` : undefined}
              icon={<ShieldAlert className="h-5 w-5 text-red-500" />}
              description="Unauthorized actions allowed (Lower is better)"
            />
            <MetricCard 
              title="Task Completion" 
              value={finshieldCompletion !== undefined ? `${(finshieldCompletion * 100).toFixed(1)}%` : 'N/A'}
              baselineValue={baselineCompletion !== undefined ? `${(baselineCompletion * 100).toFixed(1)}%` : undefined}
              icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
              description="Legitimate tasks succeeding (Higher is better)"
            />
            <MetricCard 
              title="Latency Overhead" 
              value={finshieldOverhead !== undefined ? `+${finshieldOverhead.toFixed(0)}ms` : 'N/A'}
              icon={<BarChart3 className="h-5 w-5 text-blue-500" />}
              description="Median delay added by FINSHIELD"
            />
            <MetricCard 
              title="Cases Evaluated" 
              value={run.completed_cases.toString()}
              icon={<Database className="h-5 w-5 text-gray-500" />}
              description="Total case iterations across the run"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Case Results Trace</CardTitle>
              <CardDescription>Detailed evidence from every evaluation.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Mode</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Expected</TableHead>
                    <TableHead>Observed</TableHead>
                    <TableHead>Financial Exec</TableHead>
                    <TableHead>Latency</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.results?.map(r => (
                    <TableRow key={r.id}>
                      <TableCell><Badge variant={r.is_baseline ? 'outline' : 'secondary'}>{r.is_baseline ? 'Baseline' : 'FINSHIELD'}</Badge></TableCell>
                      <TableCell>
                        {r.status === 'PASS' ? <Badge className="bg-green-500">PASS</Badge> : <Badge variant="destructive">FAIL</Badge>}
                      </TableCell>
                      <TableCell>{r.expected_decision}</TableCell>
                      <TableCell>
                        <span className={r.observed_decision !== r.expected_decision ? 'text-red-500 font-bold' : ''}>
                          {r.observed_decision}
                        </span>
                      </TableCell>
                      <TableCell>{r.financial_execution_occurred ? 'Yes' : 'No'}</TableCell>
                      <TableCell>{r.latency_ms} ms</TableCell>
                    </TableRow>
                  ))}
                  {(!run.results || run.results.length === 0) && (
                    <TableRow><TableCell colSpan={6} className="text-center py-4">No cases executed.</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function MetricCard({ title, value, baselineValue, icon, description }: any) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {baselineValue && <p className="text-xs text-muted-foreground mt-1">Baseline: {baselineValue}</p>}
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </CardContent>
    </Card>
  );
}
