from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.security_lab import (
    ScenarioCategory,
    ScenarioSeverity,
    TestStatus,
    StepResult,
    FindingSeverity,
    FindingStatus
)

class SecurityScenarioBase(BaseModel):
    name: str
    description: str
    category: ScenarioCategory
    severity: ScenarioSeverity
    target_component: str
    configuration: Dict[str, Any]
    status: str

class SecurityScenarioCreate(SecurityScenarioBase):
    slug: str

class SecurityScenarioResponse(SecurityScenarioBase):
    id: str
    workspace_id: str
    slug: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SecurityTestStepResponse(BaseModel):
    id: str
    test_run_id: str
    sequence_number: int
    step_type: str
    input_data: Optional[Dict[str, Any]] = None
    expected_behavior: str
    observed_behavior: Optional[str] = None
    result: StepResult
    security_event_id: Optional[str] = None
    audit_event_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata_: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SecurityFindingBase(BaseModel):
    severity: FindingSeverity
    title: str
    description: str
    category: ScenarioCategory
    affected_component: str
    expected_behavior: str
    observed_behavior: str
    evidence: Optional[Dict[str, Any]] = None
    status: FindingStatus

class SecurityFindingResponse(SecurityFindingBase):
    id: str
    workspace_id: str
    test_run_id: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SecurityTestRunBase(BaseModel):
    status: TestStatus
    target_agent_id: Optional[str] = None
    target_run_id: Optional[str] = None
    configuration: Dict[str, Any]
    summary: Optional[str] = None

class SecurityTestRunCreate(BaseModel):
    scenario_id: str
    target_agent_id: Optional[str] = None
    target_run_id: Optional[str] = None
    configuration: Dict[str, Any] = {}

class SecurityTestRunResponse(SecurityTestRunBase):
    id: str
    workspace_id: str
    scenario_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    initiated_by: str
    created_at: datetime
    
    scenario: Optional[SecurityScenarioResponse] = None
    steps: Optional[List[SecurityTestStepResponse]] = None
    findings: Optional[List[SecurityFindingResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class ScenarioBenchmarkEvaluation(BaseModel):
    scenario_id: str
    scenario_slug: str
    scenario_name: str
    category: ScenarioCategory
    severity: ScenarioSeverity
    target_component: str
    description: str
    expected_security_invariant: str
    
    total_runs: int = 0
    verified_runs: int = 0
    passed_defenses: int = 0
    failed_defenses: int = 0
    inconclusive_runs: int = 0
    
    latest_run_id: Optional[str] = None
    latest_status: Optional[TestStatus] = None
    latest_execution_time: Optional[datetime] = None
    observed_result: Optional[str] = None
    attack_outcome: str  # "ATTACK_BLOCKED", "ATTACK_SUCCEEDED", "INCONCLUSIVE", "UNTESTED", "EVALUATING"
    enforcement_boundary: Optional[str] = None
    evidence_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class SecurityBenchmarkSummary(BaseModel):
    total_runs: int
    verified_runs: int
    passed_defenses: int
    failed_defenses: int
    inconclusive_runs: int
    active_runs: int
    defense_rate: Optional[float] = None
    defense_rate_percentage: Optional[int] = None
    scenarios_evaluated: int
    total_scenarios: int
    generated_at: datetime
    scenario_evaluations: List[ScenarioBenchmarkEvaluation]

    model_config = ConfigDict(from_attributes=True)
