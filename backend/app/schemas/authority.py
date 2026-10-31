from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.authority import AuthorityStatus


class AuthorityCreate(BaseModel):
    agent_id: str
    intent_id: Optional[str] = None
    allowed_capabilities: List[str] = Field(default_factory=list)
    prohibited_actions: List[str] = Field(default_factory=list)
    monetary_limit: Optional[int] = Field(None, ge=0)
    currency: str = Field(default="INR", max_length=10)
    approval_threshold: Optional[int] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class AuthorityUpdate(BaseModel):
    allowed_capabilities: Optional[List[str]] = None
    prohibited_actions: Optional[List[str]] = None
    monetary_limit: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    approval_threshold: Optional[int] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class AuthorityVersionResponse(BaseModel):
    id: str
    authority_id: str
    version_number: int
    snapshot: Dict[str, Any]
    created_at: datetime
    created_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AuthorityResponse(BaseModel):
    id: str
    workspace_id: str
    intent_id: Optional[str]
    agent_id: str
    status: AuthorityStatus
    allowed_capabilities: List[str]
    prohibited_actions: List[str]
    monetary_limit: Optional[int]
    currency: str
    approval_threshold: Optional[int]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    version: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorityEvaluationRequest(BaseModel):
    authority_id: str
    agent_id: str
    action: str                         # tool_name / capability
    amount: Optional[int] = None
    currency: Optional[str] = None


class AuthoritySimulationRequest(BaseModel):
    action: str                         # tool_name / capability
    amount: Optional[int] = None
    currency: Optional[str] = None


class AuthorityEvaluationResult(BaseModel):
    authorized: bool
    reasons: List[str]
    effective_monetary_limit: Optional[int] = None
    authority_version: Optional[int] = None
    requires_approval: bool = False
    alignment_result: Optional[str] = None
    alignment_signals: List[Dict[str, Any]] = Field(default_factory=list)
