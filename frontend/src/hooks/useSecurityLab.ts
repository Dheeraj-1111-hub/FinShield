import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { securityLabApi } from '@/api/security_lab';
import { useWorkspace } from './useWorkspace';
import { toast } from 'sonner';

export function useSecurityScenarios() {
  const { currentWorkspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['security_scenarios', currentWorkspace?.id],
    queryFn: () => securityLabApi.getScenarios(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });
}

export function useSecurityTestRuns() {
  const { currentWorkspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['security_test_runs', currentWorkspace?.id],
    queryFn: () => securityLabApi.getTestRuns(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
    refetchInterval: (query: any) => {
      const data = query?.state?.data as any[];
      const hasActive = data?.some?.(r => r.status === 'QUEUED' || r.status === 'RUNNING');
      return hasActive ? 2000 : 5000;
    }
  });
}

export function useSecurityTestRun(runId: string) {
  const { currentWorkspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['security_test_run', currentWorkspace?.id, runId],
    queryFn: () => securityLabApi.getTestRunDetails(currentWorkspace!.id, runId),
    enabled: !!currentWorkspace?.id && !!runId,
    refetchInterval: (query: any) => {
      const data = query?.state?.data;
      if (data?.status === 'QUEUED' || data?.status === 'RUNNING') return 2000;
      return false;
    }
  });
}

export function useSecurityFindings() {
  const { currentWorkspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['security_findings', currentWorkspace?.id],
    queryFn: () => securityLabApi.getFindings(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
  });
}

export function useRunSecurityTest() {
  const { currentWorkspace } = useWorkspace();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ scenarioId, targetAgentId, configuration }: { scenarioId: string, targetAgentId?: string, configuration?: Record<string, any> }) => 
      securityLabApi.runTest(currentWorkspace!.id, scenarioId, configuration, targetAgentId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['security_test_runs', currentWorkspace?.id] });
      toast.success("Security Test Initiated", {
        description: "The test run has been queued in the sandbox.",
      });
    },
    onError: (error: any) => {
      toast.error("Test Execution Failed", {
        description: error.response?.data?.error?.message || "Failed to start security test.",
      });
    }
  });
}

export function useSecurityBenchmark() {
  const { currentWorkspace } = useWorkspace();
  
  return useQuery({
    queryKey: ['security_benchmark', currentWorkspace?.id],
    queryFn: () => securityLabApi.getBenchmarkSummary(currentWorkspace!.id),
    enabled: !!currentWorkspace?.id,
    refetchInterval: (query: any) => {
      const data = query?.state?.data;
      const hasActive = data?.active_runs && data.active_runs > 0;
      return hasActive ? 2000 : 5000;
    }
  });
}
