from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# API Clients
class ApiClientBase(BaseModel):
    name: str
    description: Optional[str] = None

class ApiClientCreate(ApiClientBase):
    pass

class ApiClientResponse(ApiClientBase):
    id: str
    workspace_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# API Credentials
class ApiCredentialCreate(BaseModel):
    api_client_id: str
    name: str
    scopes: List[str]

class ApiCredentialResponse(BaseModel):
    id: str
    api_client_id: str
    workspace_id: str
    name: str
    credential_prefix: str
    scopes: List[str]
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApiCredentialSecretResponse(ApiCredentialResponse):
    secret: str  # ONLY RETURNED ONCE!

# Webhooks
class WebhookEndpointBase(BaseModel):
    url: str
    description: Optional[str] = None
    subscribed_events: List[str]

class WebhookEndpointCreate(WebhookEndpointBase):
    pass

class WebhookEndpointResponse(WebhookEndpointBase):
    id: str
    workspace_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WebhookDeliveryResponse(BaseModel):
    id: str
    webhook_endpoint_id: str
    event_id: str
    attempt: int
    status: str
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    attempted_at: datetime
    next_retry_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True

class ApiRequestLogResponse(BaseModel):
    id: str
    api_client_id: Optional[str] = None
    method: str
    route: str
    status_code: int
    latency_ms: int
    occurred_at: datetime
    correlation_id: Optional[str] = None

    class Config:
        from_attributes = True
