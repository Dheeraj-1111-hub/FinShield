import { api } from "@/lib/api-client";

export type PaymentStatus = "CREATED" | "REQUIRES_AUTHORIZATION" | "AUTHORIZED" | "CAPTURED" | "FAILED" | "CANCELLED";

export interface Payment {
  id: string;
  workspace_id: string;
  agent_id?: string;
  order_id?: string;
  payment_intent_id: string;
  idempotency_key: string;
  amount: number;
  currency: string;
  status: PaymentStatus;
  payment_method_type?: string;
  merchant_reference?: string;
  metadata?: Record<string, any>;
  failure_code?: string;
  failure_reason?: string;
  created_at: string;
  updated_at: string;
  
  agent_name?: string;
  run_id?: string;
  action_id?: string;
  merchant_id?: string;
  merchant_name?: string;
  order_status?: string;
  risk_level?: string;
  risk_score?: number;
  risk_assessment_id?: string;
  gate_decision?: string;
  gate_decision_id?: string;
  intent_id?: string;
  authority_id?: string;
  policy_decision?: string;
  approval_request_id?: string;
  approval_status?: string;
}

export interface PaymentCreate {
  payment_intent_id: string;
  idempotency_key: string;
  agent_id?: string;
  order_id?: string;
  amount?: number;
  currency?: string;
  payment_method_type?: string;
  merchant_reference?: string;
  metadata?: Record<string, any>;
}

export interface PaymentMetrics {
  total_volume: number;
  transactions: number;
  captured_count: number;
  failed_count: number;
  failed_value: number;
}

export const paymentsApi = {
  list: async (): Promise<Payment[]> => {
    const { data } = await api.get<Payment[]>("/payments");
    return data;
  },

  getMetrics: async (): Promise<PaymentMetrics> => {
    const { data } = await api.get<PaymentMetrics>('/payments/metrics');
    return data;
  },

  get: async (id: string): Promise<Payment> => {
    const { data } = await api.get<Payment>(`/payments/${id}`);
    return data;
  },

  createIntent: async (payment: PaymentCreate): Promise<Payment> => {
    const { data } = await api.post<Payment>("/payments/intents", payment);
    return data;
  },

  authorize: async (id: string): Promise<Payment> => {
    const { data } = await api.post<Payment>(`/payments/${id}/authorize`);
    return data;
  },

  capture: async (id: string): Promise<Payment> => {
    const { data } = await api.post<Payment>(`/payments/${id}/capture`);
    return data;
  },

  cancel: async (id: string): Promise<Payment> => {
    const { data } = await api.post<Payment>(`/payments/${id}/cancel`);
    return data;
  }
};
