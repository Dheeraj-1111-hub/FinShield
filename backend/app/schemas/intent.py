from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.intent import IntentType, IntentStatus


# ─── Constraint sub-schemas ───────────────────────────────────────────────────

class AmountConstraint(BaseModel):
    minimum: Optional[int] = Field(None, ge=0, description="Minimum amount in currency units")
    maximum: Optional[int] = Field(None, ge=0, description="Maximum amount in currency units")
    currency: str = Field(default="INR", max_length=10)

    @model_validator(mode="after")
    def validate_min_max(self) -> "AmountConstraint":
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("minimum cannot exceed maximum")
        return self


class ProductConstraint(BaseModel):
    category: Optional[str] = Field(None, max_length=100)
    preferred_brands: List[str] = Field(default_factory=list)
    blocked_brands: List[str] = Field(default_factory=list)
    model: Optional[str] = Field(None, max_length=200)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class MerchantConstraint(BaseModel):
    allowed_merchants: List[str] = Field(default_factory=list)
    blocked_merchants: List[str] = Field(default_factory=list)
    merchant_type: Optional[str] = Field(None, max_length=100)


class QuantityConstraint(BaseModel):
    minimum_quantity: Optional[int] = Field(None, ge=1)
    maximum_quantity: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def validate_qty(self) -> "QuantityConstraint":
        if self.minimum_quantity is not None and self.maximum_quantity is not None:
            if self.minimum_quantity > self.maximum_quantity:
                raise ValueError("minimum_quantity cannot exceed maximum_quantity")
        return self


class ApprovalConstraint(BaseModel):
    approval_required_above: Optional[int] = Field(None, ge=0,
        description="Require human approval for actions above this amount")
    approval_required: bool = Field(default=False)


class IntentConstraints(BaseModel):
    """Strict validated constraints. Unknown fields are rejected."""
    model_config = ConfigDict(extra="forbid")

    amount: Optional[AmountConstraint] = None
    product: Optional[ProductConstraint] = None
    merchant: Optional[MerchantConstraint] = None
    quantity: Optional[QuantityConstraint] = None
    approval: Optional[ApprovalConstraint] = None
    allowed_actions: Optional[List[str]] = Field(default_factory=list,
        description="List of tool names explicitly allowed by this intent")
    prohibited_actions: Optional[List[str]] = Field(default_factory=list,
        description="List of tool names explicitly forbidden by this intent")
    search_only: Optional[bool] = Field(default=None,
        description="Flag indicating this intent is strictly read/search-only")
    read_only: Optional[bool] = Field(default=None,
        description="Flag indicating this intent is read-only")


# ─── Intent CRUD schemas ──────────────────────────────────────────────────────

class IntentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    intent_type: IntentType
    natural_language_request: str = Field(..., min_length=1, max_length=5000)
    structured_constraints: Optional[IntentConstraints] = None
    agent_id: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class IntentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    intent_type: Optional[IntentType] = None
    natural_language_request: Optional[str] = Field(None, min_length=1, max_length=5000)
    structured_constraints: Optional[IntentConstraints] = None
    agent_id: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class IntentVersionResponse(BaseModel):
    id: str
    intent_id: str
    version_number: int
    structured_constraints: Dict[str, Any]
    intent_type: IntentType
    title: str
    created_at: datetime
    created_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class IntentResponse(BaseModel):
    id: str
    workspace_id: str
    created_by: Optional[str]
    agent_id: Optional[str]
    status: IntentStatus
    intent_type: IntentType
    title: str
    natural_language_request: str
    structured_constraints: Optional[Dict[str, Any]]
    version: int
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, obj) -> "IntentResponse":
        return cls(
            id=obj.id,
            workspace_id=obj.workspace_id,
            created_by=obj.created_by,
            agent_id=obj.agent_id,
            status=obj.status,
            intent_type=obj.intent_type,
            title=obj.title,
            natural_language_request=obj.natural_language_request,
            structured_constraints=obj.structured_constraints,
            version=obj.version,
            valid_from=obj.valid_from,
            valid_until=obj.valid_until,
            metadata=obj.metadata_,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


# ─── Extraction schemas ───────────────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ExtractionSignal(BaseModel):
    field: str
    value: Any
    confidence: str  # HIGH, MEDIUM, LOW


class ExtractionProposal(BaseModel):
    """Result of intent extraction. This is a PROPOSAL only — not saved automatically."""
    proposed_type: IntentType
    proposed_title: str
    proposed_constraints: IntentConstraints
    signals: List[ExtractionSignal]
    explanation: str
    # Flags any unsafe inferences that the system refused to make
    refused_inferences: List[str] = Field(default_factory=list)


# ─── Evaluation schemas ───────────────────────────────────────────────────────

class AlignmentSignal(BaseModel):
    type: str        # AMOUNT, CATEGORY, MERCHANT, ACTION
    status: str      # ALIGNED, MISALIGNED, UNKNOWN
    reason: Optional[str] = None


class AlignmentResult(BaseModel):
    alignment: str   # ALIGNED, PARTIAL, MISALIGNED, UNKNOWN
    signals: List[AlignmentSignal]


class IntentEvaluationRequest(BaseModel):
    intent_id: str
    action: str              # tool_name
    amount: Optional[int] = None
    currency: Optional[str] = None
    product_category: Optional[str] = None
    merchant_id: Optional[str] = None
