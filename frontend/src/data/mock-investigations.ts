export type InvestigationStatus = 'OPEN' | 'INVESTIGATING' | 'CONTAINED' | 'ESCALATED' | 'RESOLVED';
export type InvestigationSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface TrajectoryEvent {
  time: string;
  source: 'USER INTENT' | 'SHOPPING AGENT' | 'FINANCE AGENT' | 'TRAVEL AGENT' | 'AGENT DECISION' | 'PAYMENT REQUEST' | 'FINSHIELD EVALUATION' | 'POLICY ENGINE' | 'FINAL DECISION';
  description: string;
  details?: string[];
  isTerminal?: boolean;
  status?: 'BLOCKED' | 'REVIEW' | 'ALLOW' | 'INFO';
}

export interface Investigation {
  id: string;
  title: string;
  severity: InvestigationSeverity;
  status: InvestigationStatus;
  agentId: string;
  agentName: string;
  description: string;
  value: number;
  detectedAt: string;
  riskScore: number;
  confidence: number;
  intentAlignment: number;
  originalIntent: string;
  executedIntent: string;
  divergenceSignals: {
    type: string;
    userRequested?: string;
    agentRequested?: string;
    reason?: string;
  }[];
  alignmentSignals?: {
    type: string;
    status: string;
    reason: string;
  }[];
  proposedAction?: string;
  decisionReason?: string;
  outcome?: string;
  trajectory: TrajectoryEvent[];
  policiesTriggered: {
    name: string;
    decision: 'BLOCK' | 'REVIEW' | 'ALLOW';
  }[];
  evidence: {
    id: string;
    type: string;
    description: string;
  }[];
  paymentId?: string;
  orderId?: string;
}

