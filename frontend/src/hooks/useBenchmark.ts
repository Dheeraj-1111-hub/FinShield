import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { benchmarkApi } from '@/api/benchmark';
import { useWorkspace } from './useWorkspace';
import { toast } from 'sonner';

export function useBenchmarkSuites() {
  const { currentWorkspace } = useWorkspace();
  return useQuery({
    queryKey: ['benchmark_suites', currentWorkspace?.id],
    queryFn: () => benchmarkApi.getSuites(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });
}

export function useCreateBenchmarkSuite() {
  const { currentWorkspace } = useWorkspace();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: any) => benchmarkApi.createSuite(currentWorkspace!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark_suites', currentWorkspace?.id] });
      toast.success("Benchmark suite created");
    },
    onError: (error: any) => {
      toast.error("Failed to create suite", {
        description: error.response?.data?.error?.message,
      });
    }
  });
}

export function useBenchmarkExperiments() {
  const { currentWorkspace } = useWorkspace();
  return useQuery({
    queryKey: ['benchmark_experiments', currentWorkspace?.id],
    queryFn: () => benchmarkApi.getExperiments(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });
}

export function useCreateBenchmarkExperiment() {
  const { currentWorkspace } = useWorkspace();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: any) => benchmarkApi.createExperiment(currentWorkspace!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark_experiments', currentWorkspace?.id] });
      toast.success("Experiment created");
    },
    onError: (error: any) => {
      toast.error("Failed to create experiment", {
        description: error.response?.data?.error?.message,
      });
    }
  });
}

export function useRunBenchmarkExperiment() {
  const { currentWorkspace } = useWorkspace();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => benchmarkApi.runExperiment(currentWorkspace!.id, experimentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark_runs', currentWorkspace?.id] });
      toast.success("Benchmark execution started", {
        description: "The experiment is running in the background."
      });
    },
    onError: (error: any) => {
      toast.error("Failed to start experiment", {
        description: error.response?.data?.error?.message,
      });
    }
  });
}

export function useBenchmarkRunDetail(runId: string, options?: { refetchInterval?: number | false }) {
  const { currentWorkspace } = useWorkspace();
  return useQuery({
    queryKey: ['benchmark_run_detail', currentWorkspace?.id, runId],
    queryFn: () => benchmarkApi.getRunDetail(currentWorkspace!.id, runId),
    enabled: !!currentWorkspace?.id && !!runId,
    refetchInterval: options?.refetchInterval,
  });
}
