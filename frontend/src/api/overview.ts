import { api } from "@/lib/api-client";

export interface OverviewTimeRange {
  timeRange: "24h" | "7d" | "30d" | "90d";
}

export interface AgentSummary {
  total: number;
  active: number;
  paused: number;
  revoked: number;
}

export interface FinancialSummary {
  payment_volume: number;
  payment_count: number;
  orders_count: number;
  currency?: string;
  balances_by_currency?: Record<string, number>;
}

export interface GateSummary {
  allow: number;
  review: number;
  block: number;
  allow_rate: number;
  review_rate: number;
  block_rate: number;
}

export interface RiskSummary {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface InvestigationSummary {
  open: number;
  critical: number;
  escalated: number;
}

export interface SecuritySummary {
  security_events: number;
  open_findings: number;
  audit_integrity_verified: boolean;
  audit_last_verified_at: string;
}

export interface OverviewHealth {
  api: string;
  database: string;
  redis: string;
}

export interface OnboardingState {
  workspace_configured: boolean;
  agent_configured: boolean;
  intent_configured: boolean;
  authority_configured: boolean;
  policy_configured: boolean;
  first_protected_action: boolean;
  first_benchmark: boolean;
}

export interface RecentCriticalRisk {
  id: string;
  agent_id: string;
  agent_name: string;
  action_type: string;
  risk_level: string;
  score: number;
  reason: string;
  occurred_at: string;
}

export interface RecentApprovalRequest {
  id: string;
  agent_id: string;
  agent_name: string;
  action_type: string;
  merchant?: string;
  amount?: number;
  reason: string;
  requested_at: string;
}

export interface RecentAuditEvent {
  id: string;
  event_type: string;
  actor_id: string;
  actor_type: string;
  target_id: string;
  target_type: string;
  occurred_at: string;
  details?: Record<string, any>;
}

export interface OverviewResponse {
  time_range: string;
  agents: AgentSummary;
  financial: FinancialSummary;
  gate: GateSummary;
  risk: RiskSummary;
  investigations: InvestigationSummary;
  security: SecuritySummary;
  health: OverviewHealth;
  onboarding: OnboardingState;
  recent_critical_risks: RecentCriticalRisk[];
  recent_approvals: RecentApprovalRequest[];
  recent_audit_events: RecentAuditEvent[];
}

export const getOverview = async (workspaceId: string, timeRange: string = "30d"): Promise<OverviewResponse> => {
  const response = await api.get(`/overview?time_range=${timeRange}`, {
    headers: {
      "X-Workspace-ID": workspaceId,
    },
  });
  return response.data;
};
