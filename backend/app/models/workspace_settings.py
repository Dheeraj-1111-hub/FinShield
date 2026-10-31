from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), unique=True, nullable=False)
    
    # Risk settings
    risk_threshold = Column(Integer, default=80, nullable=False)
    review_threshold = Column(Integer, default=70, nullable=False)
    high_value_transaction_threshold = Column(Float, default=100000.00, nullable=False)
    
    # AI/Security settings
    human_review_for_critical_actions = Column(Boolean, default=True, nullable=False)
    
    # Retention & Session settings
    audit_retention_days = Column(Integer, default=90, nullable=False)
    investigation_retention_days = Column(Integer, default=365, nullable=False)
    session_timeout_hours = Column(Integer, default=12, nullable=False)
    
    # Concurrency and tracking
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workspace = relationship("Workspace", backref="settings")
