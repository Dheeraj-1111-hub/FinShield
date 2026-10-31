from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from app.models.audit import EventCategory, EventSeverity, ActorType

class AuditEventCreate(BaseModel):
    event_type: str
    event_category: EventCategory
    severity: EventSeverity
    actor_type: ActorType
    actor_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class AuditEventResponse(BaseModel):
    id: str
    workspace_id: str
    event_type: str
    event_category: EventCategory
    severity: EventSeverity
    actor_type: ActorType
    actor_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    metadata_: Optional[Dict[str, Any]] = None
    workspace_sequence: int
    previous_event_hash: Optional[str] = None
    event_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

class BrokenLink(BaseModel):
    event_id: str
    reason: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None

class AuditIntegrityResponse(BaseModel):
    valid: bool
    checked_events: int
    first_event: Optional[str] = None
    last_event: Optional[str] = None
    broken_links: List[BrokenLink]
    chain_status: Optional[str] = "VALID"
    completeness_status: Optional[str] = "CHAIN_VALID_ONLY"
    completeness_note: Optional[str] = None

