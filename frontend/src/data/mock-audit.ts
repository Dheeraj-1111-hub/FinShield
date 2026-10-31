export type EventSeverity = 'INFO' | 'NOTICE' | 'WARNING' | 'HIGH' | 'CRITICAL';
export type EventResult = 'BLOCKED' | 'ALLOWED' | 'EXECUTED' | 'UPDATED' | 'CREATED' | 'PASSED';
export type EventCategory = 'Agent' | 'Financial' | 'Policy' | 'Security' | 'Investigation' | 'System';

export interface AuditEvent {
  id: string;
  time: string;
  event: string;
  actor: string;
  result: EventResult;
  severity: EventSeverity;
  category: EventCategory;
  amount?: string;
  merchant?: string;
  traceId: string;
  agentId?: string;
  policyId?: string;
  transactionId?: string;
  investigationId?: string;
  hash: string;
  prevHash: string;
  chainPosition: number;
}

export const AUDIT_STATS = {
  eventsToday: 1284,
  eventsTodayDelta: 18.4,
  criticalEvents: 7,
  criticalEventsDelta: -2,
  agentActions: 842,
  agentActionsPercentage: 65.6,
  integrityVerified: true,
  lastVerification: "00:41:12",
  totalEventsChain: 1284921,
  ingestionRate: 99.99,
  avgLatencyMs: 184
};

export const EVENT_DISTRIBUTION = [
  { category: "Agent actions", count: 842, width: "65%" },
  { category: "Policy decisions", count: 214, width: "17%" },
  { category: "Financial events", count: 126, width: "10%" },
  { category: "Security events", count: 61, width: "5%" },
  { category: "System events", count: 41, width: "3%" }
];

export const CRITICAL_EVENTS = [
  { event: "Payment blocked", actor: "Shopping Agent", detail: "₹150,000", timeAgo: "2m ago" },
  { event: "Intent divergence", actor: "Shopping Agent", detail: "", timeAgo: "3m ago" },
  { event: "Policy modified", actor: "Admin", detail: "", timeAgo: "18m ago" },
  { event: "Tool auth denied", actor: "Finance Agent", detail: "", timeAgo: "32m ago" }
];

export const AUDIT_STREAM: AuditEvent[] = [
  {
    id: "EVT-928421",
    time: "00:41:08",
    event: "Payment blocked",
    actor: "Shopping Agent",
    result: "BLOCKED",
    severity: "CRITICAL",
    category: "Financial",
    amount: "₹150,000",
    merchant: "TechNova Electronics",
    traceId: "TRC-55192",
    agentId: "AGT-7F31A9",
    policyId: "POL-001",
    transactionId: "TXN-882103",
    investigationId: "SEC-99382",
    hash: "8f92c1d7...e42a",
    prevHash: "7bc81a42...9f10",
    chainPosition: 1284921
  },
  {
    id: "EVT-928420",
    time: "00:40:52",
    event: "Policy evaluated",
    actor: "Policy Engine",
    result: "ALLOWED",
    severity: "INFO",
    category: "Policy",
    traceId: "TRC-55191",
    hash: "7bc81a42...9f10",
    prevHash: "3ab90c12...4d5e",
    chainPosition: 1284920
  },
  {
    id: "EVT-928419",
    time: "00:40:31",
    event: "Agent action",
    actor: "Finance Agent",
    result: "EXECUTED",
    severity: "NOTICE",
    category: "Agent",
    traceId: "TRC-55190",
    hash: "3ab90c12...4d5e",
    prevHash: "9cd12e34...5f6a",
    chainPosition: 1284919
  },
  {
    id: "EVT-928418",
    time: "00:39:44",
    event: "Policy modified",
    actor: "Admin",
    result: "UPDATED",
    severity: "HIGH",
    category: "Policy",
    traceId: "TRC-55189",
    hash: "9cd12e34...5f6a",
    prevHash: "4ef56a78...1b2c",
    chainPosition: 1284918
  },
  {
    id: "EVT-928417",
    time: "00:38:19",
    event: "Investigation opened",
    actor: "Risk Engine",
    result: "CREATED",
    severity: "HIGH",
    category: "Investigation",
    traceId: "TRC-55188",
    hash: "4ef56a78...1b2c",
    prevHash: "5gh78b90...2c3d",
    chainPosition: 1284917
  },
  {
    id: "EVT-928416",
    time: "00:37:52",
    event: "Security test",
    actor: "Security Lab",
    result: "PASSED",
    severity: "INFO",
    category: "Security",
    traceId: "TRC-55187",
    hash: "5gh78b90...2c3d",
    prevHash: "6ij90c12...3d4e",
    chainPosition: 1284916
  },
  {
    id: "EVT-928415",
    time: "00:36:11",
    event: "Tool invocation",
    actor: "Travel Agent",
    result: "BLOCKED",
    severity: "WARNING",
    category: "Agent",
    traceId: "TRC-55186",
    hash: "6ij90c12...3d4e",
    prevHash: "7kl12d34...4e5f",
    chainPosition: 1284915
  }
];
