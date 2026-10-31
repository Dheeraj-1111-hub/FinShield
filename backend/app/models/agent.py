import enum
from sqlalchemy import Column, String, Text, Enum, JSON, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

class AgentType(str, enum.Enum):
    SHOPPING = "SHOPPING"
    PAYMENT = "PAYMENT"
    FINANCE = "FINANCE"
    OPERATIONS = "OPERATIONS"
    CUSTOM = "CUSTOM"

class AgentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REVOKED = "REVOKED"
    ARCHIVED = "ARCHIVED"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False)
    
    # Financial & Capability Configurations
    capabilities = Column(JSON, default=list)  # e.g., ["SEARCH_PRODUCTS", "CREATE_CART"]
    max_transaction_amount = Column(Integer, nullable=True)
    monthly_limit = Column(Integer, nullable=True)
    daily_limit = Column(Integer, nullable=True)
    approval_threshold = Column(Integer, nullable=True)
    currency = Column(String, default="INR", nullable=True)
    
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", backref="agents")
    creator = relationship("User")
    credentials = relationship("AgentCredential", back_populates="agent", cascade="all, delete-orphan")

class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    client_id = Column(String, unique=True, index=True, nullable=False)
    client_secret_hash = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="credentials")
