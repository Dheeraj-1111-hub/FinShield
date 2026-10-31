import { api } from "@/lib/api-client";

export type ScenarioCategory = 
  | 'PROMPT_INJECTION'
  | 'TOOL_OUTPUT_POISONING'
  | 'AUTHORITY_ESCALATION'
  | 'INTENT_DRIFT'
  | 'POLICY_BYPASS'
  | 'GATE_BYPASS'
  | 'APPROVAL_REPLAY'
  | 'CREDENTIAL_ABUSE'
  | 'AGENT_BEHAVIOR'
  | 'PAYMENT_IDEMPOTENCY'
  | 'ORDER_INTEGRITY'
  | 'WORKSPACE_ISOLATION'
  | 'FAILURE_SAFETY'
  | 'AUDIT_INTEGRITY';

export type ScenarioSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface SecurityScenario {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string;
  category: ScenarioCategory;
  severity: ScenarioSeverity;
  target_component: string;
  configuration: Record<string, any>;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export type TestStatus = 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'PARTIAL' | 'ERROR' | 'CANCELLED';
export type StepResult = 'PASS' | 'FAIL' | 'SKIPPED' | 'ERROR' | 'PENDING';

export interface SecurityTestStep {
  id: string;
  test_run_id: string;
  sequence_number: number;
  step_type: string;
  input_data?: Record<string, any>;
  expected_behavior: string;
  observed_behavior?: string;
  result: StepResult;
  security_event_id?: string;
  audit_event_id?: string;
  started_at?: string;
  completed_at?: string;
  metadata_?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface SecurityTestRun {
  id: string;
  workspace_id: string;
  scenario_id: string;
  status: TestStatus;
  started_at?: string;
  completed_at?: string;
  initiated_by: string;
  target_agent_id?: string;
  target_run_id?: string;
  configuration: Record<string, any>;
  summary?: string;
  created_at: string;
  scenario?: SecurityScenario;
  steps?: SecurityTestStep[];
  findings?: SecurityFinding[];
}

export interface SecurityFinding {
  id: string;
  workspace_id: string;
  test_run_id: string;
  severity: string;
  title: string;
  description: string;
  category: string;
  affected_component: string;
  expected_behavior: string;
  observed_behavior: string;
  evidence?: Record<string, any>;
  status: string;
  created_at: string;
  resolved_at?: string;
}

export interface ScenarioBenchmarkEvaluation {
  scenario_id: string;
  scenario_slug: string;
  scenario_name: string;
  category: string;
  severity: string;
  target_component: string;
  description: string;
  expected_security_invariant: string;
  total_runs: number;
  verified_runs: number;
  passed_defenses: number;
  failed_defenses: number;
  inconclusive_runs: number;
  latest_run_id?: string;
  latest_status?: TestStatus;
  latest_execution_time?: string;
  observed_result?: string;
  attack_outcome: 'ATTACK_BLOCKED' | 'ATTACK_PREVENTED_BY_IMMUTABILITY' | 'TAMPER_DETECTED' | 'ATTACK_SUCCEEDED' | 'INCONCLUSIVE' | 'UNTESTED' | 'EVALUATING' | 'UNKNOWN';
  enforcement_boundary?: string;
  evidence_summary?: Record<string, any>;
}

export interface SecurityBenchmarkSummary {
  total_runs: number;
  verified_runs: number;
  passed_defenses: number;
  failed_defenses: number;
  inconclusive_runs: number;
  active_runs: number;
  defense_rate: number | null;
  defense_rate_percentage: number | null;
  scenarios_evaluated: number;
  total_scenarios: number;
  generated_at: string;
  scenario_evaluations: ScenarioBenchmarkEvaluation[];
}

export const securityLabApi = {
  getScenarios: (workspaceId: string) => 
    api.get<SecurityScenario[]>(`/workspaces/${workspaceId}/security-lab/scenarios`).then(res => res.data),
    
  getTestRuns: (workspaceId: string) => 
    api.get<SecurityTestRun[]>(`/workspaces/${workspaceId}/security-lab/runs`).then(res => res.data),

  getTestRunDetails: (workspaceId: string, runId: string) => 
    api.get<SecurityTestRun>(`/workspaces/${workspaceId}/security-lab/runs/${runId}`).then(res => res.data),

  runTest: (workspaceId: string, scenarioId: string, configuration: Record<string, any> = {}, targetAgentId?: string) => 
    api.post<SecurityTestRun>(`/workspaces/${workspaceId}/security-lab/runs`, { 
      scenario_id: scenarioId, 
      target_agent_id: targetAgentId,
      configuration 
    }).then(res => res.data),

  getFindings: (workspaceId: string) => 
    api.get<SecurityFinding[]>(`/workspaces/${workspaceId}/security-lab/findings`).then(res => res.data),

  getBenchmarkSummary: (workspaceId: string) =>
    api.get<SecurityBenchmarkSummary>(`/workspaces/${workspaceId}/security-lab/benchmark`).then(res => res.data),
};
