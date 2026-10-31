from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.policy import PolicyStatus, PolicyType
import enum

class DecisionType(str, enum.Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"

class PolicyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: PolicyStatus = PolicyStatus.DRAFT
    priority: int = Field(default=50, ge=0, le=1000)
    policy_type: PolicyType
    
    conditions: Dict[str, Any] = Field(default_factory=dict)
    actions: Dict[str, Any] = Field(default_factory=dict)

class PolicyCreate(PolicyBase):
    pass

class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[PolicyStatus] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    policy_type: Optional[PolicyType] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None

class PolicyResponse(PolicyBase):
    id: str
    workspace_id: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PolicyEvaluationRequest(BaseModel):
    agent_id: str
    amount: float
    currency: str
    merchant_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)

class MatchedPolicyInfo(BaseModel):
    policy_id: str
    name: str

class PolicyEvaluationResponse(BaseModel):
    decision: DecisionType
    matched_policies: List[MatchedPolicyInfo] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
