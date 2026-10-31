export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type RiskDecision = 'BLOCKED' | 'REVIEW' | 'ALLOWED' | 'DETECTED' | 'POLICY_CHANGE' | 'INVESTIGATING';

export interface PolicyViolation {
  rule: string;
  expected: string;
  actual: string;
  passed: boolean;
}

export interface SecurityEvent {
  id: string;
  timestamp: string;
  severity: RiskSeverity;
  type: string;
  description: string;
  agentId: string;
  decision: RiskDecision;
  
  amount?: number;
  currency?: string;
  
  // Investigation Context
  originalIntent?: string;
  intentAlignment?: number;
  
  policyViolations?: PolicyViolation[];
  
  // References
  paymentId?: string;
  orderId?: string;
  sessionId?: string;
  investigationId?: string;
  policyId?: string;
}

export const MOCK_SECURITY_EVENTS: SecurityEvent[] = [
  {
    id: "SEC-99382",
    timestamp: new Date(Date.now() - 2 * 60000).toISOString(), // 2 mins ago
    severity: "CRITICAL",
    type: "Intent Divergence",
    description: "Shopping Agent attempted an unrelated financial purchase.",
    agentId: "AGT-7F31A9", // Shopping Agent
    decision: "BLOCKED",
    amount: 150000,
    currency: "₹",
    originalIntent: "Buy laptop below ₹80,000",
    intentAlignment: 4,
    policyViolations: [
      { rule: "Intent match", expected: "> 80%", actual: "4%", passed: false },
      { rule: "Category authorization", expected: "Commerce", actual: "Financial Investment", passed: false },
      { rule: "Amount policy", expected: "< ₹80,000", actual: "₹1,50,000", passed: false }
    ],
    sessionId: "SES-8A91B2",
    investigationId: "INV-00192",
    policyId: "POL-2026-08"
  },
  {
    id: "SEC-99381",
    timestamp: new Date(Date.now() - 60 * 60000).toISOString(), // 1 hr ago
    severity: "HIGH",
    type: "Policy Threshold",
    description: "Transaction exceeded automatic approval limit.",
    agentId: "AGT-7F31A9",
    decision: "REVIEW",
    amount: 52000,
    currency: "₹",
    policyViolations: [
      { rule: "Auto-approval threshold", expected: "≤ ₹50,000", actual: "₹52,000", passed: false }
    ],
    sessionId: "SES-3F92C1",
    paymentId: "PAY-59281",
    policyId: "POL-2026-07"
  },
  {
    id: "SEC-99380",
    timestamp: new Date(Date.now() - 24 * 60 * 60000).toISOString(), // 1 day ago
    severity: "INFO",
    type: "Agent Whitelist Updated",
    description: "Added 2 new permitted merchants for Finance Agent.",
    agentId: "AGT-9X42E7", // Finance Agent
    decision: "POLICY_CHANGE",
    policyId: "POL-2026-05"
  },
  {
    id: "SEC-99379",
    timestamp: new Date(Date.now() - 25 * 60 * 60000).toISOString(), // 1 day ago
    severity: "MEDIUM",
    type: "Merchant Anomaly",
    description: "Finance Agent interacted with unverified merchant endpoint.",
    agentId: "AGT-9X42E7",
    decision: "INVESTIGATING",
    investigationId: "INV-00191"
  }
];

export const RISK_METRICS = {
  overallScore: 24,
  scoreTrend: -8,
  activeThreats: 2,
  blockedActions: 7,
  blockedTrend: 2,
  valueProtected: 184200,
  protectedCategories: [
    { label: "Investment product", amount: 150000 },
    { label: "Unauthorized purchase", amount: 22000 },
    { label: "Policy violations", amount: 12200 }
  ],
  agentsProtected: 3,
  actionsEvaluated: 284
};
