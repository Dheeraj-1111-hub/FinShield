export type FulfillmentStatus = 
  | 'PROCESSING'
  | 'CONFIRMED'
  | 'PACKED'
  | 'SHIPPED'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'CANCELLED'
  | 'RETURNED';

export type FinshieldOrderDecision = 'ALLOW' | 'REVIEW' | 'BLOCK' | 'PENDING';

export interface OrderLifecycleEvent {
  status: FulfillmentStatus | 'INTENT_CREATED' | 'PRODUCT_SELECTED' | 'ORDER_PLACED';
  timestamp: string;
  location?: string;
  details?: string;
}

export interface PurchaseIntent {
  originalRequest: string;
  agentSelectionReasoning: string;
  intentAlignmentScore: number; // 0-100
  factors: {
    budget: boolean;
    performance: boolean;
    merchantReliability: boolean;
    availability: boolean;
  };
  alternatives: Array<{
    name: string;
    price: number;
    merchant: string;
    matchScore: number;
    selected: boolean;
  }>;
}

export interface Order {
  id: string;
  agentId: string;
  sessionId: string;
  paymentId?: string;
  investigationId?: string;
  
  product: string;
  productDetails: string;
  merchant: string;
  
  amount: number;
  currency: string;
  
  finshieldDecision: FinshieldOrderDecision;
  fulfillmentStatus: FulfillmentStatus;
  
  createdAt: string;
  expectedDelivery?: string;
  deliveredAt?: string;
  
  trackingId?: string;
  carrier?: string;
  
  intent: PurchaseIntent;
  lifecycle: OrderLifecycleEvent[];
}

