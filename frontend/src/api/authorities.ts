import { api } from "@/lib/api-client";

export type AuthorityStatus = "DRAFT" | "ACTIVE" | "REVOKED" | "EXPIRED" | "ARCHIVED";

export interface AuthorityVersion {
  id: string;
  authority_id?: string;
  delegated_authority_id?: string;
  version_number?: number;
  version?: number;
  snapshot?: {
    allowed_capabilities?: string[];
    prohibited_actions?: string[];
    monetary_limit?: number | null;
    currency?: string;
    approval_threshold?: number | null;
    valid_from?: string | null;
    valid_until?: string | null;
  };
  allowed_capabilities?: string[];
  monetary_limit?: number | null;
  currency?: string;
  requires_approval_above?: number | null;
  created_at: string;
  created_by: string | null;
  change_reason?: string | null;
}

export interface DelegatedAuthority {
  id: string;
  workspace_id: string;
  agent_id: string;
  intent_id: string | null;
  allowed_capabilities: string[];
  monetary_limit: number | null;
  currency: string;
  requires_approval_above: number | null;
  valid_until: string | null;
  status: AuthorityStatus;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  revoked_at: string | null;
}

export interface AuthorityCreate {
  agent_id: string;
  intent_id?: string;
  allowed_capabilities: string[];
  monetary_limit?: number;
  currency?: string;
  requires_approval_above?: number;
  valid_until?: string;
}

export interface AuthorityUpdate {
  allowed_capabilities?: string[];
  monetary_limit?: number;
  currency?: string;
  requires_approval_above?: number;
  valid_until?: string;
  change_reason?: string;
}

export interface AuthorityEvaluationResult {
  authorized: boolean;
  reasons: string[];
  effective_monetary_limit?: number | null;
  authority_version?: number | null;
  requires_approval: boolean;
  alignment_result: "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN";
  alignment_signals: any[];
}

export const authoritiesApi = {
  list: async (skip: number = 0, limit: number = 100, agent_id?: string, status?: string) => {
    const params: any = { skip, limit };
    if (agent_id) params.agent_id = agent_id;
    if (status) params.status = status;
    const res = await api.get<DelegatedAuthority[]>("/authorities", { params });
    return res.data;
  },

  get: async (id: string) => {
    const res = await api.get<DelegatedAuthority>(`/authorities/${id}`);
    return res.data;
  },

  create: async (data: AuthorityCreate) => {
    const res = await api.post<DelegatedAuthority>("/authorities", data);
    return res.data;
  },

  update: async (id: string, data: AuthorityUpdate) => {
    const res = await api.patch<DelegatedAuthority>(`/authorities/${id}`, data);
    return res.data;
  },

  activate: async (id: string) => {
    const res = await api.post<DelegatedAuthority>(`/authorities/${id}/activate`);
    return res.data;
  },

  revoke: async (id: string, reason?: string) => {
    const res = await api.post<DelegatedAuthority>(`/authorities/${id}/revoke`, { reason });
    return res.data;
  },

  getVersions: async (id: string) => {
    const res = await api.get<AuthorityVersion[]>(`/authorities/${id}/versions`);
    return res.data;
  },

  simulate: async (id: string, payload: any) => {
    const res = await api.post<AuthorityEvaluationResult>(`/authorities/${id}/simulate`, payload);
    return res.data;
  }
};
