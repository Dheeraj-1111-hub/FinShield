from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.gate import DecisionResult, ActionRiskClass, ApprovalStatus

class GateDecisionBase(BaseModel):
    workspace_id: str
    agent_id: str
    agent_run_id: str
    agent_action_id: str
    
    intent_id: Optional[str] = None
    intent_version: Optional[int] = None
    authority_id: Optional[str] = None
    authority_version: Optional[int] = None
    
    policy_evaluation_id: Optional[str] = None
    risk_assessment_id: Optional[str] = None
    
    decision: DecisionResult
    reason_codes: List[str]
    explanation: Optional[str] = None
    
    required_approval: bool = False
    approval_id: Optional[str] = None
    supersedes_decision_id: Optional[str] = None
    
    evaluation_snapshot: Dict[str, Any]
    valid_until: Optional[datetime] = None

class GateDecisionCreate(GateDecisionBase):
    pass

class GateDecisionResponse(GateDecisionBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ApprovalRequestBase(BaseModel):
    workspace_id: str
    agent_id: str
    agent_run_id: str
    agent_action_id: str
    gate_decision_id: str
    requested_by: str
    status: ApprovalStatus
    reason: Optional[str] = None
    risk_score: Optional[float] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    transaction_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class ApprovalRequestCreate(ApprovalRequestBase):
    pass

class ApprovalRequestResponse(ApprovalRequestBase):
    id: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class GateEvaluationRequest(BaseModel):
    agent_id: str
    agent_run_id: str
    agent_action_id: str
    action_type: str
    context: Dict[str, Any]


class GateDecisionDetailResponse(BaseModel):
    id: str
    workspace_id: str
    agent_id: str
    agent_run_id: str
    agent_action_id: str
    decision: str
    reason_codes: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    required_approval: bool = False
    approval_id: Optional[str] = None
    supersedes_decision_id: Optional[str] = None
    valid_until: Optional[datetime] = None
    nonce: Optional[str] = None
    consumed_at: Optional[datetime] = None
    evaluation_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    amount: Optional[float] = None
    currency: Optional[str] = None
    execution_status: Optional[str] = None
    approval_lifecycle_status: Optional[str] = None

    agent: Optional[Dict[str, Any]] = None
    agent_run: Optional[Dict[str, Any]] = None
    agent_action: Optional[Dict[str, Any]] = None
    approval: Optional[Dict[str, Any]] = None
    intent: Optional[Dict[str, Any]] = None
    authority: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    policy_evaluation: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    payment: Optional[Dict[str, Any]] = None

    evidence_status: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class GateDecisionListItem(BaseModel):
    id: str
    workspace_id: str
    agent_id: str
    agent_name: Optional[str] = None
    agent_run_id: str
    agent_action_id: str
    tool_name: Optional[str] = None
    decision: str
    reason_codes: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    required_approval: bool = False
    approval_id: Optional[str] = None
    approval_status: Optional[str] = None
    approval_lifecycle_status: Optional[str] = None
    execution_status: Optional[str] = None
    consumed_at: Optional[datetime] = None
    supersedes_decision_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

