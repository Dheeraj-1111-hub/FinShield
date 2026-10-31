from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.payment import PaymentStatus

class PaymentBase(BaseModel):
    payment_intent_id: str = Field(..., max_length=100)
    idempotency_key: str = Field(..., max_length=100)
    agent_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0, description="Amount")
    currency: Optional[str] = Field(default="INR", max_length=3)
    
    payment_method_type: Optional[str] = Field(None, max_length=50)
    merchant_reference: Optional[str] = Field(None, max_length=100)
    metadata_: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True

class PaymentResponse(PaymentBase):
    id: str
    workspace_id: str
    status: PaymentStatus
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Enrichment fields for the frontend
    agent_name: Optional[str] = None
    run_id: Optional[str] = None
    action_id: Optional[str] = None
    
    merchant_id: Optional[str] = None
    merchant_name: Optional[str] = None
    order_status: Optional[str] = None
    
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    risk_assessment_id: Optional[str] = None
    
    gate_decision: Optional[str] = None
    gate_decision_id: Optional[str] = None
    
    intent_id: Optional[str] = None
    authority_id: Optional[str] = None
    policy_decision: Optional[str] = None
    
    approval_request_id: Optional[str] = None
    approval_status: Optional[str] = None

    class Config:
        from_attributes = True

