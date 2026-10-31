export type AgentStatus = "Active" | "Idle" | "Paused" | "Suspended" | "Error";
export type RiskLevel = "None" | "Low" | "Medium" | "High" | "Critical";
export type AgentType = "Shopping" | "Finance" | "Travel" | "Research" | "Custom";

export interface Agent {
  id: string;
  name: string;
  type: AgentType;
  description: string;
  status: AgentStatus;
  lastActive: string;
  
  // Current Task (if Active)
  currentTask?: {
    name: string;
    steps: { name: string; status: "completed" | "current" | "pending" }[];
    intentAlignment: number; // 0-100
  };

  // Financial Authority
  financialAuthority: {
    monthlyLimit: number;
    dailyLimit: number;
    transactionLimit: number;
    approvalThreshold: number;
    monthlyUsed: number;
  };

  // Activity & Risk
  transactions: number;
  risk: RiskLevel;
  isProtected: boolean;

  // Configuration
  capabilities: {
    shopping: string[];
    financial: string[];
    restricted: string[];
  };
  tools: { name: string; authorized: boolean }[];
  policies: { name: string; description: string; status: "Enforced" | "Warning" }[];
  created: string;
}

export const MOCK_AGENTS: Agent[] = [
  {
    id: "AGT-7F31A9",
    name: "Shopping Agent",
    type: "Shopping",
    description: "Autonomous shopping assistant",
    status: "Active",
    lastActive: "12 sec ago",
    currentTask: {
      name: "Searching for laptops",
      steps: [
        { name: "Intent established", status: "completed" },
        { name: "Product search", status: "completed" },
        { name: "Comparing 8 products", status: "current" },
        { name: "Merchant verification", status: "pending" },
        { name: "Purchase authorization", status: "pending" },
      ],
      intentAlignment: 96,
    },
    financialAuthority: {
      monthlyLimit: 200000,
      dailyLimit: 100000,
      transactionLimit: 80000,
      approvalThreshold: 50000,
      monthlyUsed: 8420,
    },
    transactions: 124,
    risk: "Low",
    isProtected: true,
    capabilities: {
      shopping: ["Search products", "Compare products", "Check merchant reputation", "Add to cart", "Create order"],
      financial: ["Request payment", "View transaction status"],
      restricted: ["Transfer funds", "Modify bank account", "Purchase financial products"],
    },
    tools: [
      { name: "Product Search", authorized: true },
      { name: "Merchant Verification", authorized: true },
      { name: "Payment Gateway", authorized: true },
      { name: "Bank Transfer", authorized: false },
    ],
    policies: [
      { name: "Purchase Limit", description: "Maximum ₹10,000 / transaction", status: "Enforced" },
      { name: "Monthly Budget", description: "₹30,000", status: "Enforced" },
      { name: "Category Restriction", description: "Electronics only", status: "Enforced" },
      { name: "Intent Alignment", description: "Required", status: "Enforced" },
      { name: "Merchant Risk", description: "High-risk merchants blocked", status: "Enforced" },
    ],
    created: "2026-08-15T10:00:00Z",
  },
  {
    id: "AGT-2B94C1",
    name: "Travel Agent",
    type: "Travel",
    description: "Autonomous corporate travel booking",
    status: "Idle",
    lastActive: "2 hours ago",
    financialAuthority: {
      monthlyLimit: 0,
      dailyLimit: 0,
      transactionLimit: 0,
      approvalThreshold: 0,
      monthlyUsed: 0,
    },
    transactions: 0,
    risk: "None",
    isProtected: true,
    capabilities: {
      shopping: [],
      financial: [],
      restricted: ["All financial transactions disabled"],
    },
    tools: [
      { name: "Flight Search", authorized: true },
      { name: "Hotel Search", authorized: true },
      { name: "Payment Gateway", authorized: false },
    ],
    policies: [
      { name: "Booking Class", description: "Economy only", status: "Enforced" },
      { name: "Approval", description: "All bookings require approval", status: "Enforced" },
    ],
    created: "2026-08-20T14:30:00Z",
  },
  {
    id: "AGT-9X42E7",
    name: "Finance Agent",
    type: "Finance",
    description: "Treasury and liquidity manager",
    status: "Active",
    lastActive: "4 min ago",
    currentTask: {
      name: "Sweeping idle cash",
      steps: [
        { name: "Balance check", status: "completed" },
        { name: "Yield analysis", status: "completed" },
        { name: "Executing transfer", status: "current" },
      ],
      intentAlignment: 99,
    },
    financialAuthority: {
      monthlyLimit: 150000,
      dailyLimit: 50000,
      transactionLimit: 50000,
      approvalThreshold: 25000,
      monthlyUsed: 112000,
    },
    transactions: 42,
    risk: "Medium",
    isProtected: true,
    capabilities: {
      shopping: [],
      financial: ["View balances", "Initiate transfers", "Trade execution"],
      restricted: ["External withdrawals to unknown accounts"],
    },
    tools: [
      { name: "Banking API", authorized: true },
      { name: "Trading Desk API", authorized: true },
    ],
    policies: [
      { name: "Counterparty Risk", description: "Approved institutions only", status: "Enforced" },
      { name: "Transaction Limit", description: "Maximum ₹50,000 / transaction", status: "Enforced" },
      { name: "Liquidity Buffer", description: "Maintain ₹10,000 minimum", status: "Warning" },
    ],
    created: "2026-08-10T09:15:00Z",
  }
];

export const MOCK_AGENT_EVENTS = [
  { id: 1, agentId: "AGT-7F31A9", agentName: "Shopping Agent", type: "Execution", message: "Started execution", time: "12 sec ago", status: "info" },
  { id: 2, agentId: "AGT-9X42E7", agentName: "Finance Agent", type: "Task", message: "Completed analysis", time: "4 min ago", status: "success" },
  { id: 3, agentId: "AGT-7F31A9", agentName: "Shopping Agent", type: "Security", message: "Triggered approval", time: "18 min ago", status: "warning" },
  { id: 4, agentId: "AGT-2B94C1", agentName: "Travel Agent", type: "Task", message: "Completed task", time: "2 hr ago", status: "success" },
];
