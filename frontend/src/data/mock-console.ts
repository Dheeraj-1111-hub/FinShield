export type LogLevel = 'info' | 'warn' | 'error' | 'success';

export interface ConsoleEvent {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  level: LogLevel;
  details?: any;
}

export interface TrajectoryStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'blocked';
  timestamp?: string;
  details?: any;
  authorityId?: string;
  intentId?: string;
  alignmentResult?: "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN";
}

export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'blocked';
  startTime: string;
  durationMs?: number;
  input: any;
  output?: any;
}

export interface FinshieldEvaluation {
  id: string;
  timestamp: string;
  intentAlignment: number | "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN" | "NOT EVALUATED";
  transactionRisk: 'LOW' | 'MEDIUM' | 'HIGH' | 'NOT EVALUATED';
  policyResult: 'PASS' | 'REVIEW' | 'FAIL' | 'NOT EVALUATED';
  authorityCheck: 'PASS' | 'EXCEEDED' | 'NOT EVALUATED';
  decision: 'ALLOW' | 'REVIEW_REQUIRED' | 'BLOCK' | 'FAILED' | 'NOT EVALUATED' | 'UNAVAILABLE';
  actionContext: {
    type: string;
    amount?: number;
    target?: string;
  };
  reasoning?: string;
  runId?: string;
  actionId?: string;
}

export interface AgentSession {
  id: string;
  agentId: string;
  title: string;
  status: 'running' | 'completed' | 'blocked' | 'failed';
  startTime: string;
  endTime?: string;
  userIntent: string;
  trajectory: TrajectoryStep[];
  toolCalls: ToolCall[];
  evaluations: FinshieldEvaluation[];
  events: ConsoleEvent[];
}

// MOCK DATA

export const MOCK_SESSIONS: AgentSession[] = [
  {
    id: "SES-8A72D1",
    agentId: "AGT-7F31A9", // Shopping Agent
    title: "Buy laptop under ₹80K",
    status: "completed",
    startTime: "2026-09-01T10:41:04Z",
    endTime: "2026-09-01T10:41:22Z",
    userIntent: "Buy me the best laptop under ₹80,000. Prefer performance and battery life.",
    trajectory: [
      { id: "t1", name: "Understand user request", status: "completed", timestamp: "10:41:05" },
      { id: "t2", name: "Extract constraints (Budget: ₹80K, Priority: Perf+Batt)", status: "completed", timestamp: "10:41:05" },
      { id: "t3", name: "Search products (18 candidates found)", status: "completed", timestamp: "10:41:07" },
      { id: "t4", name: "Compare products (8 candidates remaining)", status: "completed", timestamp: "10:41:09" },
      { id: "t5", name: "Verify merchants", status: "completed", timestamp: "10:41:12" },
      { id: "t6", name: "Evaluate purchase", status: "completed", timestamp: "10:41:14" },
      { id: "t7", name: "Execute payment", status: "completed", timestamp: "10:41:21", authorityId: "AUTH-8921X", intentId: "INT-4821M", alignmentResult: "ALIGNED" }
    ],
    toolCalls: [
      {
        id: "req_92831",
        name: "product_search.search",
        status: "completed",
        startTime: "10:41:06.012",
        durationMs: 842,
        input: { query: "laptop", max_price: 80000, sort: "performance_battery" },
        output: { results_count: 18, top_candidate: "Dell XPS 15" }
      },
      {
        id: "req_92832",
        name: "merchant.verify",
        status: "completed",
        startTime: "10:41:11.200",
        durationMs: 231,
        input: { merchant_id: "m_dell_official" },
        output: { risk_score: "LOW", verified: true }
      }
    ],
    evaluations: [
      {
        id: "eval_1",
        timestamp: "10:41:14.331",
        intentAlignment: 0.96,
        transactionRisk: "LOW",
        policyResult: "PASS",
        authorityCheck: "PASS",
        decision: "ALLOW",
        actionContext: {
          type: "Purchase",
          amount: 74999,
          target: "Dell XPS 15"
        },
        reasoning: "Transaction matches user intent. Amount within authority. Merchant verified. Normal user behavior."
      }
    ],
    events: [
      { id: "e1", timestamp: "10:41:04.102", type: "intent.received", message: "User intent received", level: "info" },
      { id: "e2", timestamp: "10:41:06.854", type: "tool.completed", message: "product_search completed (842ms)", level: "success" },
      { id: "e3", timestamp: "10:41:14.300", type: "risk.evaluated", message: "Fraud probability: 1.8%", level: "info" },
      { id: "e4", timestamp: "10:41:14.331", type: "policy.evaluated", message: "FINSHIELD permitted action", level: "success" }
    ]
  },
  {
    id: "SES-9X42L8",
    agentId: "AGT-7F31A9", // Shopping Agent - adversarial example
    title: "Buy laptop under ₹80K",
    status: "blocked",
    startTime: "2026-09-01T22:41:04Z",
    userIntent: "Buy me the best laptop under ₹80,000.",
    trajectory: [
      { id: "t1", name: "Understand user request", status: "completed", timestamp: "22:41:05" },
      { id: "t2", name: "Extract constraints (Budget: ₹80K)", status: "completed", timestamp: "22:41:05" },
      { id: "t3", name: "Search products (18 candidates found)", status: "completed", timestamp: "22:41:07" },
      { id: "t4", name: "Compare products (8 candidates remaining)", status: "completed", timestamp: "22:41:09" },
      { id: "t5", name: "Verify merchants", status: "completed", timestamp: "22:41:12" },
      { id: "t6", name: "Evaluate purchase", status: "blocked", timestamp: "22:41:14" },
      { id: "t7", name: "Execute payment", status: "pending", authorityId: "AUTH-8921X", intentId: "INT-4821M", alignmentResult: "MISALIGNED" }
    ],
    toolCalls: [
      {
        id: "req_92999",
        name: "product_search.search",
        status: "completed",
        startTime: "22:41:06.012",
        durationMs: 842,
        input: { query: "laptop", max_price: 80000 },
        output: { results_count: 18 }
      },
      {
        id: "req_93000",
        name: "payment.create_intent",
        status: "blocked",
        startTime: "22:41:14.100",
        durationMs: 45,
        input: { amount: 150000, description: "Investment-linked financial product" },
        output: { error: "Blocked by FINSHIELD" }
      }
    ],
    evaluations: [
      {
        id: "eval_2",
        timestamp: "22:41:14.145",
        intentAlignment: 0.04,
        transactionRisk: "HIGH",
        policyResult: "FAIL",
        authorityCheck: "EXCEEDED",
        decision: "BLOCK",
        actionContext: {
          type: "Purchase",
          amount: 150000,
          target: "Investment-linked financial product"
        },
        reasoning: "Intent divergence detected. Original intent: Laptop < ₹80,000. Requested action: Financial product ₹1,50,000."
      }
    ],
    events: [
      { id: "e1", timestamp: "22:41:04.102", type: "intent.received", message: "User intent received", level: "info" },
      { id: "e2", timestamp: "22:41:06.854", type: "tool.completed", message: "product_search completed (842ms)", level: "success" },
      { id: "e3", timestamp: "22:41:14.100", type: "risk.evaluated", message: "Fraud probability: HIGH", level: "warn" },
      { id: "e4", timestamp: "22:41:14.145", type: "policy.evaluated", message: "FINSHIELD BLOCKED action", level: "error" }
    ]
  }
];
