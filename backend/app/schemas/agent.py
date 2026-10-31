from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.agent import AgentType, AgentStatus
import enum

class AgentCapability(str, enum.Enum):
    SEARCH_PRODUCTS = "SEARCH_PRODUCTS"
    COMPARE_PRODUCTS = "COMPARE_PRODUCTS"
    CREATE_CART = "CREATE_CART"
    MANAGE_CART = "MANAGE_CART"
    ADD_CART_ITEM = "ADD_CART_ITEM"
    UPDATE_CART = "UPDATE_CART"
    CREATE_ORDER = "CREATE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    REQUEST_PAYMENT = "REQUEST_PAYMENT"
    EXECUTE_PAYMENT = "EXECUTE_PAYMENT"
    REQUEST_REFUND = "REQUEST_REFUND"
    PAY_ORDER = "PAY_ORDER"


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: AgentType
    
    capabilities: List[AgentCapability] = Field(default_factory=list)
    max_transaction_amount: Optional[int] = Field(None, ge=0)
    monthly_limit: Optional[int] = Field(None, ge=0)
    daily_limit: Optional[int] = Field(None, ge=0)
    approval_threshold: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    capabilities: Optional[List[AgentCapability]] = None
    max_transaction_amount: Optional[int] = Field(None, ge=0)
    monthly_limit: Optional[int] = Field(None, ge=0)
    daily_limit: Optional[int] = Field(None, ge=0)
    approval_threshold: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)

class AgentStatusUpdate(BaseModel):
    status: AgentStatus

class AgentResponse(AgentBase):
    id: str
    workspace_id: str
    status: AgentStatus
    
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class AgentCredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class AgentCredentialResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    client_id: str
    status: str
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class AgentCredentialSecretResponse(AgentCredentialResponse):
    client_secret: str

