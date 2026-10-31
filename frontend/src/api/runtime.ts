import { api } from "@/lib/api-client";

export interface ToolDefinition {
  name: string;
  description: string;
  required_capabilities: string[];
  input_schema: Record<string, any>;
}

export interface AgentRun {
  id: string;
  agent_id: string;
  workspace_id: string;
  session_id: string | null;
  status: "QUEUED" | "RUNNING" | "WAITING" | "WAITING_FOR_APPROVAL" | "COMPLETED" | "FAILED" | "CANCELLED" | "BLOCKED";
  trigger_type: string | null;
  input: string;
  output: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  actions: AgentAction[];
}

export interface AgentAction {
  id: string;
  run_id: string;
  sequence_number: number;
  tool_name: string;
  input: Record<string, any> | null;
  output: Record<string, any> | null;
  status: "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED" | "DENIED";
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  authority_id?: string | null;
  intent_id?: string | null;
  alignment_result?: "ALIGNED" | "MISALIGNED" | "PARTIAL" | "UNKNOWN" | null;
  alignment_signals?: any[] | null;
}

export const runtimeApi = {
  getTools: () => {
    return api.get<ToolDefinition[]>("/agent-runtime/tools").then(res => res.data);
  },
  
  createRun: (data: { agent_id: string; input: string; trigger_type?: string; session_id?: string }) => {
    return api.post<AgentRun>("/agent-runtime/runs", data).then(res => res.data);
  },

  listRuns: (agentId: string) => {
    return api.get<AgentRun[]>(`/agent-runtime/agents/${agentId}/runs`).then(res => res.data);
  },

  getRun: (runId: string) => {
    return api.get<AgentRun>(`/agent-runtime/runs/${runId}`).then(res => res.data);
  },

  cancelRun: (runId: string) => {
    return api.post<AgentRun>(`/agent-runtime/runs/${runId}/cancel`).then(res => res.data);
  },

  executeAction: (runId: string, data: { tool_name: string; input: any }) => {
    return api.post<AgentAction>(`/agent-runtime/runs/${runId}/actions`, data).then(res => res.data);
  },

  finishRun: (runId: string, output: string) => {
    return api.post<AgentRun>(`/agent-runtime/runs/${runId}/finish`, { output }).then(res => res.data);
  }
};
