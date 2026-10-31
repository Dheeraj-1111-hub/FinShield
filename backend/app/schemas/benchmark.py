from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Benchmark Suite ---
class BenchmarkSuiteBase(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = "1.0"
    status: Optional[str] = "DRAFT"

class BenchmarkSuiteCreate(BenchmarkSuiteBase):
    pass

class BenchmarkSuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None

class BenchmarkSuite(BenchmarkSuiteBase):
    id: str
    workspace_id: str
    slug: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Benchmark Case ---
class BenchmarkCaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    difficulty: Optional[str] = None

    initial_state: Optional[Dict[str, Any]] = None
    agent_configuration: Optional[Dict[str, Any]] = None
    intent_configuration: Optional[Dict[str, Any]] = None
    authority_configuration: Optional[Dict[str, Any]] = None
    attack_configuration: Optional[Dict[str, Any]] = None

    expected_outcome: Optional[str] = None
    expected_decision: str
    evaluation_rules: Optional[Dict[str, Any]] = None

class BenchmarkCaseCreate(BenchmarkCaseBase):
    suite_id: str

class BenchmarkCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None
    agent_configuration: Optional[Dict[str, Any]] = None
    intent_configuration: Optional[Dict[str, Any]] = None
    authority_configuration: Optional[Dict[str, Any]] = None
    attack_configuration: Optional[Dict[str, Any]] = None
    expected_outcome: Optional[str] = None
    expected_decision: Optional[str] = None
    evaluation_rules: Optional[Dict[str, Any]] = None

class BenchmarkCase(BenchmarkCaseBase):
    id: str
    suite_id: str
    workspace_id: str
    version: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Benchmark Experiment ---
class BenchmarkExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    suite_id: str
    suite_version: str

    baseline_configuration: Optional[Dict[str, Any]] = None
    protected_configuration: Optional[Dict[str, Any]] = None
    
    repetitions: int = 1
    random_seed: Optional[int] = None

class BenchmarkExperimentCreate(BenchmarkExperimentBase):
    pass

class BenchmarkExperiment(BenchmarkExperimentBase):
    id: str
    workspace_id: str
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Benchmark Case Result ---
class BenchmarkCaseResultBase(BaseModel):
    is_baseline: bool
    repetition_index: int
    status: str

    expected_decision: Optional[str] = None
    observed_decision: Optional[str] = None
    expected_outcome: Optional[str] = None
    observed_outcome: Optional[str] = None

    execution_success: bool = False
    financial_execution_occurred: bool = False
    
    payment_id: Optional[str] = None
    order_id: Optional[str] = None

    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    gate_decision: Optional[str] = None

    latency_ms: Optional[int] = None

    error: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

class BenchmarkCaseResult(BenchmarkCaseResultBase):
    id: str
    benchmark_run_id: str
    case_id: str
    workspace_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Benchmark Run ---
class BenchmarkRunBase(BaseModel):
    experiment_id: str
    environment: str = "SANDBOX"
    seed: Optional[int] = None
    configuration_snapshot: Dict[str, Any]

class BenchmarkRunCreate(BenchmarkRunBase):
    pass

class BenchmarkRun(BenchmarkRunBase):
    id: str
    workspace_id: str
    status: str
    total_cases: int
    completed_cases: int
    failed_cases: int
    summary: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Benchmark Metrics ---
class BenchmarkMetricBase(BaseModel):
    metric_name: str
    metric_value: float
    is_baseline: bool = False
    metadata_snapshot: Optional[Dict[str, Any]] = None

class BenchmarkMetric(BenchmarkMetricBase):
    id: str
    benchmark_run_id: str
    workspace_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Compound Responses ---
class BenchmarkRunDetail(BenchmarkRun):
    results: List[BenchmarkCaseResult] = []
    metrics: List[BenchmarkMetric] = []

    class Config:
        from_attributes = True

class BenchmarkExperimentDetail(BenchmarkExperiment):
    runs: List[BenchmarkRun] = []
    
    class Config:
        from_attributes = True

class BenchmarkSuiteDetail(BenchmarkSuite):
    cases: List[BenchmarkCase] = []

    class Config:
        from_attributes = True
