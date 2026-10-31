import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class AuthorityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class DelegatedAuthority(Base):
    __tablename__ = "delegated_authorities"

    id = Column(String, primary_key=True, default=lambda: f"auth_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link to the intent that spawned this authority
    intent_id = Column(String, ForeignKey("intents.id", ondelete="SET NULL"), nullable=True, index=True)

    # The agent this authority is bound to
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(Enum(AuthorityStatus), default=AuthorityStatus.DRAFT, nullable=False)

    # Capabilities the agent is allowed to use under this authority
    allowed_capabilities = Column(JSON, default=list, nullable=False)

    # Capabilities explicitly prohibited (even if agent has them)
    prohibited_actions = Column(JSON, default=list, nullable=False)

    # Monetary limits
    monetary_limit = Column(Integer, nullable=True)          # Maximum per-transaction in currency units
    currency = Column(String(10), default="INR", nullable=False)
    approval_threshold = Column(Integer, nullable=True)      # Require approval above this amount

    # Time bounds (UTC)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # Versioning
    version = Column(Integer, default=1, nullable=False)

    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
    intent = relationship("Intent", back_populates="authorities")
    agent = relationship("Agent")
    creator = relationship("User")
    versions = relationship("AuthorityVersion", back_populates="authority",
                            cascade="all, delete-orphan", order_by="AuthorityVersion.version_number")


class AuthorityVersion(Base):
    """Immutable snapshot of a DelegatedAuthority at a specific version."""
    __tablename__ = "authority_versions"

    id = Column(String, primary_key=True, default=lambda: f"av_{uuid.uuid4().hex[:16]}")
    authority_id = Column(String, ForeignKey("delegated_authorities.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Full snapshot of the authority at this version
    snapshot = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    authority = relationship("DelegatedAuthority", back_populates="versions")
    creator = relationship("User")
