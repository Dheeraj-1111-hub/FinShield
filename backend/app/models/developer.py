import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class ApiClientStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"

class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    EXHAUSTED = "EXHAUSTED"
    CANCELLED = "CANCELLED"

class ApiClient(Base):
    __tablename__ = "api_clients"

    id = Column(String, primary_key=True, default=lambda: f"cli_{uuid.uuid4().hex}")
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(ApiClientStatus), default=ApiClientStatus.ACTIVE, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    credentials = relationship("ApiCredential", back_populates="client")
    workspace = relationship("Workspace")

class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(String, primary_key=True, default=lambda: f"cred_{uuid.uuid4().hex}")
    api_client_id = Column(String, ForeignKey("api_clients.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    
    credential_prefix = Column(String, nullable=False, index=True)  # e.g. "fs_test_abc12"
    secret_hash = Column(String, nullable=False)

    scopes = Column(JSON, nullable=False, default=list) # List of strings e.g., ["payments:write"]

    status = Column(String, default="ACTIVE", nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    client = relationship("ApiClient", back_populates="credentials")

class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    
    id = Column(String, primary_key=True, default=lambda: f"wh_{uuid.uuid4().hex}")
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", nullable=False)
    
    secret_hash = Column(String, nullable=False)
    subscribed_events = Column(JSON, nullable=False, default=list)

    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    deliveries = relationship("WebhookDelivery", back_populates="endpoint")

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True, default=lambda: f"whd_{uuid.uuid4().hex}")
    webhook_endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_id = Column(String, nullable=False, index=True)
    
    attempt = Column(Integer, default=1, nullable=False)
    status = Column(Enum(WebhookDeliveryStatus), default=WebhookDeliveryStatus.PENDING, nullable=False)
    
    http_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    attempted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    
    error = Column(Text, nullable=True)

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")

class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"
    
    id = Column(String, primary_key=True, default=lambda: f"req_{uuid.uuid4().hex}")
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    api_client_id = Column(String, ForeignKey("api_clients.id"), nullable=True, index=True)
    credential_id = Column(String, ForeignKey("api_credentials.id"), nullable=True, index=True)
    
    method = Column(String, nullable=False)
    route = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    
    occurred_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    error_code = Column(String, nullable=True)
