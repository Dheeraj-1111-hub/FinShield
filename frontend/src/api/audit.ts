import { api as apiClient } from "../lib/api-client";

export interface AuditEvent {
  id: string;
  workspace_id: string;
  event_type: string;
  event_category: 'AUTH' | 'WORKSPACE' | 'AGENT' | 'INTENT' | 'AUTHORITY' | 'POLICY' | 'RISK' | 'GATE' | 'APPROVAL' | 'COMMERCE' | 'PAYMENT' | 'INVESTIGATION' | 'SYSTEM' | string;
  severity: 'INFO' | 'NOTICE' | 'WARNING' | 'HIGH' | 'CRITICAL';
  actor_type: 'USER' | 'AGENT' | 'SYSTEM' | string;
  actor_id?: string;
  agent_id?: string;
  agent_run_id?: string;
  agent_action_id?: string;
  entity_type?: string;
  entity_id?: string;
  payload?: any;
  before_snapshot?: any;
  after_snapshot?: any;
  metadata?: any;
  created_at: string;
  request_id?: string;
  correlation_id?: string;
  ip_address?: string;
  user_agent?: string;
  previous_event_hash?: string;
  event_hash?: string;
  hash?: string;
  signature?: string;
  workspace_sequence: number;
}

export interface AuditEventsResponse {
  items: AuditEvent[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface BrokenLink {
  event_id: string;
  reason: string;
  expected?: any;
  actual?: any;
}

export interface AuditIntegrityResult {
  valid: boolean;
  checked_events: number;
  first_event?: string | null;
  last_event?: string | null;
  broken_links: BrokenLink[];
  is_valid: boolean;
  tampered_events: string[];
  checked_count: number;
  last_valid_hash?: string;
  chain_status?: 'VALID' | 'TAMPERED' | 'EMPTY' | string;
  completeness_status?: 'CHAIN_VALID_ONLY' | 'INCOMPLETE_INGESTION' | 'NO_EVENTS' | 'TAMPERED' | string;
  completeness_note?: string;
}


export const getAuditEvents = async (workspaceId: string, params?: any): Promise<AuditEventsResponse> => {
  const query = new URLSearchParams();
  if (params) {
    const limit = params.size || params.limit || 100;
    const page = params.page || 1;
    const skip = params.skip !== undefined ? params.skip : (page - 1) * limit;
    query.append("limit", String(limit));
    query.append("skip", String(skip));

    if (params.category) query.append("category", params.category);
    if (params.severity) query.append("severity", params.severity);
    if (params.entity_type) query.append("entity_type", params.entity_type);
    if (params.entity_id) query.append("entity_id", params.entity_id);
    if (params.actor_id) query.append("actor_id", params.actor_id);
  }
  query.append("workspace_id", workspaceId);

  const response = await apiClient.get(`/audit?${query.toString()}`, {
    headers: { "X-Workspace-ID": workspaceId },
  });

  const data = response.data;
  if (Array.isArray(data)) {
    return {
      items: data,
      total: data.length,
      page: 1,
      size: data.length,
      pages: 1
    };
  }
  return data;
};

export const getAuditEvent = async (workspaceId: string, eventId: string): Promise<AuditEvent> => {
  const response = await apiClient.get(`/audit/${eventId}`, {
    headers: { "X-Workspace-ID": workspaceId },
    params: { workspace_id: workspaceId }
  });
  return response.data;
};

export const verifyAuditIntegrity = async (workspaceId: string): Promise<AuditIntegrityResult> => {
  const response = await apiClient.post(
    `/audit/integrity/verify`,
    {},
    {
      headers: { "X-Workspace-ID": workspaceId },
      params: { workspace_id: workspaceId }
    }
  );
  const data = response.data;
  const broken = data.broken_links || [];
  return {
    valid: Boolean(data.valid),
    checked_events: Number(data.checked_events ?? 0),
    first_event: data.first_event ?? null,
    last_event: data.last_event ?? null,
    broken_links: broken,
    is_valid: Boolean(data.valid),
    tampered_events: broken.map((b: any) => b.event_id),
    checked_count: Number(data.checked_events ?? 0),
    last_valid_hash: data.last_event,
    chain_status: data.chain_status,
    completeness_status: data.completeness_status,
    completeness_note: data.completeness_note,
  };

};

export const getAuditCorrelation = async (workspaceId: string, correlationId: string): Promise<AuditEvent[]> => {
  const response = await apiClient.get(`/audit/correlations/${correlationId}`, {
    headers: { "X-Workspace-ID": workspaceId },
    params: { workspace_id: workspaceId }
  });
  return response.data;
};
