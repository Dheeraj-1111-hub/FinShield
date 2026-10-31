import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, UniqueConstraint
from datetime import datetime, timezone
from app.db.database import Base

class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    REQUIRES_AUTHORIZATION = "REQUIRES_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: f"pay_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(String, nullable=True) # Future-proofing for Phase 6
    
    payment_intent_id = Column(String, nullable=False, index=True)
    idempotency_key = Column(String, nullable=False)
    
    amount = Column(Integer, nullable=False) # In minor units (e.g. paise)
    currency = Column(String, nullable=False, default="INR")
    
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.CREATED)
    payment_method_type = Column(String, nullable=True)
    merchant_reference = Column(String, nullable=True)
    
    metadata_ = Column("metadata", JSON, nullable=True)
    
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('workspace_id', 'idempotency_key', name='uq_workspace_idempotency_key'),
    )
