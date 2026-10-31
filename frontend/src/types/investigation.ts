export type InvestigationStatus = 'OPEN' | 'IN_REVIEW' | 'ESCALATED' | 'RESOLVED' | 'CLOSED';
export type InvestigationPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type InvestigationType = 'UNAUTHORIZED_ACCESS' | 'POLICY_VIOLATION' | 'ANOMALOUS_BEHAVIOR' | 'FRAUD_ATTEMPT' | 'DATA_EXFILTRATION' | 'SYSTEM_ALERT' | 'OTHER';
export type ResolutionType = 'FALSE_POSITIVE' | 'CONFIRMED_THREAT' | 'AUTHORIZED_BEHAVIOR' | 'POLICY_CONFIGURATION_ISSUE' | 'AGENT_MISBEHAVIOR' | 'MERCHANT_ISSUE' | 'USER_ERROR' | 'SYSTEM_ERROR' | 'OTHER';

export interface SecurityEvent {
  id: string;
  workspace_id: string;
  agent_id: string;
  correlation_key: string;
  event_type: string;
  severity: string;
  source: string;
  title: string;
  description?: string;
  raw_data?: Record<string, any>;
  timestamp: string;
}

export interface Investigation {
  id: string;
  workspace_id: string;
  agent_id: string;
  agent_run_id?: string;
  title: string;
  description: string;
  status: InvestigationStatus;
  priority: InvestigationPriority;
  type: InvestigationType;
  assigned_to?: string;
  created_by?: string;
  resolution?: ResolutionType;
  resolution_reason?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  closed_at?: string;
  original_intent?: string;
  executed_intent?: string;
  proposed_action?: string;
  decision_reason?: string;
  outcome?: string;
  intent_alignment?: number;
  divergence_signals?: {
    type: string;
    userRequested?: string;
    agentRequested?: string;
    reason?: string;
  }[];
  alignment_signals?: {
    type: string;
    status: string;
    reason: string;
  }[];
  metadata?: Record<string, any>;
}

export interface InvestigationEvidence {
  id: string;
  investigation_id: string;
  evidence_type: string;
  entity_type: string;
  entity_id: string;
  title?: string;
  description?: string;
  snapshot: Record<string, any>;
  source_timestamp: string;
  sequence_number: number;
  created_at: string;
}

export interface InvestigationTimelineEvent {
  id: string;
  investigation_id: string;
  timestamp: string;
  sequence_number: number;
  event_type: string;
  entity_type?: string;
  entity_id?: string;
  actor_type?: string;
  actor_id?: string;
  severity?: string;
  title: string;
  description?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface InvestigationNote {
  id: string;
  investigation_id: string;
  author_id: string;
  content: string;
  is_internal_only: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvestigationCreate {
  agent_id: string;
  title: string;
  description: string;
  priority?: InvestigationPriority;
  type?: InvestigationType;
  assigned_to?: string;
}

export interface InvestigationResolutionReq {
  resolution: ResolutionType;
  resolution_reason: string;
}

export interface InvestigationNoteCreate {
  content: string;
  is_internal_only?: boolean;
}

export interface AssignRequest {
  assigned_to: string;
}
