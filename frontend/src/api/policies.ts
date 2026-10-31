import { api } from "@/lib/api-client";

export type PolicyStatus = "DRAFT" | "ACTIVE" | "DISABLED" | "ARCHIVED";
export type PolicyType = "TRANSACTION_LIMIT" | "AGENT_AUTHORITY" | "CAPABILITY" | "MERCHANT" | "APPROVAL" | "CURRENCY" | "VELOCITY" | "CUSTOM";
export type DecisionType = "ALLOW" | "REVIEW" | "BLOCK";

export interface Policy {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  status: PolicyStatus;
  priority: number;
  policy_type: PolicyType;
  conditions: Record<string, any>;
  actions: Record<string, any>;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyCreate {
  name: string;
  description?: string;
  status?: PolicyStatus;
  priority?: number;
  policy_type: PolicyType;
  conditions?: Record<string, any>;
  actions?: Record<string, any>;
}

export interface PolicyUpdate {
  name?: string;
  description?: string;
  status?: PolicyStatus;
  priority?: number;
  policy_type?: PolicyType;
  conditions?: Record<string, any>;
  actions?: Record<string, any>;
}

export interface PolicyEvaluationRequest {
  agent_id: string;
  amount: number;
  currency: string;
  merchant_id?: string;
  capabilities?: string[];
}

export interface MatchedPolicyInfo {
  policy_id: string;
  name: string;
}

export interface PolicyEvaluationResponse {
  decision: DecisionType;
  matched_policies: MatchedPolicyInfo[];
  reasons: string[];
}

export const policiesApi = {
  list: async (): Promise<Policy[]> => {
    const { data } = await api.get<Policy[]>("/policies");
    return data;
  },

  get: async (id: string): Promise<Policy> => {
    const { data } = await api.get<Policy>(`/policies/${id}`);
    return data;
  },

  create: async (policy: PolicyCreate): Promise<Policy> => {
    const { data } = await api.post<Policy>("/policies", policy);
    return data;
  },

  update: async (id: string, updates: PolicyUpdate): Promise<Policy> => {
    const { data } = await api.patch<Policy>(`/policies/${id}`, updates);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/policies/${id}`);
  },

  evaluate: async (req: PolicyEvaluationRequest): Promise<PolicyEvaluationResponse> => {
    const { data } = await api.post<PolicyEvaluationResponse>("/policies/evaluate", req);
    return data;
  }
};
