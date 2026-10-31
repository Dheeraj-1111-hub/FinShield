import enum
import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Enum, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

class MerchantStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    ARCHIVED = "ARCHIVED"

class CartStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CHECKED_OUT = "CHECKED_OUT"
    ABANDONED = "ABANDONED"

class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND_PENDING = "REFUND_PENDING"

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=lambda: f"mer_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(MerchantStatus), default=MerchantStatus.ACTIVE, nullable=False)
    merchant_reference = Column(String, nullable=True)
    risk_metadata = Column(JSON, nullable=True)
    created_by = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    products = relationship("Product", back_populates="merchant")

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: f"prd_{uuid.uuid4().hex[:16]}")
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    price = Column(Integer, nullable=False) # Minor units
    currency = Column(String, nullable=False, default="INR")
    inventory = Column(Integer, default=0, nullable=False)
    sku = Column(String, nullable=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    merchant = relationship("Merchant", back_populates="products")

class Cart(Base):
    __tablename__ = "carts"

    id = Column(String, primary_key=True, default=lambda: f"crt_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(Enum(CartStatus), default=CartStatus.ACTIVE, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(String, primary_key=True, default=lambda: f"cti_{uuid.uuid4().hex[:16]}")
    cart_id = Column(String, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: f"ord_{uuid.uuid4().hex[:16]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    cart_id = Column(String, ForeignKey("carts.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False)
    payment_id = Column(String, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    subtotal = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", foreign_keys=[payment_id])

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=lambda: f"ori_{uuid.uuid4().hex[:16]}")
    order_id = Column(String, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name_snapshot = Column(String, nullable=False)
    merchant_name_snapshot = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_at_order = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
