import { createFileRoute, Link } from '@tanstack/react-router';
import { useBenchmarkSuites, useBenchmarkExperiments } from '@/hooks/useBenchmark';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LayoutDashboard, Beaker, Play, Plus } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export const Route = createFileRoute('/app/benchmark/')({
  component: BenchmarkDashboardComponent,
});

function BenchmarkDashboardComponent() {
  const { data: suites, isLoading: loadingSuites } = useBenchmarkSuites();
  const { data: experiments, isLoading: loadingExperiments } = useBenchmarkExperiments();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Benchmark Lab</h2>
          <p className="text-muted-foreground mt-2">
            Measure safety, utility, robustness and performance of FINSHIELD through reproducible experiments.
          </p>
        </div>
        <Link to="/app/benchmark/builder">
          <Button>
            <Plus className="mr-2 h-4 w-4" /> New Experiment
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Beaker className="h-5 w-5 text-primary" />
              Benchmark Suites
            </CardTitle>
            <CardDescription>Available standardized evaluation suites</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingSuites ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : suites && suites.length > 0 ? (
              <div className="space-y-4">
                {suites.map((suite) => (
                  <div key={suite.id} className="flex justify-between items-center p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div>
                      <h4 className="font-semibold">{suite.name} <Badge variant="outline" className="ml-2">v{suite.version}</Badge></h4>
                      <p className="text-sm text-muted-foreground mt-1">{suite.description}</p>
                    </div>
                    <Badge variant={suite.status === 'ACTIVE' ? 'default' : 'secondary'}>{suite.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm text-center py-4">No benchmark suites yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5 text-primary" />
              Experiments & Runs
            </CardTitle>
            <CardDescription>Recent comparative tests</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingExperiments ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : experiments && experiments.length > 0 ? (
              <div className="space-y-4">
                {experiments.map((exp) => (
                  <div key={exp.id} className="flex justify-between items-center p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div>
                      <h4 className="font-semibold">{exp.name}</h4>
                      <p className="text-sm text-muted-foreground mt-1">Repetitions: {exp.repetitions} • Suite v{exp.suite_version}</p>
                    </div>
                    <Badge>{exp.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm text-center py-4">No experiments yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
