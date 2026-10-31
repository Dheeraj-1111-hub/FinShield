export type PolicyStatus = 'ACTIVE' | 'DRAFT' | 'DISABLED' | 'CONFLICT' | 'ERROR';
export type PolicyScope = 'ALL_AGENTS' | 'AGT-7F31A9' | 'AGT-2B94C1' | 'AGT-9X42E7';
export type PolicyType = 'Financial Authority' | 'Intent & Capability' | 'Merchant Controls' | 'Transaction Limits' | 'Compliance' | 'Velocity';
export type PolicyDecisionAction = 'ALLOW' | 'REVIEW' | 'BLOCK' | 'ESCALATE';

export interface PolicyRule {
  condition: string;
  action: PolicyDecisionAction;
}

export interface PolicyAuditLog {
  timestamp: string;
  actor: string;
  change: string;
  previousValue?: string;
  newValue?: string;
}

export interface PolicyStats {
  evaluations: number;
  allowed: number;
  review: number;
  blocked: number;
}

export interface Policy {
  id: string;
  name: string;
  description: string;
  status: PolicyStatus;
  scope: PolicyScope;
  type: PolicyType;
  rules: PolicyRule[];
  stats: PolicyStats;
  lastTriggered: string;
  version: number;
  auditHistory: PolicyAuditLog[];
}

export const MOCK_POLICIES: Policy[] = [
  {
    id: "POL-2026-08",
    name: "Agent Spending Limits",
    description: "Controls autonomous transaction authority limits.",
    status: "ACTIVE",
    scope: "ALL_AGENTS",
    type: "Financial Authority",
    rules: [
      { condition: "Transaction Amount > ₹50,000", action: "REVIEW" },
      { condition: "Transaction Amount > ₹1,00,000", action: "BLOCK" }
    ],
    stats: { evaluations: 91, allowed: 84, review: 5, blocked: 2 },
    lastTriggered: new Date(Date.now() - 2 * 60 * 60000).toISOString(),
    version: 3,
    auditHistory: [
      { timestamp: new Date(Date.now() - 2 * 24 * 60 * 60000).toISOString(), actor: "System", change: "Policy activated" },
      { timestamp: new Date(Date.now() - 5 * 24 * 60 * 60000).toISOString(), actor: "User Account", change: "Maximum transaction changed", previousValue: "₹40,000", newValue: "₹50,000" }
    ]
  },
  {
    id: "POL-2026-09",
    name: "Commerce Restrictions",
    description: "Restricts shopping agent from non-commerce domains.",
    status: "ACTIVE",
    scope: "AGT-7F31A9", // Shopping Agent
    type: "Intent & Capability",
    rules: [
      { condition: "Merchant Category = Commerce", action: "ALLOW" },
      { condition: "Merchant Category = Financial Investment", action: "BLOCK" }
    ],
    stats: { evaluations: 18, allowed: 17, review: 0, blocked: 1 },
    lastTriggered: new Date(Date.now() - 60 * 60000).toISOString(),
    version: 2,
    auditHistory: [
      { timestamp: new Date(Date.now() - 10 * 24 * 60 * 60000).toISOString(), actor: "System", change: "Policy created" }
    ]
  },
  {
    id: "POL-2026-10",
    name: "Financial Product Restrictions",
    description: "Requires explicit authorization for investments.",
    status: "ACTIVE",
    scope: "ALL_AGENTS",
    type: "Compliance",
    rules: [
      { condition: "Category = Investment Products", action: "BLOCK" },
      { condition: "Agent Authorization = Explicit", action: "ALLOW" }
    ],
    stats: { evaluations: 7, allowed: 5, review: 0, blocked: 2 },
    lastTriggered: new Date(Date.now() - 2 * 60 * 60000).toISOString(),
    version: 1,
    auditHistory: [
      { timestamp: new Date(Date.now() - 30 * 24 * 60 * 60000).toISOString(), actor: "User Account", change: "Policy created" }
    ]
  },
  {
    id: "POL-2026-11",
    name: "Travel Booking Limits",
    description: "Limits autonomous travel bookings.",
    status: "ACTIVE",
    scope: "AGT-2B94C1", // Travel Agent
    type: "Transaction Limits",
    rules: [
      { condition: "Amount > ₹30,000", action: "REVIEW" },
      { condition: "Amount > ₹75,000", action: "BLOCK" }
    ],
    stats: { evaluations: 9, allowed: 9, review: 0, blocked: 0 },
    lastTriggered: new Date(Date.now() - 24 * 60 * 60000).toISOString(),
    version: 1,
    auditHistory: []
  },
  {
    id: "POL-2026-05",
    name: "Merchant Verification",
    description: "Checks merchant reputation score.",
    status: "ACTIVE",
    scope: "ALL_AGENTS",
    type: "Merchant Controls",
    rules: [
      { condition: "Merchant Verification = Unverified", action: "REVIEW" },
      { condition: "Merchant Reputation Score < 40", action: "BLOCK" }
    ],
    stats: { evaluations: 12, allowed: 10, review: 2, blocked: 0 },
    lastTriggered: new Date(Date.now() - 25 * 60 * 60000).toISOString(),
    version: 4,
    auditHistory: []
  },
  {
    id: "POL-2026-12",
    name: "Transaction Velocity",
    description: "Prevents rapid consecutive spending.",
    status: "ACTIVE",
    scope: "ALL_AGENTS",
    type: "Velocity",
    rules: [
      { condition: "Transaction Count > 5 per 10 min", action: "REVIEW" }
    ],
    stats: { evaluations: 42, allowed: 41, review: 1, blocked: 0 },
    lastTriggered: new Date(Date.now() - 18 * 60000).toISOString(),
    version: 1,
    auditHistory: []
  },
  {
    id: "POL-2026-13",
    name: "Intent Alignment",
    description: "Ensures agent action matches user intent.",
    status: "ACTIVE",
    scope: "ALL_AGENTS",
    type: "Intent & Capability",
    rules: [
      { condition: "Intent Match < 60%", action: "REVIEW" },
      { condition: "Intent Match < 30%", action: "BLOCK" }
    ],
    stats: { evaluations: 105, allowed: 102, review: 1, blocked: 2 },
    lastTriggered: new Date(Date.now() - 2 * 60000).toISOString(),
    version: 2,
    auditHistory: []
  },
  {
    id: "POL-2026-14",
    name: "Monthly Agent Authority",
    description: "Total monthly spend limit per agent.",
    status: "ACTIVE",
    scope: "AGT-7F31A9", // Shopping Agent
    type: "Financial Authority",
    rules: [
      { condition: "Monthly Total > ₹30,000", action: "BLOCK" }
    ],
    stats: { evaluations: 0, allowed: 0, review: 0, blocked: 0 },
    lastTriggered: new Date().toISOString(),
    version: 1,
    auditHistory: []
  }
];

export const POLICIES_METRICS = {
  activePolicies: 12,
  enforcementEvents: 284,
  allowedPercent: 96.8,
  blockedValue: 184200,
  agentsCovered: 3,
  agentsTotal: 3,
  health: {
    healthy: 10,
    conflicts: 1,
    unused: 1
  }
};
