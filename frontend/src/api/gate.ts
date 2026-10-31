import { api } from "@/lib/api-client";

export interface GateDecision {
  id: string;
  workspace_id: string;
  agent_id: string;
  agent_run_id: string;
  agent_action_id: string;
  intent_id?: string;
  authority_id?: string;
  decision: 'ALLOW' | 'REVIEW' | 'BLOCK';
  reason_codes: string[];
  explanation: string;
  required_approval: boolean;
  approval_id?: string;
  created_at: string;
}

export const gateApi = {
  getDecisions: async (params?: any): Promise<GateDecision[]> => {
    const response = await api.get<GateDecision[]>('/gate/decisions', { params });
    return response.data;
  },

  getDecision: async (id: string): Promise<GateDecision> => {
    const response = await api.get<GateDecision>(`/gate/decisions/${id}`);
    return response.data;
  },
};
