from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole, RequireScopeOrRole, get_auth_context, ApiRequestContext
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.execution_context import ExecutionContext
import app.services.payment_service as payment_service

router = APIRouter()

@router.post("/intents", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_intent(
    payment_data: PaymentCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.DEVELOPER], required_scope="payments:write"))
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    payment = await payment_service.create_payment_intent(db, current_workspace.id, payment_data, ctx)
    return await payment_service.get_payment_dict(db, current_workspace.id, payment.id)

@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await payment_service.get_payments(db, current_workspace.id)

from pydantic import BaseModel

class PaymentMetrics(BaseModel):
    total_volume: int
    transactions: int
    captured_count: int
    failed_count: int
    failed_value: int

@router.get("/metrics", response_model=PaymentMetrics)
async def get_payment_metrics(
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await payment_service.get_payment_metrics(db, current_workspace.id)

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await payment_service.get_payment_dict(db, current_workspace.id, payment_id)

@router.post("/{payment_id}/authorize", response_model=PaymentResponse)
async def authorize_payment(
    payment_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], required_scope="payments:authorize"))
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    payment = await payment_service.authorize_payment(db, current_workspace.id, payment_id, ctx)
    return await payment_service.get_payment_dict(db, current_workspace.id, payment.id)

@router.post("/{payment_id}/capture", response_model=PaymentResponse)
async def capture_payment(
    payment_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], required_scope="payments:capture"))
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    payment = await payment_service.capture_payment(db, current_workspace.id, payment_id, ctx)
    return await payment_service.get_payment_dict(db, current_workspace.id, payment.id)

@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], required_scope="payments:cancel"))
):
    ctx = ExecutionContext(
        is_human=auth_ctx.is_human,
        user_id=auth_ctx.user_id,
        is_agent=auth_ctx.is_agent,
        agent_id=auth_ctx.agent_id,
        is_agent_runtime=False
    )
    payment = await payment_service.cancel_payment(db, current_workspace.id, payment_id, ctx)
    return await payment_service.get_payment_dict(db, current_workspace.id, payment.id)
