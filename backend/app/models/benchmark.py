from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class BenchmarkSuite(Base):
    __tablename__ = "benchmark_suites"

    id = Column(String, primary_key=True, default=lambda: f"bs_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String, nullable=False, index=True)
    
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    
    version = Column(String, nullable=False, default="1.0")
    status = Column(String, nullable=False, default="DRAFT") # DRAFT, ACTIVE, ARCHIVED
    
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cases = relationship("BenchmarkCase", back_populates="suite", cascade="all, delete-orphan")


class BenchmarkCase(Base):
    __tablename__ = "benchmark_cases"

    id = Column(String, primary_key=True, default=lambda: f"bc_{uuid.uuid4().hex[:12]}")
    suite_id = Column(String, ForeignKey("benchmark_suites.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False) # LEGITIMATE_COMMERCE, PROMPT_INJECTION, etc.
    difficulty = Column(String, nullable=True)

    # Configuration for the experiment
    initial_state = Column(JSON, nullable=True)
    agent_configuration = Column(JSON, nullable=True)
    intent_configuration = Column(JSON, nullable=True)
    authority_configuration = Column(JSON, nullable=True)
    attack_configuration = Column(JSON, nullable=True)

    # Expected outcomes for metric evaluation
    expected_outcome = Column(String, nullable=True)
    expected_decision = Column(String, nullable=False) # ALLOW, BLOCK, REVIEW
    evaluation_rules = Column(JSON, nullable=True)
    
    version = Column(String, nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    suite = relationship("BenchmarkSuite", back_populates="cases")


class BenchmarkExperiment(Base):
    __tablename__ = "benchmark_experiments"

    id = Column(String, primary_key=True, default=lambda: f"be_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String, nullable=False, index=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    suite_id = Column(String, ForeignKey("benchmark_suites.id"), nullable=False)
    suite_version = Column(String, nullable=False)

    baseline_configuration = Column(JSON, nullable=True)
    protected_configuration = Column(JSON, nullable=True)
    
    repetitions = Column(Integer, nullable=False, default=1)
    random_seed = Column(Integer, nullable=True)
    
    status = Column(String, nullable=False, default="DRAFT")

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    runs = relationship("BenchmarkRun", back_populates="experiment", cascade="all, delete-orphan")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(String, primary_key=True, default=lambda: f"run_{uuid.uuid4().hex[:12]}")
    experiment_id = Column(String, ForeignKey("benchmark_experiments.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)

    status = Column(String, nullable=False, default="QUEUED") # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    
    configuration_snapshot = Column(JSON, nullable=False)
    environment = Column(String, nullable=False, default="SANDBOX")
    seed = Column(Integer, nullable=True)

    total_cases = Column(Integer, nullable=False, default=0)
    completed_cases = Column(Integer, nullable=False, default=0)
    failed_cases = Column(Integer, nullable=False, default=0)
    
    summary = Column(String, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("BenchmarkExperiment", back_populates="runs")
    results = relationship("BenchmarkCaseResult", back_populates="run", cascade="all, delete-orphan")


class BenchmarkCaseResult(Base):
    __tablename__ = "benchmark_case_results"

    id = Column(String, primary_key=True, default=lambda: f"bcr_{uuid.uuid4().hex[:12]}")
    benchmark_run_id = Column(String, ForeignKey("benchmark_runs.id"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("benchmark_cases.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)

    is_baseline = Column(Boolean, nullable=False, default=False)
    repetition_index = Column(Integer, nullable=False, default=1)

    status = Column(String, nullable=False) # PASS, FAIL, ERROR

    expected_decision = Column(String, nullable=True)
    observed_decision = Column(String, nullable=True)
    
    expected_outcome = Column(String, nullable=True)
    observed_outcome = Column(String, nullable=True)

    execution_success = Column(Boolean, nullable=False, default=False)
    financial_execution_occurred = Column(Boolean, nullable=False, default=False)
    
    agent_completed = Column(Boolean, nullable=False, default=False)
    financial_action_attempted = Column(Boolean, nullable=False, default=False)
    gate_evaluated = Column(Boolean, nullable=False, default=False)
    execution_status = Column(String, nullable=True) # NOT_REACHED, EXECUTED, REVIEW_REQUIRED, BLOCKED, ERROR, RATE_LIMITED
    unauthorized_execution = Column(Boolean, nullable=False, default=False)
    
    # New containment metric fields
    authorized_transaction_executed = Column(Boolean, nullable=False, default=False)
    unauthorized_transaction_executed = Column(Boolean, nullable=False, default=False)
    attack_contained = Column(Boolean, nullable=False, default=False)
    
    provider_error = Column(Boolean, nullable=False, default=False)
    provider_rate_limited = Column(Boolean, nullable=False, default=False)
    
    payment_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)

    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String, nullable=True)
    gate_decision = Column(String, nullable=True)

    latency_ms = Column(Integer, nullable=True)

    error = Column(String, nullable=True)
    evidence = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("BenchmarkRun", back_populates="results")
    case = relationship("BenchmarkCase")

class BenchmarkMetric(Base):
    __tablename__ = "benchmark_metrics"
    
    id = Column(String, primary_key=True, default=lambda: f"bm_{uuid.uuid4().hex[:12]}")
    benchmark_run_id = Column(String, ForeignKey("benchmark_runs.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    is_baseline = Column(Boolean, nullable=False, default=False)
    metadata_snapshot = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
