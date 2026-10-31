import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

class RunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

class ActionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"
    PENDING_APPROVAL = "PENDING_APPROVAL"

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=lambda: f"run_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, index=True, nullable=True)

    # Explicit FK columns (previously in metadata_ JSON)
    intent_id = Column(String, ForeignKey("intents.id", ondelete="SET NULL"), nullable=True, index=True)
    authority_id = Column(String, ForeignKey("delegated_authorities.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(Enum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    trigger_type = Column(String, nullable=True) # e.g., "MANUAL", "API", "SCHEDULED"

    input = Column(Text, nullable=False)
    output = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    metadata_ = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
    agent = relationship("Agent")
    intent = relationship("Intent")
    authority = relationship("DelegatedAuthority")
    actions = relationship("AgentAction", back_populates="run", cascade="all, delete-orphan", order_by="AgentAction.sequence_number")




class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(String, primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:16]}")
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sequence_number = Column(Integer, nullable=False)
    tool_name = Column(String, nullable=False)
    
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    
    status = Column(Enum(ActionStatus), default=ActionStatus.QUEUED, nullable=False)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    # Intent & Authority context — stamped at execution time
    intent_id = Column(String, ForeignKey("intents.id", ondelete="SET NULL"), nullable=True)
    intent_version = Column(Integer, nullable=True)
    authority_id = Column(String, ForeignKey("delegated_authorities.id", ondelete="SET NULL"), nullable=True)
    authority_version = Column(Integer, nullable=True)

    # Alignment result (ALIGNED, PARTIAL, MISALIGNED, UNKNOWN, None if not evaluated)
    alignment_result = Column(String, nullable=True)
    alignment_signals = Column(JSON, nullable=True)

    metadata_ = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    run = relationship("AgentRun", back_populates="actions")