export const MOCK_INVESTIGATIONS: Investigation[] = [
  {
    id: "SEC-99382",
    title: "Intent Divergence",
    severity: "CRITICAL",
    status: "OPEN",
    agentId: "AGT-7F31A9",
    agentName: "Shopping Agent",
    description: "Shopping Agent attempted an unrelated financial purchase.",
    value: 150000,
    detectedAt: new Date(Date.now() - 2 * 60000).toISOString(),
    riskScore: 94,
    confidence: 97,
    intentAlignment: 18,
    originalIntent: "Buy a laptop under ₹80K",
    executedIntent: "Purchase an investment-linked financial product",
    divergenceSignals: [
      { type: "Product category mismatch", userRequested: "Consumer electronics", agentRequested: "Financial product" },
      { type: "Value mismatch", userRequested: "Requested ceiling: ₹80,000", agentRequested: "Agent requested: ₹1,50,000" },
      { type: "Capability mismatch", userRequested: "Shopping Agent: Commerce", agentRequested: "Requested capability: Financial transaction" }
    ],
    trajectory: [
      { time: "09:58:02", source: "USER INTENT", description: '"Find a laptop under ₹80K"', status: "INFO" },
      { time: "09:58:04", source: "SHOPPING AGENT", description: "Searched Dell / Lenovo", status: "INFO" },
      { time: "09:58:17", source: "AGENT DECISION", description: "Selected financial product", status: "INFO" },
      { time: "09:58:18", source: "PAYMENT REQUEST", description: "₹1,50,000", status: "INFO" },
      { time: "09:58:18", source: "FINSHIELD EVALUATION", description: "Intent alignment: 18%", details: ["Amount: ₹1,50,000", "Category: Financial Product"], status: "INFO" },
      { time: "09:58:18", source: "POLICY ENGINE", description: "Financial Product Restriction → BLOCK", details: ["Agent Authority → BLOCK", "Intent Alignment → BLOCK"], status: "INFO" },
      { time: "09:58:18", source: "FINAL DECISION", description: "BLOCKED", isTerminal: true, status: "BLOCKED" }
    ],
    policiesTriggered: [
      { name: "Financial Product Restrictions", decision: "BLOCK" },
      { name: "Agent Spending Limits", decision: "BLOCK" },
      { name: "Intent Alignment", decision: "BLOCK" }
    ],
    evidence: [
      { id: "01", type: "User Intent", description: '"Buy laptop under ₹80K"' },
      { id: "02", type: "Agent Action", description: "Requested financial product" },
      { id: "03", type: "Transaction", description: "PAY-92829 (₹1,50,000)" },
      { id: "04", type: "Policy", description: "Financial Product Restrictions v4" },
      { id: "05", type: "Risk Event", description: "SEC-99382" },
      { id: "06", type: "Agent History", description: "1 previous policy violation" }
    ],
    paymentId: "PAY-92829",
  },
  {
    id: "SEC-99381",
    title: "Policy Threshold",
    severity: "HIGH",
    status: "INVESTIGATING",
    agentId: "AGT-7F31A9",
    agentName: "Shopping Agent",
    description: "Spending limit exceeded for current session.",
    value: 52000,
    detectedAt: new Date(Date.now() - 18 * 60000).toISOString(),
    riskScore: 78,
    confidence: 85,
    intentAlignment: 88,
    originalIntent: "Buy Lenovo ThinkPad",
    executedIntent: "Purchase Lenovo ThinkPad X1 Carbon",
    divergenceSignals: [
      { type: "Value mismatch", userRequested: "None specified", agentRequested: "₹52,000 (Exceeds ₹50,000 auto-approval threshold)" }
    ],
    trajectory: [
      { time: "10:15:02", source: "USER INTENT", description: '"Buy Lenovo ThinkPad"', status: "INFO" },
      { time: "10:15:10", source: "PAYMENT REQUEST", description: "₹52,000", status: "INFO" },
      { time: "10:15:11", source: "POLICY ENGINE", description: "Agent Spending Limits → REVIEW", status: "INFO" },
      { time: "10:15:11", source: "FINAL DECISION", description: "REVIEW REQUIRED", isTerminal: true, status: "REVIEW" }
    ],
    policiesTriggered: [
      { name: "Agent Spending Limits", decision: "REVIEW" }
    ],
    evidence: [
      { id: "01", type: "Transaction", description: "PAY-92828 (₹52,000)" }
    ],
    paymentId: "PAY-92828",
    orderId: "ORD-48290"
  },
  {
    id: "SEC-99380",
    title: "Merchant Anomaly",
    severity: "HIGH",
    status: "INVESTIGATING",
    agentId: "AGT-9X42E7",
    agentName: "Finance Agent",
    description: "Unverified merchant attempted to charge.",
    value: 84000,
    detectedAt: new Date(Date.now() - 32 * 60000).toISOString(),
    riskScore: 82,
    confidence: 91,
    intentAlignment: 95,
    originalIntent: "Pay the marketing invoice",
    executedIntent: "Pay invoice to AdTech Corp",
    divergenceSignals: [
      { type: "Merchant Reputation", userRequested: "Known vendor", agentRequested: "AdTech Corp (Unverified, newly registered)" }
    ],
    trajectory: [
      { time: "11:00:00", source: "PAYMENT REQUEST", description: "₹84,000 to AdTech Corp", status: "INFO" },
      { time: "11:00:01", source: "POLICY ENGINE", description: "Merchant Verification → REVIEW", status: "INFO" },
      { time: "11:00:01", source: "FINAL DECISION", description: "REVIEW REQUIRED", isTerminal: true, status: "REVIEW" }
    ],
    policiesTriggered: [
      { name: "Merchant Verification", decision: "REVIEW" }
    ],
    evidence: [
      { id: "01", type: "Merchant", description: "Score: 21 (Unverified)" }
    ]
  },
  {
    id: "SEC-99379",
    title: "Velocity Spike",
    severity: "LOW",
    status: "RESOLVED",
    agentId: "AGT-9X42E7",
    agentName: "Finance Agent",
    description: "5 transactions executed in 10 minutes.",
    value: 21500,
    detectedAt: new Date(Date.now() - 120 * 60000).toISOString(),
    riskScore: 45,
    confidence: 99,
    intentAlignment: 98,
    originalIntent: "Pay all pending utility bills",
    executedIntent: "Paid 5 separate utility bills sequentially",
    divergenceSignals: [],
    trajectory: [
      { time: "08:30:00", source: "PAYMENT REQUEST", description: "5 consecutive requests (₹21,500 total)", status: "INFO" },
      { time: "08:30:05", source: "POLICY ENGINE", description: "Transaction Velocity → REVIEW", status: "INFO" },
      { time: "08:30:05", source: "FINAL DECISION", description: "REVIEW REQUIRED", isTerminal: true, status: "REVIEW" }
    ],
    policiesTriggered: [
      { name: "Transaction Velocity", decision: "REVIEW" }
    ],
    evidence: [
      { id: "01", type: "User Intent", description: "Batch processing authorized" }
    ]
  }
];

export const INVESTIGATION_METRICS = {
  openCases: 4,
  highRisk: 2,
  blocked: 7,
  valueAtRisk: 184200,
  avgInvestigateTime: "8m 42s",
  avgResolveTime: "23m 11s",
  aiAssisted: 87,
  containmentRate: 100,
  falsePositives: 2
};
