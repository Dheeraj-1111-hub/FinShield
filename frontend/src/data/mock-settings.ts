// ─── FINSHIELD Settings — Mock Data ──────────────────────────────────────────

export interface Session {
  id: string;
  browser: string;
  os: string;
  location: string;
  lastActive: string;
  isCurrent: boolean;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'ACTIVE' | 'INVITED' | 'SUSPENDED';
  joined: string;
  permissions: Record<string, boolean>;
}

export interface SecurityEvent {
  time: string;
  event: string;
  detail: string;
}

export interface Invoice {
  date: string;
  description: string;
  amount: string;
  status: 'PAID' | 'PENDING';
}

// ── Profile ───────────────────────────────────────────────────────────────────
export const PROFILE = {
  name: 'User Account',
  email: 'user@finshield.dev',
  plan: 'Free Tier',
  initials: 'UA',
};

// ── Workspace ─────────────────────────────────────────────────────────────────
export const WORKSPACE = {
  name: 'FINSHIELD Sandbox',
  id: 'ws_7F31A9••••••',
  environment: 'SANDBOX' as const,
  plan: 'FREE',
  created: '12 Aug 2026',
  defaultCurrency: 'INR',
  defaultRiskThreshold: 70,
  defaultReviewThreshold: 25000,
  defaultAgentEnv: 'Sandbox',
};

// ── Sessions ──────────────────────────────────────────────────────────────────
export const SESSIONS: Session[] = [];

// ── Security Events ───────────────────────────────────────────────────────────
export const SECURITY_EVENTS: SecurityEvent[] = [];

// ── Team Members ──────────────────────────────────────────────────────────────
export const TEAM_MEMBERS: TeamMember[] = [];

// ── Billing ───────────────────────────────────────────────────────────────────
export const BILLING = {
  plan: 'FREE',
  price: '₹0',
  features: ['3 agents', '10,000 protected actions / month', '7-day audit retention', 'Sandbox environment'],
  usage: {
    protectedActions: { used: 0, max: 10000 },
    apiRequests:      { used: 0, max: 50000 },
    agents:           { used: 0, max: 3 },
  },
};

export const INVOICES: Invoice[] = [];

// ── Notification defaults ─────────────────────────────────────────────────────
export const DEFAULT_NOTIFICATIONS = {
  security: {
    critical_security: true, suspicious_agent: true,
    failed_auth: true, api_key_changes: true,
  },
  risk: {
    high_risk_tx: true, payment_blocked: true,
    policy_review: true, investigation_opened: true,
  },
  platform: {
    system_incidents: true, api_degradation: true,
    maintenance: true, product_updates: false,
  },
  delivery: { email: true, in_app: true, webhook: true },
  riskThreshold: 80,
  txThreshold: 50000,
  dailyThreshold: 200000,
};
