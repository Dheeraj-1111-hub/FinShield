export type PaymentStatus = 
  | 'CREATED' 
  | 'EVALUATING' 
  | 'REVIEW_REQUIRED' 
  | 'BLOCKED' 
  | 'AUTHORIZED' 
  | 'CAPTURED' 
  | 'SETTLED' 
  | 'FAILED' 
  | 'REFUNDED';

export type FinshieldDecision = 'ALLOW' | 'REVIEW' | 'BLOCK' | 'PENDING';

export interface PaymentLifecycleEvent {
  status: PaymentStatus | 'FINSHIELD_EVALUATED';
  timestamp: string;
  details?: string;
}

export interface PaymentProviderRouting {
  provider: string;
  expectedUtility: number;
  successProbability: number;
  fraudRisk: number;
  latencyMs: number;
  cost: number;
  reason: string;
  alternatives: Array<{
    provider: string;
    expectedUtility: number;
  }>;
}

export interface FinshieldPaymentEvaluation {
  id: string;
  decision: FinshieldDecision;
  intentAlignment: number;
  riskScore: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  policyResult: 'PASS' | 'REVIEW' | 'FAIL';
  authorityCheck: 'PASS' | 'EXCEEDED';
  fraudProbability: number;
  merchantRisk: 'LOW' | 'MEDIUM' | 'HIGH';
  behavioralAnomaly: number;
  modelVersion: string;
  policyVersion: string;
  originalIntent?: string;
  reasoning?: string;
}

export interface Payment {
  id: string;
  agentId: string;
  sessionId?: string;
  orderId?: string;
  investigationId?: string;
  
  amount: number;
  currency: string;
  merchant: string;
  merchantDomain?: string;
  merchantFirstSeen?: string;
  product: string;
  
  status: PaymentStatus;
  
  finshield: FinshieldPaymentEvaluation;
  routing?: PaymentProviderRouting;
  
  createdAt: string;
  lifecycle: PaymentLifecycleEvent[];
}

export const MOCK_PAYMENTS: Payment[] = [
  {
    id: "PAY-92831",
    agentId: "AGT-7F31A9", // Shopping Agent
    sessionId: "SES-8A72D1",
    orderId: "ORD-48291",
    amount: 74999,
    currency: "INR",
    merchant: "Dell Store",
    merchantDomain: "dell.com",
    merchantFirstSeen: "12 months ago",
    product: "Dell XPS 15",
    status: "CAPTURED",
    createdAt: "2026-09-01T22:41:07Z",
    finshield: {
      id: "EVAL-92831",
      decision: "ALLOW",
      intentAlignment: 0.97,
      riskScore: "LOW",
      policyResult: "PASS",
      authorityCheck: "PASS",
      fraudProbability: 0.018,
      merchantRisk: "LOW",
      behavioralAnomaly: 0.04,
      modelVersion: "risk-v4",
      policyVersion: "shopping-policy-v2",
      originalIntent: "Buy a laptop under ₹80,000 with good performance and battery life.",
      reasoning: "Transaction matches user intent. Amount within authority. Merchant verified."
    },
    routing: {
      provider: "Provider B",
      expectedUtility: 0.91,
      successProbability: 0.96,
      fraudRisk: 0.008,
      latencyMs: 141,
      cost: 1.55,
      reason: "Highest expected utility under current risk and latency constraints.",
      alternatives: [
        { provider: "Provider A", expectedUtility: 0.81 },
        { provider: "Provider C", expectedUtility: 0.69 }
      ]
    },
    lifecycle: [
      { status: 'CREATED', timestamp: "2026-09-01T22:41:07.102Z" },
      { status: 'FINSHIELD_EVALUATED', timestamp: "2026-09-01T22:41:07.221Z" },
      { status: 'AUTHORIZED', timestamp: "2026-09-01T22:41:07.409Z" },
      { status: 'CAPTURED', timestamp: "2026-09-01T22:41:09.102Z" },
    ]
  },
  {
    id: "PAY-92830",
    agentId: "AGT-7F31A9",
    amount: 52000,
    currency: "INR",
    merchant: "Lenovo",
    product: "ThinkPad X1",
    status: "REVIEW_REQUIRED",
    createdAt: "2026-09-01T21:15:00Z",
    finshield: {
      id: "EVAL-92830",
      decision: "REVIEW",
      intentAlignment: 0.98,
      riskScore: "LOW",
      policyResult: "REVIEW",
      authorityCheck: "PASS",
      fraudProbability: 0.012,
      merchantRisk: "LOW",
      behavioralAnomaly: 0.02,
      modelVersion: "risk-v4",
      policyVersion: "shopping-policy-v2",
      originalIntent: "Laptop under ₹80,000",
      reasoning: "Transaction exceeds automatic approval threshold of ₹50,000."
    },
    lifecycle: [
      { status: 'CREATED', timestamp: "2026-09-01T21:15:00.100Z" },
      { status: 'FINSHIELD_EVALUATED', timestamp: "2026-09-01T21:15:00.250Z" },
      { status: 'REVIEW_REQUIRED', timestamp: "2026-09-01T21:15:00.300Z" }
    ]
  },
  {
    id: "PAY-92829",
    agentId: "AGT-8A22B4", // Finance Agent
    investigationId: "INV-2918",
    amount: 150000,
    currency: "INR",
    merchant: "Unknown Store",
    product: "Investment-linked financial product",
    status: "BLOCKED",
    createdAt: "2026-09-01T19:30:00Z",
    finshield: {
      id: "EVAL-92829",
      decision: "BLOCK",
      intentAlignment: 0.04,
      riskScore: "HIGH",
      policyResult: "FAIL",
      authorityCheck: "EXCEEDED",
      fraudProbability: 0.85,
      merchantRisk: "HIGH",
      behavioralAnomaly: 0.92,
      modelVersion: "risk-v4",
      policyVersion: "finance-policy-v1",
      originalIntent: "Laptop under ₹80,000",
      reasoning: "Intent divergence detected. Transaction exceeds agent authority."
    },
    lifecycle: [
      { status: 'CREATED', timestamp: "2026-09-01T19:30:00.000Z" },
      { status: 'FINSHIELD_EVALUATED', timestamp: "2026-09-01T19:30:00.500Z" },
      { status: 'BLOCKED', timestamp: "2026-09-01T19:30:00.600Z", details: "Intent divergence" }
    ]
  },
  {
    id: "PAY-92828",
    agentId: "AGT-3M99X1", // Travel Agent
    amount: 12400,
    currency: "INR",
    merchant: "MakeMyTrip",
    product: "Flight to Delhi",
    status: "CAPTURED",
    createdAt: "2026-09-01T10:05:00Z",
    finshield: {
      id: "EVAL-92828",
      decision: "ALLOW",
      intentAlignment: 0.99,
      riskScore: "LOW",
      policyResult: "PASS",
      authorityCheck: "PASS",
      fraudProbability: 0.005,
      merchantRisk: "LOW",
      behavioralAnomaly: 0.01,
      modelVersion: "risk-v4",
      policyVersion: "travel-policy-v1",
      reasoning: "Transaction parameters nominal."
    },
    lifecycle: [
      { status: 'CREATED', timestamp: "2026-09-01T10:05:00.000Z" },
      { status: 'FINSHIELD_EVALUATED', timestamp: "2026-09-01T10:05:00.200Z" },
      { status: 'AUTHORIZED', timestamp: "2026-09-01T10:05:01.000Z" },
      { status: 'CAPTURED', timestamp: "2026-09-01T10:05:02.000Z" },
    ]
  }
];
