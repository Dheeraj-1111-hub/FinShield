from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.investigation import (
    InvestigationStatus, 
    InvestigationPriority, 
    InvestigationType,
    ResolutionType
)

class SecurityEventBase(BaseModel):
    workspace_id: str
    event_type: str
    severity: str
    source_type: str
    source_id: str
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_key: Optional[str] = None

class SecurityEventCreate(SecurityEventBase):
    pass

class SecurityEventResponse(SecurityEventBase):
    id: str
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvestigationEvidenceBase(BaseModel):
    evidence_type: str
    entity_type: str
    entity_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    snapshot: Dict[str, Any]
    source_timestamp: datetime
    sequence_number: int = 0

class InvestigationEvidenceCreate(InvestigationEvidenceBase):
    pass

class InvestigationEvidenceResponse(InvestigationEvidenceBase):
    id: str
    investigation_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvestigationTimelineEventBase(BaseModel):
    timestamp: datetime
    sequence_number: int = 0
    event_type: str
    entity_type: str
    entity_id: str
    actor_type: Optional[str] = None
    actor_id: Optional[str] = None
    severity: Optional[str] = None
    title: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")

class InvestigationTimelineEventCreate(InvestigationTimelineEventBase):
    pass

class InvestigationTimelineEventResponse(InvestigationTimelineEventBase):
    id: str
    investigation_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class InvestigationNoteBase(BaseModel):
    content: str

class InvestigationNoteCreate(InvestigationNoteBase):
    pass

class InvestigationNoteUpdate(InvestigationNoteBase):
    pass

class InvestigationNoteResponse(InvestigationNoteBase):
    id: str
    investigation_id: str
    author_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvestigationBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: InvestigationType
    priority: InvestigationPriority = InvestigationPriority.MEDIUM
    
class InvestigationCreate(InvestigationBase):
    source_type: str
    source_id: str
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    intent_id: Optional[str] = None
    intent_version: Optional[int] = None
    authority_id: Optional[str] = None
    authority_version: Optional[int] = None
    risk_assessment_id: Optional[str] = None
    gate_decision_id: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    merchant_id: Optional[str] = None

class InvestigationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[InvestigationPriority] = None
    assigned_to: Optional[str] = None

class InvestigationResolution(BaseModel):
    resolution: ResolutionType
    resolution_reason: str

class InvestigationResponse(InvestigationBase):
    id: str
    workspace_id: str
    status: InvestigationStatus
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    
    source_type: str
    source_id: str
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    
    intent_id: Optional[str] = None
    intent_version: Optional[int] = None
    authority_id: Optional[str] = None
    authority_version: Optional[int] = None
    risk_assessment_id: Optional[str] = None
    gate_decision_id: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    merchant_id: Optional[str] = None
    
    opened_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    resolution: Optional[ResolutionType] = None
    resolution_reason: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    original_intent: Optional[str] = None
    executed_intent: Optional[str] = None
    proposed_action: Optional[str] = None
    decision_reason: Optional[str] = None
    outcome: Optional[str] = None
    intent_alignment: Optional[int] = None
    divergence_signals: List[Dict[str, Any]] = Field(default_factory=list)
    alignment_signals: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class InvestigationExportResponse(BaseModel):
    investigation: InvestigationResponse
    evidence: List[InvestigationEvidenceResponse]
    timeline: List[InvestigationTimelineEventResponse]
    notes: List[InvestigationNoteResponse]
