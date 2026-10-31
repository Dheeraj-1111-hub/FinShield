from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, JSON, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.db.database import Base

class ScenarioCategory(str, enum.Enum):
    PROMPT_INJECTION = "PROMPT_INJECTION"
    TOOL_OUTPUT_POISONING = "TOOL_OUTPUT_POISONING"
    AUTHORITY_ESCALATION = "AUTHORITY_ESCALATION"
    INTENT_DRIFT = "INTENT_DRIFT"
    POLICY_BYPASS = "POLICY_BYPASS"
    GATE_BYPASS = "GATE_BYPASS"
    APPROVAL_REPLAY = "APPROVAL_REPLAY"
    CREDENTIAL_ABUSE = "CREDENTIAL_ABUSE"
    AGENT_BEHAVIOR = "AGENT_BEHAVIOR"
    PAYMENT_IDEMPOTENCY = "PAYMENT_IDEMPOTENCY"
    ORDER_INTEGRITY = "ORDER_INTEGRITY"
    WORKSPACE_ISOLATION = "WORKSPACE_ISOLATION"
    FAILURE_SAFETY = "FAILURE_SAFETY"
    AUDIT_INTEGRITY = "AUDIT_INTEGRITY"

class ScenarioSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TestStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

class StepResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    PENDING = "PENDING"

class FindingSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FindingStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

class SecurityScenario(Base):
    __tablename__ = "security_scenarios"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)
    category = Column(Enum(ScenarioCategory), nullable=False)
    severity = Column(Enum(ScenarioSeverity), nullable=False)
    target_component = Column(String, nullable=False)
    configuration = Column(JSON, nullable=False, default={})
    status = Column(String, nullable=False, default="ACTIVE")
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SecurityTestRun(Base):
    __tablename__ = "security_test_runs"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("security_scenarios.id"), nullable=False)
    status = Column(Enum(TestStatus), nullable=False, default=TestStatus.QUEUED)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    initiated_by = Column(String, nullable=False)
    target_agent_id = Column(String, nullable=True)
    target_run_id = Column(String, nullable=True)
    configuration = Column(JSON, nullable=False, default={})
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    scenario = relationship("SecurityScenario", lazy="selectin")
    steps = relationship("SecurityTestStep", back_populates="test_run", cascade="all, delete-orphan", order_by="SecurityTestStep.sequence_number", lazy="selectin")
    findings = relationship("SecurityFinding", back_populates="test_run", cascade="all, delete-orphan", lazy="selectin")

class SecurityTestStep(Base):
    __tablename__ = "security_test_steps"
    
    id = Column(String, primary_key=True)
    test_run_id = Column(String, ForeignKey("security_test_runs.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)
    input_data = Column(JSON, nullable=True)
    expected_behavior = Column(Text, nullable=False)
    observed_behavior = Column(Text, nullable=True)
    result = Column(Enum(StepResult), nullable=False, default=StepResult.PENDING)
    security_event_id = Column(String, nullable=True)
    audit_event_id = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    
    test_run = relationship("SecurityTestRun", back_populates="steps")

class SecurityFinding(Base):
    __tablename__ = "security_findings"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    test_run_id = Column(String, ForeignKey("security_test_runs.id"), nullable=False)
    severity = Column(Enum(FindingSeverity), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(ScenarioCategory), nullable=False)
    affected_component = Column(String, nullable=False)
    expected_behavior = Column(Text, nullable=False)
    observed_behavior = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)
    status = Column(Enum(FindingStatus), nullable=False, default=FindingStatus.OPEN)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    test_run = relationship("SecurityTestRun", back_populates="findings")
