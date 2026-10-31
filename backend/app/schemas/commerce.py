from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.commerce import MerchantStatus, ProductStatus, CartStatus, OrderStatus

# --- Merchant Schemas ---
class MerchantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: MerchantStatus = MerchantStatus.ACTIVE
    merchant_reference: Optional[str] = None
    risk_metadata: Optional[Dict[str, Any]] = None

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    id: str
    workspace_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    price: int = Field(..., ge=0)
    currency: str = "INR"
    inventory: int = Field(..., ge=0)
    sku: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    metadata_: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata", validation_alias=AliasChoices("metadata_", "metadata"))

class ProductCreate(ProductBase):
    merchant_id: str

class ProductResponse(ProductBase):
    id: str
    merchant_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# --- Cart Schemas ---
class CartItemBase(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0)

from pydantic import computed_field

class CartItemResponse(CartItemBase):
    id: str
    cart_id: str
    product: Optional[ProductResponse] = None
    
    @computed_field
    def unit_price(self) -> int:
        return self.product.price if self.product else 0
        
    @computed_field
    def total(self) -> int:
        return self.unit_price * self.quantity

    model_config = ConfigDict(from_attributes=True)

class CartCreate(BaseModel):
    agent_id: Optional[str] = None
    currency: str = "INR"

class CartResponse(BaseModel):
    id: str
    workspace_id: str
    agent_id: Optional[str] = None
    status: CartStatus
    currency: str
    created_at: datetime
    updated_at: datetime
    items: List[CartItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- Order Schemas ---
class OrderItemResponse(BaseModel):
    id: str
    order_id: str
    product_id: str
    product_name_snapshot: str
    merchant_name_snapshot: str
    quantity: int
    unit_price_at_order: int
    total: int
    product: Optional[ProductResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    cart_id: str
    agent_id: Optional[str] = None
    merchant_id: str
    metadata_: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata", validation_alias=AliasChoices("metadata_", "metadata"))

class OrderResponse(BaseModel):
    id: str
    workspace_id: str
    agent_id: Optional[str] = None
    cart_id: Optional[str] = None
    merchant_id: str
    payment_id: Optional[str] = None
    status: OrderStatus
    currency: str
    subtotal: int
    total: int
    metadata_: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata", validation_alias=AliasChoices("metadata_", "metadata"))
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
