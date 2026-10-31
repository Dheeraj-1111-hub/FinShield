import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any

from app.db.database import Base
import enum

class PolicyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"

class PolicyType(str, enum.Enum):
    TRANSACTION_LIMIT = "TRANSACTION_LIMIT"
    AGENT_AUTHORITY = "AGENT_AUTHORITY"
    CAPABILITY = "CAPABILITY"
    MERCHANT = "MERCHANT"
    APPROVAL = "APPROVAL"
    CURRENCY = "CURRENCY"
    VELOCITY = "VELOCITY"
    CUSTOM = "CUSTOM"

class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[PolicyStatus] = mapped_column(SQLEnum(PolicyStatus, name="policystatus_enum"), default=PolicyStatus.DRAFT, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    policy_type: Mapped[PolicyType] = mapped_column(SQLEnum(PolicyType, name="policytype_enum"), nullable=False)
    
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    actions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    workspace = relationship("Workspace")
    creator = relationship("User")
