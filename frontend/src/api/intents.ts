import { api } from "@/lib/api-client";

export type IntentType = "PURCHASE" | "SEARCH" | "COMPARE" | "BOOKING" | "TRANSFER" | "PAYMENT" | "OTHER";
export type IntentStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "REVOKED" | "COMPLETED" | "ARCHIVED";

export interface IntentVersion {
  id: string;
  intent_id: string;
  version: number;
  title: string;
  natural_language_request: string | null;
  structured_constraints: Record<string, any>;
  intent_type: IntentType;
  created_at: string;
  created_by: string | null;
  change_reason: string | null;
}

export interface Intent {
  id: string;
  workspace_id: string;
  title: string;
  natural_language_request: string | null;
  structured_constraints: Record<string, any>;
  intent_type: IntentType;
  status: IntentStatus;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntentCreate {
  title: string;
  natural_language_request?: string;
  structured_constraints?: Record<string, any>;
  intent_type?: IntentType;
}

export interface IntentUpdate {
  title?: string;
  natural_language_request?: string;
  structured_constraints?: Record<string, any>;
  intent_type?: IntentType;
  change_reason?: string;
}

export interface IntentExtractionResult {
  proposed_title: string;
  proposed_type: IntentType;
  signals: any[];
  proposed_constraints: Record<string, any>;
  explanation: string;
}

export interface AlignmentResult {
  alignment: "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN";
  signals: any[];
}

export const intentsApi = {
  list: async (skip: number = 0, limit: number = 100) => {
    const res = await api.get<Intent[]>("/intents", { params: { skip, limit } });
    return res.data;
  },

  get: async (id: string) => {
    const res = await api.get<Intent>(`/intents/${id}`);
    return res.data;
  },

  create: async (data: IntentCreate) => {
    const res = await api.post<Intent>("/intents", data);
    return res.data;
  },

  update: async (id: string, data: IntentUpdate) => {
    const res = await api.patch<Intent>(`/intents/${id}`, data);
    return res.data;
  },

  confirm: async (id: string) => {
    const res = await api.post<Intent>(`/intents/${id}/confirm`);
    return res.data;
  },

  pause: async (id: string) => {
    const res = await api.post<Intent>(`/intents/${id}/pause`);
    return res.data;
  },

  revoke: async (id: string) => {
    const res = await api.post<Intent>(`/intents/${id}/revoke`);
    return res.data;
  },

  getVersions: async (id: string) => {
    const res = await api.get<IntentVersion[]>(`/intents/${id}/versions`);
    return res.data;
  },

  extract: async (natural_language_request: string) => {
    const res = await api.post<IntentExtractionResult>("/intents/extract", { text: natural_language_request });
    return res.data;
  },

  evaluateAlignment: async (id: string, payload: any) => {
    const res = await api.post<AlignmentResult>(`/intents/${id}/evaluate`, payload);
    return res.data;
  }
};
