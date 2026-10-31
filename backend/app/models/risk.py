import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class RiskAssessmentType(str, enum.Enum):
    TRANSACTION = "TRANSACTION"
    AGENT_ACTION = "AGENT_ACTION"
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAssessmentStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String, primary_key=True, default=lambda: f"ra_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_run_id = Column(String, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_action_id = Column(String, ForeignKey("agent_actions.id", ondelete="SET NULL"), nullable=True, index=True)

    intent_id = Column(String, ForeignKey("intents.id", ondelete="SET NULL"), nullable=True, index=True)
    intent_version = Column(Integer, nullable=True)

    authority_id = Column(String, ForeignKey("delegated_authorities.id", ondelete="SET NULL"), nullable=True, index=True)
    authority_version = Column(Integer, nullable=True)

    assessment_type = Column(Enum(RiskAssessmentType), nullable=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)

    decision_hint = Column(String, nullable=True)

    # JSONB for signals and exact features snapshot
    signals = Column(JSON, nullable=False, default=list)
    feature_snapshot = Column(JSON, nullable=False, default=dict)

    model_version = Column(String, nullable=False)
    scoring_version = Column(String, nullable=False)

    status = Column(Enum(RiskAssessmentStatus), nullable=False, default=RiskAssessmentStatus.COMPLETED)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    metadata_ = Column("metadata", JSON, nullable=True)

    # Relationships
    workspace = relationship("Workspace")
    agent = relationship("Agent")
    run = relationship("AgentRun")
    action = relationship("AgentAction")
    intent = relationship("Intent")
    authority = relationship("DelegatedAuthority")
