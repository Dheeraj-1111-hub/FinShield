// ─── FINSHIELD Developer Portal — Mock Data ───────────────────────────────────

export type KeyStatus = 'ACTIVE' | 'EXPIRING' | 'REVOKED';
export type KeyEnv = 'Sandbox' | 'Production';
export type WebhookHealth = 'HEALTHY' | 'DEGRADED' | 'FAILING';
export type AgentStatus = 'CONNECTED' | 'DISCONNECTED' | 'SUSPENDED';
export type RequestDecision = 'BLOCKED' | 'ALLOWED' | 'REVIEW' | 'EXECUTED';

export interface ApiKey {
  id: string;
  name: string;
  environment: KeyEnv;
  scope: string;
  created: string;
  lastUsed: string;
  status: KeyStatus;
  maskedKey: string;
  requests: number;
  permissions: string[];
  createdBy: string;
  lastIp: string;
  expires: string;
}

export interface WebhookEndpoint {
  id: string;
  url: string;
  events: string[];
  health: WebhookHealth;
  deliveries: number;
  failures: number;
  retryQueue: number;
  lastDelivery: string;
  lastStatus: string;
  deliverySuccessRate: number;
}

export interface ConnectedAgent {
  id: string;
  agentId: string;
  name: string;
  status: AgentStatus;
  capabilities: string[];
  lastRequest: string;
  apiVersion: string;
  requests: number;
  policyId: string;
}

export interface RecentRequest {
  id: string;
  time: string;
  method: 'POST' | 'GET' | 'PUT' | 'DELETE';
  path: string;
  agent: string;
  statusCode: number;
  decision: RequestDecision;
  latencyMs: number;
  traceId: string;
}

export interface ActivityBar {
  hour: string;
  requests: number;
  heightPct: number;
}

// ── KPI Stats ────────────────────────────────────────────────────────────────
export const DEV_STATS = {
  activeKeys: 0,
  expiringKeys: 0,
  webhooks: 0,
  healthyWebhooks: 0,
  apiUptime: 100,
  avgLatencyMs: 0,
  requests24h: 0,
  requests24hDelta: 0,
  p50Ms: 0,
  p95Ms: 0,
  errors24h: 0,
  successRate: 100,
};

// ── API Keys ─────────────────────────────────────────────────────────────────
export const API_KEYS: ApiKey[] = [];

// ── Webhooks ─────────────────────────────────────────────────────────────────
export const WEBHOOKS: WebhookEndpoint[] = [];

// ── Connected Agents ──────────────────────────────────────────────────────────
export const CONNECTED_AGENTS: ConnectedAgent[] = [];

// ── Activity Bars (24h sparkline) ─────────────────────────────────────────────
export const ACTIVITY_BARS: ActivityBar[] = [
  { hour: '00', requests: 0, heightPct: 0 },
  { hour: '01', requests: 0, heightPct: 0 },
  { hour: '02', requests: 0, heightPct: 0 },
  { hour: '03', requests: 0, heightPct: 0 },
  { hour: '04', requests: 0, heightPct: 0 },
  { hour: '05', requests: 0, heightPct: 0 },
  { hour: '06', requests: 0, heightPct: 0 },
  { hour: '07', requests: 0, heightPct: 0 },
  { hour: '08', requests: 0, heightPct: 0 },
  { hour: '09', requests: 0, heightPct: 0 },
  { hour: '10', requests: 0, heightPct: 0 },
  { hour: '11', requests: 0, heightPct: 0 },
  { hour: '12', requests: 0, heightPct: 0 },
  { hour: '13', requests: 0, heightPct: 0 },
  { hour: '14', requests: 0, heightPct: 0 },
  { hour: '15', requests: 0, heightPct: 0 },
  { hour: '16', requests: 0, heightPct: 0 },
  { hour: '17', requests: 0, heightPct: 0 },
  { hour: '18', requests: 0, heightPct: 0 },
  { hour: '19', requests: 0, heightPct: 0 },
  { hour: '20', requests: 0, heightPct: 0 },
  { hour: '21', requests: 0, heightPct: 0 },
  { hour: '22', requests: 0, heightPct: 0 },
  { hour: '23', requests: 0, heightPct: 0 },
];

// ── Recent Requests ───────────────────────────────────────────────────────────
export const RECENT_REQUESTS: RecentRequest[] = [];
