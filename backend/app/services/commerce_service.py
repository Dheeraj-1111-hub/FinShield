from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.models.commerce import (
    Merchant, MerchantStatus, Product, ProductStatus,
    Cart, CartStatus, CartItem, Order, OrderStatus, OrderItem
)
from app.schemas.commerce import (
    MerchantCreate, ProductCreate, CartCreate, CartItemCreate, OrderCreate
)
from app.models.audit import EventCategory, EventSeverity, ActorType, EventTypes
from app.services.audit_service import AuditService

from app.schemas.execution_context import ExecutionContext

class CommerceService:
    @staticmethod
    async def _log_activity(
        db: AsyncSession,
        workspace_id: str,
        action: str,
        order_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        actor_type: Optional[ActorType] = None,
        details: dict = None,
        severity: EventSeverity = EventSeverity.INFO
    ):
        audit_service = AuditService(db)
        if not actor_type:
            if agent_id:
                actor_type = ActorType.AGENT
            elif actor_id:
                actor_type = ActorType.USER
            else:
                actor_type = ActorType.SYSTEM
                
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type=action,
            event_category=EventCategory.ORDER,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id or agent_id,
            agent_id=agent_id,
            entity_type="ORDER",
            entity_id=order_id,
            payload=details or {}
        )

    @staticmethod
    async def _verify_gate_token(db: AsyncSession, workspace_id: str, ctx: ExecutionContext, action_type: str, amount: Optional[float] = None, currency: Optional[str] = None, target_identity: Optional[str] = None, consume_nonce: bool = True):
        if not ctx.is_agent:
            return
            
        if not ctx.is_agent_runtime:
            raise HTTPException(status_code=403, detail="Agents must execute via AgentRuntimeService.")
            
        if not ctx.signed_decision_token:
            raise HTTPException(status_code=403, detail="Protected operation requires signed decision token.")
            
        from app.core.gate_crypto import GateCrypto
        from app.models.gate import GateDecision
        from sqlalchemy import update
        
        try:
            decision = GateCrypto.verify_token(ctx.signed_decision_token)
        except Exception as e:
            raise HTTPException(status_code=403, detail=f"Invalid signed decision token: {str(e)}")
            
        if decision.decision != "ALLOW":
            raise HTTPException(status_code=403, detail="Protected operation requires Action Gate ALLOW decision.")
            
        if decision.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Token workspace mismatch")
            
        if decision.agent_id != ctx.agent_id:
            raise HTTPException(status_code=403, detail="Token agent mismatch")
            
        if decision.action_type != action_type:
            raise HTTPException(status_code=403, detail="Token action mismatch")
            
        if amount is not None and decision.amount != amount:
            raise HTTPException(status_code=403, detail="Token amount mismatch")
            
        if currency is not None and decision.currency != currency:
            raise HTTPException(status_code=403, detail="Token currency mismatch")
            
        if target_identity is not None and decision.target_identity != target_identity:
            raise HTTPException(status_code=403, detail="Token target mismatch")
            
        if consume_nonce:
            # Consume nonce atomically
            stmt = update(GateDecision).where(
                GateDecision.nonce == decision.nonce, 
                GateDecision.consumed_at.is_(None)
            ).values(consumed_at=datetime.now(timezone.utc)).execution_options(synchronize_session="fetch")
            
            result = await db.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=403, detail="Token nonce already consumed or invalid")

        return decision


    # --- Merchant ---
    @staticmethod
    async def create_merchant(db: AsyncSession, workspace_id: str, data: MerchantCreate, ctx: ExecutionContext) -> Merchant:
        if ctx.is_agent and not ctx.is_agent_runtime:
            raise HTTPException(status_code=403, detail="Agents must execute via AgentRuntimeService.")
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        merchant = Merchant(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            status=data.status,
            merchant_reference=data.merchant_reference,
            risk_metadata=data.risk_metadata,
            created_by=actor_id
        )
        db.add(merchant)
        await db.commit()
        await db.refresh(merchant)
        
        await CommerceService._log_activity(db, workspace_id, "MERCHANT_CREATED", actor_id=actor_id, details={"merchant_id": merchant.id})
        await db.commit()
        return merchant

    @staticmethod
    async def list_merchants(db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100) -> List[Merchant]:
        stmt = select(Merchant).where(Merchant.workspace_id == workspace_id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- Product ---
    @staticmethod
    async def create_product(db: AsyncSession, workspace_id: str, data: ProductCreate, ctx: ExecutionContext) -> Product:
        if ctx.is_agent and not ctx.is_agent_runtime:
            raise HTTPException(status_code=403, detail="Agents must execute via AgentRuntimeService.")
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        stmt = select(Merchant).where(Merchant.id == data.merchant_id, Merchant.workspace_id == workspace_id)
        result = await db.execute(stmt)
        merchant = result.scalar_one_or_none()
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
            
        product = Product(
            merchant_id=data.merchant_id,
            name=data.name,
            description=data.description,
            category=data.category,
            price=data.price,
            currency=data.currency,
            inventory=data.inventory,
            sku=data.sku,
            status=data.status,
            metadata_=data.metadata_
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        
        await CommerceService._log_activity(db, workspace_id, "PRODUCT_CREATED", actor_id=actor_id, details={"product_id": product.id})
        await db.commit()
        return product

    @staticmethod
    def _normalize_category_filter(category: Optional[str]) -> List[str]:
        from app.services.taxonomy import get_taxonomy_synonyms
        return get_taxonomy_synonyms(category)

    @staticmethod
    async def list_products(db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100, merchant_id: Optional[str] = None, category: Optional[str] = None) -> List[Product]:
        from sqlalchemy import or_
        stmt = select(Product).join(Merchant).where(Merchant.workspace_id == workspace_id)
        if merchant_id:
            stmt = stmt.where(Product.merchant_id == merchant_id)
        if category:
            cat_list = CommerceService._normalize_category_filter(category)
            if cat_list:
                cat_conditions = [Product.category.ilike(f"%{c}%") for c in cat_list]
                stmt = stmt.where(or_(*cat_conditions))
            
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_product(db: AsyncSession, workspace_id: str, product_id: str) -> Product:
        stmt = select(Product).join(Merchant).where(Product.id == product_id, Merchant.workspace_id == workspace_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    # --- Cart ---
    @staticmethod
    async def create_cart(db: AsyncSession, workspace_id: str, data: CartCreate, ctx: ExecutionContext) -> Cart:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "create_cart")
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        cart_agent_id = ctx.agent_id if ctx.is_agent else None
        
        cart = Cart(
            workspace_id=workspace_id,
            agent_id=cart_agent_id,
            currency=data.currency
        )
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        await CommerceService._log_activity(db, workspace_id, "CART_CREATED", actor_id=actor_id, details={"cart_id": cart.id})
        await db.commit()
        return await CommerceService.get_cart(db, workspace_id, cart.id)

    @staticmethod
    async def get_cart(db: AsyncSession, workspace_id: str, cart_id: str) -> Cart:
        stmt = (
            select(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.product))
            .where(Cart.id == cart_id, Cart.workspace_id == workspace_id)
            .execution_options(populate_existing=True)
        )
        result = await db.execute(stmt)
        cart = result.unique().scalar_one_or_none()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        return cart

    @staticmethod
    async def add_cart_item(db: AsyncSession, workspace_id: str, cart_id: str, data: CartItemCreate, ctx: ExecutionContext) -> CartItem:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "add_to_cart")
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        cart = await CommerceService.get_cart(db, workspace_id, cart_id)
        product = await CommerceService.get_product(db, workspace_id, data.product_id)
        
        if product.status != ProductStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cannot add inactive product to cart")
        if cart.currency and product.currency and cart.currency != product.currency:
            raise HTTPException(status_code=400, detail=f"Currency mismatch: product is in {product.currency} but cart is in {cart.currency}")
        if product.inventory < data.quantity:
            raise HTTPException(status_code=400, detail="Not enough inventory")
        
        stmt = select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == data.product_id)
        result = await db.execute(stmt)
        existing_item = result.scalar_one_or_none()
        
        if existing_item:
            existing_item.quantity += data.quantity
            await db.commit()
            await db.refresh(existing_item)
            item = existing_item
        else:
            item = CartItem(
                cart_id=cart_id,
                product_id=data.product_id,
                quantity=data.quantity
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            
        await CommerceService._log_activity(db, workspace_id, "CART_ITEM_ADDED", actor_id=actor_id, details={"cart_id": cart.id, "product_id": product.id, "quantity": data.quantity})
        await db.commit()
        item.product = product
        # Ensure total and unit_price fields in CartItemResponse are met if they were added. Wait, CartItem base schema has no total or unit price explicitly in model, wait, I need to check schema.
        # Actually CartItem base has: product_id, quantity. CartItemResponse adds unit_price and total properties but wait, the model CartItem doesn't have them!
        # Let me add property methods dynamically or just let Pydantic model them if we want? The requirement didn't say CartItem needs unit_price. Ah, the schema has it, I'll need to make sure schema gets it. 
        # I'll just attach them
        item.unit_price = product.price
        item.total = product.price * item.quantity
        return item

    @staticmethod
    async def remove_cart_item(db: AsyncSession, workspace_id: str, cart_id: str, item_id: str, ctx: ExecutionContext):
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "remove_cart_item")
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        cart = await CommerceService.get_cart(db, workspace_id, cart_id)
        stmt = select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")
            
        product_id = item.product_id
        await db.delete(item)
        
        await CommerceService._log_activity(db, workspace_id, "CART_ITEM_REMOVED", actor_id=actor_id, details={"cart_id": cart.id, "product_id": product_id})
        await db.commit()

    @staticmethod
    async def update_cart_item(db: AsyncSession, workspace_id: str, cart_id: str, item_id: str, quantity: int, ctx: ExecutionContext) -> CartItem:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "update_cart_item")
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        cart = await CommerceService.get_cart(db, workspace_id, cart_id)
        stmt = select(CartItem).options(joinedload(CartItem.product)).where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")
            
        product = item.product
        if product.inventory < quantity:
            raise HTTPException(status_code=400, detail="Not enough inventory")
            
        item.quantity = quantity
        await CommerceService._log_activity(db, workspace_id, "CART_ITEM_UPDATED", actor_id=actor_id, details={"cart_id": cart.id, "item_id": item.id, "quantity": quantity})
        await db.commit()
        await db.refresh(item)
        item.unit_price = product.price
        item.total = product.price * item.quantity
        return item

    # --- Order ---
    @staticmethod
    async def create_order(db: AsyncSession, workspace_id: str, data: OrderCreate, ctx: ExecutionContext) -> Order:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "checkout", target_identity=data.cart_id)
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        order_agent_id = ctx.agent_id if ctx.is_agent else None
        
        cart = await CommerceService.get_cart(db, workspace_id, data.cart_id)
        if cart.status == CartStatus.CHECKED_OUT:
            stmt_existing_order = select(Order).where(Order.cart_id == cart.id, Order.workspace_id == workspace_id)
            res_order = await db.execute(stmt_existing_order)
            existing_order = res_order.scalars().first()
            if existing_order:
                return existing_order

        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cart is no longer active")
            
        if not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Duplicate order prevention across run:
        if ctx.agent_run_id:
            stmt_run_orders = select(Order).where(
                Order.workspace_id == workspace_id,
                Order.agent_id == (order_agent_id or cart.agent_id),
                Order.status.in_([OrderStatus.PENDING_PAYMENT, OrderStatus.PAID])
            )
            res_run_orders = await db.execute(stmt_run_orders)
            for existing_ord in res_run_orders.scalars().all():
                m = existing_ord.metadata_ or {}
                if m.get("agent_run_id") == ctx.agent_run_id:
                    return existing_ord

        stmt = select(Merchant).where(Merchant.id == data.merchant_id, Merchant.workspace_id == workspace_id)
        result = await db.execute(stmt)
        merchant = result.scalar_one_or_none()
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")

        order_meta = dict(data.metadata_ or {})
        if ctx.agent_run_id:
            order_meta["agent_run_id"] = ctx.agent_run_id

        order = Order(
            workspace_id=workspace_id,
            agent_id=order_agent_id or cart.agent_id,
            cart_id=cart.id,
            merchant_id=merchant.id,
            status=OrderStatus.PENDING_PAYMENT,
            currency=cart.currency,
            subtotal=0,
            total=0,
            metadata_=order_meta
        )
        db.add(order)
        await db.flush() 
        
        # Validate and lock products for inventory deduction
        product_ids = [item.product_id for item in cart.items]
        stmt_products = select(Product).where(Product.id.in_(product_ids)).with_for_update()
        result_products = await db.execute(stmt_products)
        products_dict = {p.id: p for p in result_products.scalars()}
        
        subtotal = 0
        for cart_item in cart.items:
            product = products_dict.get(cart_item.product_id)
            if not product or product.status != ProductStatus.ACTIVE:
                raise HTTPException(status_code=400, detail=f"Product {cart_item.product_id} is unavailable")
            if product.merchant_id != merchant.id:
                raise HTTPException(status_code=400, detail=f"Merchant mismatch: product '{product.name}' does not belong to merchant '{merchant.name}'")
            if order.currency and product.currency and order.currency != product.currency:
                raise HTTPException(status_code=400, detail=f"Currency mismatch: product {product.name} is in {product.currency} but order is in {order.currency}")
            if product.inventory < cart_item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough inventory for {product.name}")
                
            # Decrement inventory
            product.inventory -= cart_item.quantity
            
            line_total = product.price * cart_item.quantity
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                merchant_name_snapshot=merchant.name,
                quantity=cart_item.quantity,
                unit_price_at_order=product.price,
                total=line_total
            )
            db.add(order_item)
            subtotal += line_total
            
        order.subtotal = subtotal
        order.total = subtotal 
        
        cart.status = CartStatus.CHECKED_OUT
        
        await db.commit()
        await db.refresh(order)
        
        order = await CommerceService.get_order(db, workspace_id, order.id)
        
        await CommerceService._log_activity(
            db,
            workspace_id,
            "ORDER_CREATED",
            order_id=order.id,
            actor_id=actor_id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM),
            details={"total": order.total, "currency": order.currency}
        )
        await db.commit()
        return await CommerceService.get_order(db, workspace_id, order.id)

    @staticmethod
    async def get_order(db: AsyncSession, workspace_id: str, order_id: str) -> Order:
        stmt = select(Order).options(joinedload(Order.items).joinedload(OrderItem.product)).where(Order.id == order_id, Order.workspace_id == workspace_id)
        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @staticmethod
    async def list_orders(db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100) -> List[Order]:
        stmt = select(Order).options(joinedload(Order.items).joinedload(OrderItem.product)).where(Order.workspace_id == workspace_id).order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    @staticmethod
    async def cancel_order(db: AsyncSession, workspace_id: str, order_id: str, ctx: ExecutionContext) -> Order:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "cancel_order", target_identity=order_id)
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        order = await CommerceService.get_order(db, workspace_id, order_id)
        
        if order.status not in (OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT):
            raise HTTPException(status_code=400, detail=f"Cannot cancel order in status {order.status}")
            
        # Restore inventory
        for item in order.items:
            if item.product:
                item.product.inventory += item.quantity
                
        order.status = OrderStatus.CANCELLED
        await CommerceService._log_activity(
            db,
            workspace_id,
            "ORDER_CANCELLED",
            order_id=order.id,
            actor_id=actor_id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)
        )
        await db.commit()
        return await CommerceService.get_order(db, workspace_id, order.id)

    @staticmethod
    async def process_order(db: AsyncSession, workspace_id: str, order_id: str, ctx: ExecutionContext) -> Order:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "process_order", target_identity=order_id)
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        order = await CommerceService.get_order(db, workspace_id, order_id)
        if order.status != OrderStatus.PAID:
            raise HTTPException(status_code=400, detail=f"Cannot process order in status {order.status}. Must be PAID.")
            
        order.status = OrderStatus.PROCESSING
        await CommerceService._log_activity(
            db,
            workspace_id,
            "ORDER_PROCESSING",
            order_id=order.id,
            actor_id=actor_id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)
        )
        await db.commit()
        return await CommerceService.get_order(db, workspace_id, order.id)

    @staticmethod
    async def fulfill_order(db: AsyncSession, workspace_id: str, order_id: str, ctx: ExecutionContext) -> Order:
        await CommerceService._verify_gate_token(db, workspace_id, ctx, "fulfill_order", target_identity=order_id)
            
        actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
        order = await CommerceService.get_order(db, workspace_id, order_id)
        if order.status != OrderStatus.PROCESSING:
            raise HTTPException(status_code=400, detail=f"Cannot fulfill order in status {order.status}. Must be PROCESSING.")
            
        order.status = OrderStatus.FULFILLED
        await CommerceService._log_activity(
            db,
            workspace_id,
            "ORDER_FULFILLED",
            order_id=order.id,
            actor_id=actor_id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)
        )
        await db.commit()
        return await CommerceService.get_order(db, workspace_id, order.id)

    @staticmethod
    async def mark_order_paid(db: AsyncSession, order_id: str, payment_id: str):
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            return 
            
        if order.status != OrderStatus.PENDING_PAYMENT:
            return
            
        order.status = OrderStatus.PAID
        order.payment_id = payment_id
        await CommerceService._log_activity(
            db,
            order.workspace_id,
            "ORDER_PAID",
            order_id=order.id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if order.agent_id else ActorType.SYSTEM,
            details={"payment_id": payment_id, "total": order.total, "currency": order.currency}
        )
        await db.commit()

    @staticmethod
    async def mark_order_payment_failed(db: AsyncSession, order_id: str, payment_id: str):
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            return
            
        if order.status != OrderStatus.PENDING_PAYMENT:
            return
            
        # Restore inventory
        stmt_items = select(OrderItem).options(joinedload(OrderItem.product)).where(OrderItem.order_id == order_id)
        result_items = await db.execute(stmt_items)
        items = result_items.scalars().all()
        for item in items:
            if item.product:
                item.product.inventory += item.quantity
                
        order.status = OrderStatus.PAYMENT_FAILED
        order.payment_id = payment_id
        await CommerceService._log_activity(
            db,
            order.workspace_id,
            "ORDER_FAILED",
            order_id=order.id,
            agent_id=order.agent_id,
            actor_type=ActorType.AGENT if order.agent_id else ActorType.SYSTEM,
            details={"payment_id": payment_id},
            severity=EventSeverity.WARNING
        )
        await db.commit()