export const MOCK_ORDERS: Order[] = [
  {
    id: "ORD-48291",
    agentId: "AGT-7F31A9", // Shopping Agent
    sessionId: "SES-8A72D1",
    paymentId: "PAY-92831",
    product: "Dell XPS 15",
    productDetails: "Core Ultra 7, 16GB RAM, 512GB SSD",
    merchant: "Dell Store",
    amount: 74999,
    currency: "INR",
    finshieldDecision: "ALLOW",
    fulfillmentStatus: "DELIVERED",
    createdAt: "2026-09-01T22:41:07Z",
    expectedDelivery: "2026-09-04T18:00:00Z",
    deliveredAt: "2026-09-04T11:42:00Z",
    trackingId: "TRK-928371",
    carrier: "Example Logistics",
    intent: {
      originalRequest: "Buy me a laptop below ₹80,000.",
      agentSelectionReasoning: "The selected offer maximized overall purchase utility while remaining within the user's constraints. Chosen over cheaper options due to merchant reliability.",
      intentAlignmentScore: 97,
      factors: {
        budget: true,
        performance: true,
        merchantReliability: true,
        availability: true
      },
      alternatives: [
        { name: "Dell XPS 15", price: 74999, merchant: "Dell Store", matchScore: 94, selected: true },
        { name: "Lenovo ThinkPad X1", price: 72000, merchant: "Lenovo Store", matchScore: 91, selected: false },
        { name: "HP Spectre", price: 76499, merchant: "HP Store", matchScore: 88, selected: false }
      ]
    },
    lifecycle: [
      { status: 'INTENT_CREATED', timestamp: "2026-09-01T22:38:12Z" },
      { status: 'PRODUCT_SELECTED', timestamp: "2026-09-01T22:40:18Z" },
      { status: 'ORDER_PLACED', timestamp: "2026-09-01T22:41:07Z" },
      { status: 'CONFIRMED', timestamp: "2026-09-01T22:43:00Z" },
      { status: 'PACKED', timestamp: "2026-09-02T09:12:00Z", location: "Mumbai Hub" },
      { status: 'SHIPPED', timestamp: "2026-09-02T14:31:00Z", location: "Mumbai Transit" },
      { status: 'OUT_FOR_DELIVERY', timestamp: "2026-09-04T07:15:00Z", location: "Hyderabad Local" },
      { status: 'DELIVERED', timestamp: "2026-09-04T11:42:00Z", location: "Destination" },
    ]
  },
  {
    id: "ORD-48290",
    agentId: "AGT-7F31A9", // Shopping Agent
    sessionId: "SES-8A72D2",
    paymentId: "PAY-92830",
    product: "Lenovo ThinkPad X1",
    productDetails: "Core i7, 16GB RAM, 1TB SSD",
    merchant: "Lenovo Store",
    amount: 52000,
    currency: "INR",
    finshieldDecision: "REVIEW",
    fulfillmentStatus: "PROCESSING",
    createdAt: "2026-09-05T09:15:00Z",
    intent: {
      originalRequest: "Buy a developer laptop for new hire.",
      agentSelectionReasoning: "Excellent keyboard and reliability score. Requires human review due to policy threshold.",
      intentAlignmentScore: 98,
      factors: {
        budget: true,
        performance: true,
        merchantReliability: true,
        availability: true
      },
      alternatives: [
        { name: "Lenovo ThinkPad X1", price: 52000, merchant: "Lenovo Store", matchScore: 95, selected: true }
      ]
    },
    lifecycle: [
      { status: 'INTENT_CREATED', timestamp: "2026-09-05T09:10:00Z" },
      { status: 'PRODUCT_SELECTED', timestamp: "2026-09-05T09:14:00Z" },
      { status: 'ORDER_PLACED', timestamp: "2026-09-05T09:15:00Z" }
    ]
  },
  {
    id: "ORD-48289",
    agentId: "AGT-2B94C1", // Travel Agent
    sessionId: "SES-9T11A1",
    paymentId: "PAY-92828",
    product: "Flight to Delhi",
    productDetails: "Economy, Round Trip, 1 Passenger",
    merchant: "MakeMyTrip",
    amount: 12400,
    currency: "INR",
    finshieldDecision: "ALLOW",
    fulfillmentStatus: "CONFIRMED",
    createdAt: "2026-09-06T10:05:00Z",
    intent: {
      originalRequest: "Book next week's flight to Delhi.",
      agentSelectionReasoning: "Complies with economy-only policy and meets schedule requirements.",
      intentAlignmentScore: 99,
      factors: {
        budget: true,
        performance: true,
        merchantReliability: true,
        availability: true
      },
      alternatives: []
    },
    lifecycle: [
      { status: 'INTENT_CREATED', timestamp: "2026-09-06T09:50:00Z" },
      { status: 'PRODUCT_SELECTED', timestamp: "2026-09-06T10:00:00Z" },
      { status: 'ORDER_PLACED', timestamp: "2026-09-06T10:05:00Z" },
      { status: 'CONFIRMED', timestamp: "2026-09-06T10:06:00Z" }
    ]
  },
  {
    id: "ORD-48288",
    agentId: "AGT-9X42E7", // Finance Agent
    sessionId: "SES-3F99B1",
    paymentId: "PAY-92829",
    investigationId: "INV-2918",
    product: "Investment-linked financial product",
    productDetails: "High-yield unauthorized instrument",
    merchant: "Unknown Store",
    amount: 150000,
    currency: "INR",
    finshieldDecision: "BLOCK",
    fulfillmentStatus: "CANCELLED",
    createdAt: "2026-09-06T12:30:00Z",
    intent: {
      originalRequest: "Sweep idle cash into short term bonds.",
      agentSelectionReasoning: "Attempted to maximize yield but selected unauthorized counterparty.",
      intentAlignmentScore: 4,
      factors: {
        budget: false,
        performance: true,
        merchantReliability: false,
        availability: true
      },
      alternatives: []
    },
    lifecycle: [
      { status: 'INTENT_CREATED', timestamp: "2026-09-06T12:20:00Z" },
      { status: 'PRODUCT_SELECTED', timestamp: "2026-09-06T12:28:00Z" },
      { status: 'ORDER_PLACED', timestamp: "2026-09-06T12:30:00Z", details: "Intercepted" },
      { status: 'CANCELLED', timestamp: "2026-09-06T12:30:01Z", details: "Blocked by FINSHIELD" }
    ]
  }
];
