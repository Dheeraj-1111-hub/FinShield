import api from './config';

export interface ApiClient {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'REVOKED';
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface ApiCredential {
  id: string;
  api_client_id: string;
  workspace_id: string;
  name: string;
  credential_prefix: string;
  scopes: string[];
  status: string;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
  revoked_at?: string;
}

export interface WebhookEndpoint {
  id: string;
  workspace_id: string;
  url: string;
  description?: string;
  subscribed_events: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApiRequestLog {
  id: string;
  api_client_id?: string;
  method: string;
  route: string;
  status_code: int;
  latency_ms: int;
  occurred_at: string;
  correlation_id?: string;
}

// Clients
export const getApiClients = async (workspaceId: string): Promise<ApiClient[]> => {
  const response = await api.get(`/developers/clients?workspace_id=${workspaceId}`);
  return response.data;
};

export const createApiClient = async (workspaceId: string, data: { name: string, description?: string }): Promise<ApiClient> => {
  const response = await api.post(`/developers/clients?workspace_id=${workspaceId}`, data);
  return response.data;
};

// Credentials
export const getApiCredentials = async (workspaceId: string): Promise<ApiCredential[]> => {
  const response = await api.get(`/developers/credentials?workspace_id=${workspaceId}`);
  return response.data;
};

export const createApiCredential = async (workspaceId: string, data: { api_client_id: string, name: string, scopes: string[] }): Promise<ApiCredential & { secret: string }> => {
  const response = await api.post(`/developers/credentials?workspace_id=${workspaceId}`, data);
  return response.data;
};

export const revokeApiCredential = async (workspaceId: string, credentialId: string): Promise<void> => {
  await api.post(`/developers/credentials/${credentialId}/revoke?workspace_id=${workspaceId}`);
};

// Webhooks
export const getWebhooks = async (workspaceId: string): Promise<WebhookEndpoint[]> => {
  const response = await api.get(`/developers/webhooks?workspace_id=${workspaceId}`);
  return response.data;
};

export const createWebhook = async (workspaceId: string, data: { url: string, description?: string, subscribed_events: string[] }): Promise<WebhookEndpoint> => {
  const response = await api.post(`/developers/webhooks?workspace_id=${workspaceId}`, data);
  return response.data;
};

// Request Logs
export const getRequestLogs = async (workspaceId: string): Promise<ApiRequestLog[]> => {
  const response = await api.get(`/developers/request-logs?workspace_id=${workspaceId}`);
  return response.data;
};
