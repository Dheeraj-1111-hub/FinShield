import enum
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, JSON, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class InvestigationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class InvestigationPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class InvestigationType(str, enum.Enum):
    RISK_ANOMALY = "RISK_ANOMALY"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INTENT_DRIFT = "INTENT_DRIFT"
    AUTHORITY_VIOLATION = "AUTHORITY_VIOLATION"
    AGENT_BEHAVIOR = "AGENT_BEHAVIOR"
    PAYMENT_ANOMALY = "PAYMENT_ANOMALY"
    MERCHANT_ANOMALY = "MERCHANT_ANOMALY"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    TOOL_OUTPUT_POISONING = "TOOL_OUTPUT_POISONING"
    SECURITY_EVENT = "SECURITY_EVENT"
    OTHER = "OTHER"

class ResolutionType(str, enum.Enum):
    FALSE_POSITIVE = "FALSE_POSITIVE"
    CONFIRMED_THREAT = "CONFIRMED_THREAT"
    AUTHORIZED_BEHAVIOR = "AUTHORIZED_BEHAVIOR"
    POLICY_CONFIGURATION_ISSUE = "POLICY_CONFIGURATION_ISSUE"
    AGENT_MISBEHAVIOR = "AGENT_MISBEHAVIOR"
    MERCHANT_ISSUE = "MERCHANT_ISSUE"
    USER_ERROR = "USER_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    OTHER = "OTHER"

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    
    agent_id = Column(String, index=True, nullable=True)
    agent_run_id = Column(String, nullable=True)
    agent_action_id = Column(String, nullable=True)
    
    occurred_at = Column(DateTime(timezone=True), default=func.now())
    payload = Column(JSON, default={})
    correlation_key = Column(String, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now())

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, index=True, nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    type = Column(Enum(InvestigationType), nullable=False)
    status = Column(Enum(InvestigationStatus), default=InvestigationStatus.OPEN, nullable=False)
    priority = Column(Enum(InvestigationPriority), default=InvestigationPriority.MEDIUM, nullable=False)
    
    created_by = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    
    agent_id = Column(String, index=True, nullable=True)
    agent_run_id = Column(String, nullable=True)
    agent_action_id = Column(String, nullable=True)
    
    intent_id = Column(String, nullable=True)
    intent_version = Column(Integer, nullable=True)
    
    authority_id = Column(String, nullable=True)
    authority_version = Column(Integer, nullable=True)
    
    risk_assessment_id = Column(String, nullable=True)
    gate_decision_id = Column(String, nullable=True)
    
    payment_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    merchant_id = Column(String, nullable=True)
    
    opened_at = Column(DateTime(timezone=True), default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    resolution = Column(Enum(ResolutionType), nullable=True)
    resolution_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    metadata_ = Column("metadata", JSON, default={}) # Using metadata_ to avoid conflict with SQLAlchemy metadata

class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, index=True, nullable=False)
    
    evidence_type = Column(String, nullable=False) # e.g. RISK_ASSESSMENT, AGENT_ACTION, INTENT
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    snapshot = Column(JSON, nullable=False)
    
    source_timestamp = Column(DateTime(timezone=True), nullable=False)
    sequence_number = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=func.now())

class InvestigationTimelineEvent(Base):
    __tablename__ = "investigation_timeline_events"

    id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, index=True, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False)
    sequence_number = Column(Integer, default=0, nullable=False)
    
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    
    actor_type = Column(String, nullable=True)
    actor_id = Column(String, nullable=True)
    
    severity = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    metadata_ = Column("metadata", JSON, default={})
    
    created_at = Column(DateTime(timezone=True), default=func.now())

class InvestigationNote(Base):
    __tablename__ = "investigation_notes"

    id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, index=True, nullable=False)
    
    author_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
