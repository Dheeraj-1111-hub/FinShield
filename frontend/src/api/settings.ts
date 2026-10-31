import { api } from "@/lib/api-client";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  status: string;
}

export interface UserPreferences {
  language: string;
  timezone: string;
  date_format: string;
  notification_preferences: Record<string, boolean>;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  environment: string;
  currency: string;
  timezone: string;
}

export interface WorkspaceSettings {
  risk_threshold: number;
  review_threshold: number;
  high_value_transaction_threshold: number;
  human_review_for_critical_actions: boolean;
  audit_retention_days: number;
  investigation_retention_days: number;
  session_timeout_hours: number;
  version: number;
}

export const usersApi = {
  getProfile: async () => {
    const res = await api.get<{ user: UserProfile }>("/users/me");
    return res.data.user;
  },
  updateProfile: async (data: Partial<UserProfile>) => {
    const res = await api.patch<{ user: UserProfile }>("/users/me", data);
    return res.data.user;
  },
  getPreferences: async () => {
    const res = await api.get<{ preferences: UserPreferences }>("/users/me/preferences");
    return res.data.preferences;
  },
  updatePreferences: async (data: Partial<UserPreferences>) => {
    const res = await api.patch<{ preferences: UserPreferences }>("/users/me/preferences", data);
    return res.data.preferences;
  }
};

export const workspacesApi = {
  getCurrent: async () => {
    const res = await api.get<{ workspace: Workspace }>("/workspaces/current");
    return res.data.workspace;
  },
  updateCurrent: async (data: Partial<Workspace>) => {
    const res = await api.patch<{ workspace: Workspace }>("/workspaces/current", data);
    return res.data.workspace;
  },
  getSettings: async () => {
    const res = await api.get<{ settings: WorkspaceSettings }>("/workspaces/current/settings");
    return res.data.settings;
  },
  updateSettings: async (data: Partial<WorkspaceSettings>) => {
    const res = await api.patch<{ settings: WorkspaceSettings }>("/workspaces/current/settings", data);
    return res.data.settings;
  }
};
