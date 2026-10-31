from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class AgentSummary(BaseModel):
    total: int
    active: int
    paused: int
    revoked: int
    model_config = ConfigDict(from_attributes=True)

class FinancialSummary(BaseModel):
    payment_volume: float
    payment_count: int
    orders_count: int
    currency: str = "INR"
    balances_by_currency: Dict[str, float] = {}
    model_config = ConfigDict(from_attributes=True)

class GateSummary(BaseModel):
    allow: int
    review: int
    block: int
    allow_rate: float
    review_rate: float
    block_rate: float
    model_config = ConfigDict(from_attributes=True)

class RiskSummary(BaseModel):
    low: int
    medium: int
    high: int
    critical: int
    model_config = ConfigDict(from_attributes=True)

class InvestigationSummary(BaseModel):
    open: int
    critical: int
    escalated: int
    model_config = ConfigDict(from_attributes=True)

class SecuritySummary(BaseModel):
    security_events: int
    open_findings: int
    audit_integrity_verified: bool
    audit_last_verified_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class OverviewHealth(BaseModel):
    api: str
    database: str
    redis: str
    model_config = ConfigDict(from_attributes=True)

class RecentCriticalRisk(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    action_type: str
    risk_level: str
    score: float
    reason: str
    occurred_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RecentApprovalRequest(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    action_type: str
    merchant: Optional[str] = None
    amount: Optional[float] = None
    reason: str
    requested_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RecentAuditEvent(BaseModel):
    id: str
    event_type: str
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    occurred_at: datetime
    details: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class OnboardingState(BaseModel):
    workspace_configured: bool
    agent_configured: bool
    intent_configured: bool
    authority_configured: bool
    policy_configured: bool
    first_protected_action: bool
    first_benchmark: bool
    model_config = ConfigDict(from_attributes=True)

class OverviewResponse(BaseModel):
    time_range: str
    agents: AgentSummary
    financial: FinancialSummary
    gate: GateSummary
    risk: RiskSummary
    investigations: InvestigationSummary
    security: SecuritySummary
    health: OverviewHealth
    onboarding: OnboardingState
    recent_critical_risks: List[RecentCriticalRisk]
    recent_approvals: List[RecentApprovalRequest]
    recent_audit_events: List[RecentAuditEvent]
    model_config = ConfigDict(from_attributes=True)
