import { api } from "@/lib/api-client";

export interface ApprovalRequest {
  id: string;
  workspace_id: string;
  agent_id: string;
  agent_run_id: string;
  agent_action_id: string;
  gate_decision_id: string;
  requested_by: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';
  reason: string;
  risk_score?: string;
  amount?: number;
  currency?: string;
  transaction_data?: Record<string, any>;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export interface ApprovalDecisionResponse {
  agent_run_id: string;
  decision: string;
  nonce: string;
  agent_action_id: string;
  reason_codes: string[];
  consumed_at: string | null;
  intent_id: string;
  authority_id: string;
  policy_evaluation_id: string;
  risk_assessment_id: string;
}

export interface GateDecisionDetail {
  id: string;
  workspace_id: string;
  agent_id: string;
  agent_run_id: string;
  agent_action_id: string;
  decision: 'ALLOW' | 'REVIEW' | 'BLOCK' | string;
  reason_codes: string[];
  explanation?: string | null;
  required_approval: boolean;
  approval_id?: string | null;
  supersedes_decision_id?: string | null;
  valid_until?: string | null;
  nonce?: string | null;
  consumed_at?: string | null;
  evaluation_snapshot: Record<string, any>;
  created_at: string;
  updated_at?: string | null;

  amount?: number | null;
  currency?: string | null;
  execution_status?: string | null;
  approval_lifecycle_status?: string | null;

  agent?: {
    id: string;
    name: string;
    type: string;
    status: string;
    capabilities: string[];
    created_at?: string | null;
  } | null;

  agent_run?: {
    id: string;
    status: string;
    trigger_type?: string | null;
    input?: string | null;
    output?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    started_at?: string | null;
    completed_at?: string | null;
    created_at?: string | null;
  } | null;

  agent_action?: {
    id: string;
    tool_name: string;
    sequence_number: number;
    status: string;
    input?: any;
    output?: any;
    alignment_result?: string | null;
    alignment_signals?: any;
    error_code?: string | null;
    error_message?: string | null;
    created_at?: string | null;
  } | null;

  approval?: {
    id: string;
    status: string;
    requested_by: string;
    reason?: string | null;
    risk_score?: number | null;
    amount?: number | null;
    currency?: string | null;
    transaction_data?: Record<string, any>;
    expires_at?: string | null;
    approved_by?: string | null;
    approved_at?: string | null;
    rejected_by?: string | null;
    rejected_at?: string | null;
    created_at?: string | null;
  } | null;

  intent?: {
    id: string;
    title: string;
    natural_language_request: string;
    status: string;
    intent_type: string;
    structured_constraints?: Record<string, any>;
    version: number;
    created_at?: string | null;
  } | null;

  authority?: {
    id: string;
    status: string;
    allowed_capabilities: string[];
    prohibited_actions: string[];
    monetary_limit?: number | null;
    currency: string;
    approval_threshold?: number | null;
    valid_from?: string | null;
    valid_until?: string | null;
    version: number;
  } | null;

  risk_assessment?: {
    id: string;
    risk_score: number;
    risk_level: string;
    assessment_type: string;
    decision_hint?: string | null;
    signals: string[];
    feature_snapshot: Record<string, any>;
    model_version: string;
    scoring_version: string;
    status: string;
  } | null;

  policy_evaluation?: {
    policy_evaluation_id?: string | null;
    policy_snapshot?: Record<string, any>;
    evaluation_snapshot?: Record<string, any>;
    policy_name?: string | null;
    policy_type?: string | null;
  } | null;

  order?: {
    id: string;
    status: string;
    subtotal: number;
    total: number;
    currency: string;
    merchant_id?: string | null;
    payment_id?: string | null;
    created_at?: string | null;
    items?: Array<{
      product_name: string;
      quantity: number;
      unit_price: number;
      total: number;
    }>;
  } | null;

  payment?: {
    id: string;
    status: string;
    amount: number;
    currency: string;
    order_id?: string | null;
    idempotency_key?: string | null;
    payment_intent_id?: string | null;
    failure_code?: string | null;
    failure_reason?: string | null;
    created_at?: string | null;
  } | null;

  evidence_status: Record<string, string>;
}

export interface GateDecisionListItem {
  id: string;
  workspace_id: string;
  agent_id: string;
  agent_name?: string | null;
  agent_run_id: string;
  agent_action_id: string;
  tool_name?: string | null;
  decision: string;
  reason_codes: string[];
  explanation?: string | null;
  required_approval: boolean;
  approval_id?: string | null;
  approval_status?: string | null;
  approval_lifecycle_status?: string | null;
  execution_status?: string | null;
  consumed_at?: string | null;
  supersedes_decision_id?: string | null;
  amount?: number | null;
  currency?: string | null;
  created_at: string;
}

export const approvalsApi = {
  getApprovals: async (workspaceId: string, params?: any): Promise<ApprovalRequest[]> => {
    const response = await api.get<ApprovalRequest[]>(`/approvals/${workspaceId}/approvals`, { params });
    return response.data;
  },

  getApproval: async (workspaceId: string, id: string): Promise<ApprovalRequest> => {
    const response = await api.get<ApprovalRequest>(`/approvals/${workspaceId}/approvals/${id}`);
    return response.data;
  },

  decide: async (approvalId: string, decision: 'APPROVED' | 'REJECTED', reason?: string): Promise<ApprovalDecisionResponse> => {
    const response = await api.post<ApprovalDecisionResponse>(`/approvals/${approvalId}/decision`, { decision, reason });
    return response.data;
  },

  getGateDecision: async (decisionId: string): Promise<GateDecisionDetail> => {
    const response = await api.get<GateDecisionDetail>(`/gate-decisions/${decisionId}`);
    return response.data;
  },

  listGateDecisions: async (params?: { limit?: number; agent_id?: string; run_id?: string }): Promise<GateDecisionListItem[]> => {
    const response = await api.get<GateDecisionListItem[]>('/gate-decisions', { params });
    return response.data;
  },
};

