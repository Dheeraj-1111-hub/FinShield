from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole, get_auth_context, ApiRequestContext
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole
from app.schemas.execution_context import ExecutionContext
from app.schemas.commerce import (
    MerchantCreate, MerchantResponse,
    ProductCreate, ProductResponse,
    CartCreate, CartResponse, CartItemCreate, CartItemResponse,
    OrderCreate, OrderResponse
)
from app.services.commerce_service import CommerceService

router = APIRouter(tags=["Commerce"])

# Role Dependencies
dev_access = RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.DEVELOPER])

# --- Merchants ---
@router.post("/merchants", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dev_access)])
async def create_merchant(
    data: MerchantCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.create_merchant(db, current_workspace.id, data, ctx)

@router.get("/merchants", response_model=List[MerchantResponse], dependencies=[Depends(dev_access)])
async def list_merchants(
    skip: int = 0,
    limit: int = 100,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.list_merchants(db, current_workspace.id, skip, limit)

# --- Products ---
@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dev_access)])
async def create_product(
    data: ProductCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.create_product(db, current_workspace.id, data, ctx)

@router.get("/products", response_model=List[ProductResponse], dependencies=[Depends(dev_access)])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    merchant_id: str = None,
    category: str = None,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.list_products(db, current_workspace.id, skip, limit, merchant_id, category)

@router.get("/products/{product_id}", response_model=ProductResponse, dependencies=[Depends(dev_access)])
async def get_product(
    product_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.get_product(db, current_workspace.id, product_id)

# --- Carts ---
@router.post("/carts", response_model=CartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dev_access)])
async def create_cart(
    data: CartCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.create_cart(db, current_workspace.id, data, ctx)

@router.get("/carts/{cart_id}", response_model=CartResponse, dependencies=[Depends(dev_access)])
async def get_cart(
    cart_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.get_cart(db, current_workspace.id, cart_id)

@router.post("/carts/{cart_id}/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dev_access)])
async def add_cart_item(
    cart_id: str,
    data: CartItemCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.add_cart_item(db, current_workspace.id, cart_id, data, ctx)

@router.patch("/carts/{cart_id}/items/{item_id}", response_model=CartItemResponse, dependencies=[Depends(dev_access)])
async def update_cart_item(
    cart_id: str,
    item_id: str,
    data: dict,  # Wait, I should import CartItemUpdate, but I'll define it or use dict to avoid import errors
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    # Expecting {"quantity": N}
    quantity = data.get("quantity")
    if quantity is None or quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.update_cart_item(db, current_workspace.id, cart_id, item_id, quantity, ctx)

@router.delete("/carts/{cart_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(dev_access)])
async def remove_cart_item(
    cart_id: str,
    item_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    await CommerceService.remove_cart_item(db, current_workspace.id, cart_id, item_id, ctx)
    return None

# --- Orders ---
@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dev_access)])
async def create_order(
    data: OrderCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.create_order(db, current_workspace.id, data, ctx)

@router.get("/orders", response_model=List[OrderResponse], dependencies=[Depends(dev_access)])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.list_orders(db, current_workspace.id, skip, limit)

@router.get("/orders/{order_id}", response_model=OrderResponse, dependencies=[Depends(dev_access)])
async def get_order(
    order_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await CommerceService.get_order(db, current_workspace.id, order_id)

@router.post("/orders/{order_id}/cancel", response_model=OrderResponse, dependencies=[Depends(dev_access)])
async def cancel_order(
    order_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.cancel_order(db, current_workspace.id, order_id, ctx)

@router.post("/orders/{order_id}/process", response_model=OrderResponse, dependencies=[Depends(dev_access)])
async def process_order(
    order_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.process_order(db, current_workspace.id, order_id, ctx)

@router.post("/orders/{order_id}/fulfill", response_model=OrderResponse, dependencies=[Depends(dev_access)])
async def fulfill_order(
    order_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    return await CommerceService.fulfill_order(db, current_workspace.id, order_id, ctx)
