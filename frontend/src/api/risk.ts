import { api } from "@/lib/api-client";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskSignal {
  signal_type: string;
  score: number;
  severity: RiskLevel;
  weight: number;
  contribution: number;
  reason_code: string;
  explanation: string;
}

export interface RiskAssessment {
  id: string;
  workspace_id: string;
  agent_id?: string | null;
  agent_action_id?: string | null;
  agent_run_id?: string | null;
  intent_id?: string | null;
  intent_version?: number | null;
  authority_id?: string | null;
  authority_version?: number | null;
  assessment_type: string;
  risk_score: number;
  risk_level: RiskLevel;
  decision_hint?: string | null;
  signals: RiskSignal[];
  feature_snapshot: Record<string, any>;
  model_version: string;
  scoring_version: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RiskSummary {
  total_assessments: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
  average_score: number;
  high_risk_rate: number;
}

export interface RiskEvaluateRequest {
  agent_id: string;
  agent_action_id?: string;
  agent_run_id?: string;
  intent_id?: string;
  authority_id?: string;
  merchant_id?: string;
  product_category?: string;
  transaction?: {
    amount: number;
    currency: string;
  };
}

export const riskApi = {
  getAssessments: async (agentId?: string, level?: string): Promise<RiskAssessment[]> => {
    const params = new URLSearchParams();
    if (agentId) params.append('agent_id', agentId);
    if (level) params.append('level', level);
    const response = await api.get<RiskAssessment[]>(`/risk/assessments?${params.toString()}`);
    return response.data;
  },

  getAssessment: async (id: string): Promise<RiskAssessment> => {
    const response = await api.get<RiskAssessment>(`/risk/assessments/${id}`);
    return response.data;
  },

  getSummary: async (days: number = 7): Promise<RiskSummary> => {
    const response = await api.get<RiskSummary>(`/risk/summary?days=${days}`);
    return response.data;
  },

  evaluateRisk: async (request: RiskEvaluateRequest, persist: boolean = false): Promise<RiskAssessment> => {
    const response = await api.post<RiskAssessment>(`/risk/evaluate?persist=${persist}`, request);
    return response.data;
  }
};
