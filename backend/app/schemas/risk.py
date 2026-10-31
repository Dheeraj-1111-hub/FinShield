from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.models.risk import RiskAssessmentType, RiskLevel, RiskAssessmentStatus


class RiskSignal(BaseModel):
    signal_type: str = Field(..., description="e.g., INTENT_MISMATCH, AUTHORITY_PROXIMITY")
    score: float = Field(..., description="Score 0-100")
    severity: RiskLevel = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    weight: float = Field(..., description="0.0 to 1.0 multiplier")
    contribution: float = Field(..., description="score * weight")
    reason_code: str = Field(..., description="Machine readable reason")
    explanation: str = Field(..., description="Human readable explanation")


class TransactionContext(BaseModel):
    amount: Optional[int] = None
    currency: Optional[str] = None


class RiskEvaluateRequest(BaseModel):
    agent_id: str
    agent_action_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    intent_id: Optional[str] = None
    authority_id: Optional[str] = None
    merchant_id: Optional[str] = None
    product_category: Optional[str] = None
    transaction: Optional[TransactionContext] = None


class RiskAssessmentResponse(BaseModel):
    id: str
    workspace_id: str
    
    agent_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    intent_id: Optional[str] = None
    intent_version: Optional[int] = None
    authority_id: Optional[str] = None
    authority_version: Optional[int] = None
    
    assessment_type: RiskAssessmentType
    
    risk_score: float
    risk_level: RiskLevel
    
    decision_hint: Optional[str] = None
    
    signals: List[RiskSignal]
    feature_snapshot: Dict[str, Any]
    
    model_version: str
    scoring_version: str
    status: RiskAssessmentStatus
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskSummaryResponse(BaseModel):
    total_assessments: int
    low: int
    medium: int
    high: int
    critical: int
    average_score: float
    high_risk_rate: float
