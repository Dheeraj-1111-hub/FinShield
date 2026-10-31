import { api } from '@/lib/api-client';

export interface AgentRunResponse {
  id: string;
  agent_id: string;
  workspace_id: string;
  status: string;
  input: string;
  output?: string;
  created_at: string;
  session_id?: string;
  gate_decision?: string;
  authoritative_decision?: string;
}

export interface AgentActionResponse {
  id: string;
  run_id: string;
  sequence_number: number;
  tool_name: string;
  input?: any;
  output?: any;
  status: string;
  alignment_result?: string;
  error_message?: string;
  error_code?: string;
  authority_id?: string;
  gate_decision?: string;
  gate_decision_id?: string;
}

export interface AgentRunDetailsResponse extends AgentRunResponse {
  actions: AgentActionResponse[];
}

export interface DecisionTraceGateDecision {
  id: string;
  agent_action_id: string;
  decision: string;
  reason_codes: string[];
  explanation?: string;
  required_approval: boolean;
  approval_id?: string;
  supersedes_decision_id?: string;
  evaluation_snapshot: Record<string, any>;
  risk_assessment_id?: string;
  intent_id?: string;
  authority_id?: string;
  created_at: string;
}

export interface DecisionTraceApproval {
  id: string;
  agent_action_id: string;
  gate_decision_id: string;
  status: string;
  reason?: string;
  amount?: number;
  currency?: string;
  transaction_data?: Record<string, any>;
  approved_by?: string;
  approved_at?: string;
  approver_name?: string;
  approver_email?: string;
  created_at: string;
}

export interface DecisionTraceOrder {
  id: string;
  status: string;
  total: number;
  currency: string;
  merchant_id?: string;
  created_at: string;
}

export interface DecisionTracePayment {
  id: string;
  order_id?: string;
  status: string;
  amount: number;
  currency: string;
  created_at: string;
}

export interface DecisionTraceAuditEvent {
  id: string;
  event_type: string;
  event_category: string;
  severity: string;
  actor_type: string;
  actor_id?: string;
  entity_type?: string;
  entity_id?: string;
  payload?: Record<string, any>;
  created_at: string;
}

export interface DecisionTraceResponse {
  run_id: string;
  run_status: string;
  input: string;
  output?: string;
  created_at: string;
  actions: AgentActionResponse[];
  gate_decisions: DecisionTraceGateDecision[];
  approvals: DecisionTraceApproval[];
  orders: DecisionTraceOrder[];
  payments: DecisionTracePayment[];
  audit_events: DecisionTraceAuditEvent[];
  final_gate_decision?: string;
}

export const agentRuntimeApi = {
  runs: {
    list: async (agentId: string): Promise<AgentRunResponse[]> => {
      const { data } = await api.get(`/agent-runtime/agents/${agentId}/runs`);
      return data;
    },
    get: async (runId: string): Promise<AgentRunDetailsResponse> => {
      const { data } = await api.get(`/agent-runtime/runs/${runId}`);
      return data;
    },
    getDecisionTrace: async (runId: string): Promise<DecisionTraceResponse> => {
      const { data } = await api.get(`/agent-runtime/runs/${runId}/decision-trace`);
      return data;
    },
    create: async (agentId: string, input: string, authorityId?: string, sessionId?: string): Promise<AgentRunResponse> => {
      const { data } = await api.post('/agent-runtime/runs', {
        agent_id: agentId,
        input: input,
        authority_id: authorityId,
        session_id: sessionId
      });
      return data;
    },
    executeAction: async (runId: string, toolName: string, toolInput: any): Promise<AgentActionResponse> => {
      const { data } = await api.post(`/agent-runtime/runs/${runId}/actions`, {
        tool_name: toolName,
        input: toolInput,
      });
      return data;
    },
    simulate: async (runId: string): Promise<void> => {
      await api.post(`/agent-runtime/runs/${runId}/simulate`);
    },
    resume: async (runId: string): Promise<AgentRunDetailsResponse> => {
      const { data } = await api.post(`/agent-runtime/runs/${runId}/resume`);
      return data;
    },
  },
};

