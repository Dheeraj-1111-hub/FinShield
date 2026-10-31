import { api } from "@/lib/api-client";

export type AgentType = "SHOPPING" | "PAYMENT" | "FINANCE" | "OPERATIONS" | "CUSTOM";
export type AgentStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "REVOKED" | "ARCHIVED";

export type AgentCapability = 
  | "SEARCH_PRODUCTS"
  | "COMPARE_PRODUCTS"
  | "CREATE_CART"
  | "MANAGE_CART"
  | "ADD_CART_ITEM"
  | "UPDATE_CART"
  | "CREATE_ORDER"
  | "CANCEL_ORDER"
  | "REQUEST_PAYMENT"
  | "EXECUTE_PAYMENT"
  | "REQUEST_REFUND"
  | "PAY_ORDER";

export interface Agent {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  type: AgentType;
  status: AgentStatus;
  capabilities: AgentCapability[];
  max_transaction_amount: number | null;
  monthly_limit: number | null;
  daily_limit: number | null;
  approval_threshold: number | null;
  currency: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  last_active_at: string | null;
}

export interface AgentCreate {
  name: string;
  description?: string;
  type: AgentType;
  capabilities?: AgentCapability[];
  max_transaction_amount?: number;
  monthly_limit?: number;
  daily_limit?: number;
  approval_threshold?: number;
  currency?: string;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  capabilities?: AgentCapability[];
  max_transaction_amount?: number | null;
  monthly_limit?: number | null;
  daily_limit?: number | null;
  approval_threshold?: number | null;
  currency?: string;
}

export interface AgentCredential {
  id: string;
  agent_id: string;
  name: string;
  client_id: string;
  status: string;
  created_at: string;
  last_used_at: string | null;
}

export interface AgentCredentialSecret extends AgentCredential {
  client_secret: string;
}

export interface AgentActivity {
  id: string;
  agent_id: string;
  action: string;
  actor_id: string | null;
  details: Record<string, any>;
  created_at: string;
}

export const agentsApi = {
  list: async () => {
    const res = await api.get<Agent[]>("/agents");
    return res.data;
  },
  
  get: async (id: string) => {
    const res = await api.get<Agent>(`/agents/${id}`);
    return res.data;
  },
  
  create: async (data: AgentCreate) => {
    const res = await api.post<Agent>("/agents", data);
    return res.data;
  },
  
  update: async (id: string, data: AgentUpdate) => {
    const res = await api.patch<Agent>(`/agents/${id}`, data);
    return res.data;
  },
  
  updateStatus: async (id: string, status: "ACTIVE" | "PAUSED" | "REVOKED") => {
    const { data } = await api.post(`/agents/${id}/status`, { status });
    return data;
  },
  
  listCredentials: async (id: string): Promise<AgentCredential[]> => {
    const { data } = await api.get(`/agents/${id}/credentials`);
    return data;
  },
  
  createCredential: async (id: string, name: string): Promise<AgentCredentialSecret> => {
    const { data } = await api.post(`/agents/${id}/credentials`, { name });
    return data;
  },
  
  revokeCredential: async (id: string, credentialId: string): Promise<void> => {
    await api.delete(`/agents/${id}/credentials/${credentialId}`);
  },

  listActivity: async (id: string): Promise<AgentActivity[]> => {
    const { data } = await api.get(`/agents/${id}/activity`);
    return data;
  }
};
