import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class IntentType(str, enum.Enum):
    PURCHASE = "PURCHASE"
    SEARCH = "SEARCH"
    COMPARE = "COMPARE"
    BOOKING = "BOOKING"
    TRANSFER = "TRANSFER"
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"


class IntentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    CANCELLED = "CANCELLED"


class Intent(Base):
    __tablename__ = "intents"

    id = Column(String, primary_key=True, default=lambda: f"int_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Optional: pin this intent to a specific agent
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(Enum(IntentStatus), default=IntentStatus.DRAFT, nullable=False)
    intent_type = Column(Enum(IntentType), nullable=False)

    title = Column(String(200), nullable=False)
    natural_language_request = Column(Text, nullable=False)

    # Structured constraints validated by Pydantic at write time, stored as JSONB
    structured_constraints = Column(JSON, nullable=True, default=dict)

    # Versioning — auto-incremented on every update
    version = Column(Integer, default=1, nullable=False)

    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    metadata_ = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
    creator = relationship("User")
    agent = relationship("Agent")
    versions = relationship("IntentVersion", back_populates="intent",
                            cascade="all, delete-orphan", order_by="IntentVersion.version_number")
    authorities = relationship("DelegatedAuthority", back_populates="intent",
                               cascade="all, delete-orphan")


class IntentVersion(Base):
    """Immutable snapshot of an intent at a specific version number."""
    __tablename__ = "intent_versions"

    id = Column(String, primary_key=True, default=lambda: f"iv_{uuid.uuid4().hex[:16]}")
    intent_id = Column(String, ForeignKey("intents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Full snapshot of structured_constraints at this version
    structured_constraints = Column(JSON, nullable=False, default=dict)
    intent_type = Column(Enum(IntentType), nullable=False)
    title = Column(String(200), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    intent = relationship("Intent", back_populates="versions")
    creator = relationship("User")
