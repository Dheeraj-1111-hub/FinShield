import { api } from '@/lib/api-client';

export interface BenchmarkSuite {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  version: string;
  status: string;
  created_at: string;
}

export interface BenchmarkCase {
  id: string;
  suite_id: string;
  name: string;
  description?: string;
  category: string;
  difficulty?: string;
  expected_decision: string;
}

export interface BenchmarkExperiment {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  suite_id: string;
  suite_version: string;
  baseline_configuration?: any;
  protected_configuration?: any;
  repetitions: int;
  status: string;
  created_at: string;
}

export interface BenchmarkRun {
  id: string;
  experiment_id: string;
  workspace_id: string;
  status: string;
  total_cases: number;
  completed_cases: number;
  failed_cases: number;
  summary?: string;
  started_at?: string;
  completed_at?: string;
}

export interface BenchmarkMetric {
  metric_name: string;
  metric_value: number;
  is_baseline: boolean;
}

export interface BenchmarkCaseResult {
  id: string;
  is_baseline: boolean;
  repetition_index: number;
  status: string;
  expected_decision: string;
  observed_decision: string;
  financial_execution_occurred: boolean;
  latency_ms: number;
  error?: string;
}

export interface BenchmarkRunDetail extends BenchmarkRun {
  results: BenchmarkCaseResult[];
  metrics: BenchmarkMetric[];
}

export const benchmarkApi = {
  getSuites: async (workspaceId: string): Promise<BenchmarkSuite[]> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/benchmark/suites`);
    return data;
  },
  
  createSuite: async (workspaceId: string, payload: any): Promise<BenchmarkSuite> => {
    const { data } = await api.post(`/workspaces/${workspaceId}/benchmark/suites`, payload);
    return data;
  },

  getCases: async (workspaceId: string, suiteId: string): Promise<BenchmarkCase[]> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/benchmark/suites/${suiteId}/cases`);
    return data;
  },
  
  createCase: async (workspaceId: string, payload: any): Promise<BenchmarkCase> => {
    const { data } = await api.post(`/workspaces/${workspaceId}/benchmark/cases`, payload);
    return data;
  },

  getExperiments: async (workspaceId: string): Promise<BenchmarkExperiment[]> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/benchmark/experiments`);
    return data;
  },

  createExperiment: async (workspaceId: string, payload: any): Promise<BenchmarkExperiment> => {
    const { data } = await api.post(`/workspaces/${workspaceId}/benchmark/experiments`, payload);
    return data;
  },

  getRuns: async (workspaceId: string, experimentId: string): Promise<BenchmarkRun[]> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/benchmark/experiments/${experimentId}/runs`);
    return data;
  },

  runExperiment: async (workspaceId: string, experimentId: string): Promise<BenchmarkRun> => {
    const { data } = await api.post(`/workspaces/${workspaceId}/benchmark/experiments/${experimentId}/runs`);
    return data;
  },
  
  getRunDetail: async (workspaceId: string, runId: string): Promise<BenchmarkRunDetail> => {
    const { data } = await api.get(`/workspaces/${workspaceId}/benchmark/runs/${runId}`);
    return data;
  }
};
