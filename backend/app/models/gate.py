import enum
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, JSON, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class DecisionResult(str, enum.Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"

class ActionRiskClass(str, enum.Enum):
    READ = "READ"
    LOW_IMPACT = "LOW_IMPACT"
    COMMERCE = "COMMERCE"
    FINANCIAL = "FINANCIAL"
    SENSITIVE = "SENSITIVE"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    CANCELLED = "CANCELLED"

class GateDecision(Base):
    __tablename__ = "gate_decisions"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), index=True, nullable=False)
    
    agent_id = Column(String, ForeignKey("agents.id"), index=True, nullable=False)
    agent_run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False)
    agent_action_id = Column(String, ForeignKey("agent_actions.id"), nullable=False)
    
    intent_id = Column(String, ForeignKey("intents.id"), nullable=True)
    intent_version = Column(Integer, nullable=True)
    
    authority_id = Column(String, ForeignKey("delegated_authorities.id"), nullable=True)
    authority_version = Column(Integer, nullable=True)
    
    policy_evaluation_id = Column(String, nullable=True)
    risk_assessment_id = Column(String, ForeignKey("risk_assessments.id"), nullable=True)
    
    decision = Column(Enum(DecisionResult), nullable=False)
    reason_codes = Column(JSON, nullable=False, default=list)
    explanation = Column(String, nullable=True)
    
    required_approval = Column(Boolean, default=False)
    approval_id = Column(String, nullable=True) # Removed ForeignKey to break cycle for SQLite tests
    supersedes_decision_id = Column(String, ForeignKey("gate_decisions.id"), nullable=True)
    
    evaluation_snapshot = Column(JSON, nullable=False)
    
    valid_until = Column(DateTime(timezone=True), nullable=True)
    nonce = Column(String, nullable=True, unique=True, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workspace = relationship("Workspace")
    agent = relationship("Agent")
    agent_run = relationship("AgentRun")
    agent_action = relationship("AgentAction")
    intent = relationship("Intent")
    authority = relationship("DelegatedAuthority")
    risk_assessment = relationship("RiskAssessment")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), index=True, nullable=False)
    
    agent_id = Column(String, ForeignKey("agents.id"), index=True, nullable=False)
    agent_run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False)
    agent_action_id = Column(String, ForeignKey("agent_actions.id"), nullable=False)
    
    gate_decision_id = Column(String, ForeignKey("gate_decisions.id"), nullable=False)
    
    requested_by = Column(String, nullable=False) # e.g. "SYSTEM_GATE"
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    
    reason = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    amount = Column(Integer, nullable=True)
    currency = Column(String, nullable=True)
    transaction_data = Column(JSON, nullable=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    rejected_by = Column(String, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workspace = relationship("Workspace")
    agent = relationship("Agent")
    agent_run = relationship("AgentRun")
    agent_action = relationship("AgentAction")
    gate_decision = relationship("GateDecision", foreign_keys=[gate_decision_id])
    approver = relationship("User", foreign_keys=[approved_by])
    rejecter = relationship("User", foreign_keys=[rejected_by])
