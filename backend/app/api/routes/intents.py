from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.intent import IntentStatus
from app.core.dependencies import (
    get_current_user, get_current_workspace, get_db, RequireScopeOrRole,
    get_auth_context, ApiRequestContext
)
from app.schemas.intent import (
    IntentCreate, IntentUpdate, IntentResponse,
    IntentVersionResponse, ExtractionRequest, ExtractionProposal,
    IntentEvaluationRequest, AlignmentResult,
)
import app.services.intent_service as intent_service
from app.services.intent_extractor import extract_intent
from app.services.alignment_engine import evaluate_alignment

router = APIRouter()


@router.post("", response_model=IntentResponse, status_code=status.HTTP_201_CREATED)
async def create_intent(
    data: IntentCreate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], "intents:write")),
):
    intent = await intent_service.create_intent(db, current_workspace.id, auth_ctx.user_id, data)
    return IntentResponse.from_orm_model(intent)


@router.get("", response_model=List[IntentResponse])
async def list_intents(
    status_filter: Optional[str] = None,
    agent_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.VIEWER], "intents:read")),
):
    status_enum = IntentStatus(status_filter) if status_filter else None
    intents = await intent_service.list_intents(
        db, current_workspace.id, status=status_enum, agent_id=agent_id, skip=skip, limit=limit
    )
    return [IntentResponse.from_orm_model(i) for i in intents]


@router.get("/{intent_id}", response_model=IntentResponse)
async def get_intent(
    intent_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.VIEWER], "intents:read")),
):
    intent = await intent_service.get_intent(db, current_workspace.id, intent_id)
    return IntentResponse.from_orm_model(intent)


@router.patch("/{intent_id}", response_model=IntentResponse)
async def update_intent(
    intent_id: str,
    data: IntentUpdate,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], "intents:write")),
):
    intent = await intent_service.update_intent(db, current_workspace.id, intent_id, auth_ctx.user_id, data)
    return IntentResponse.from_orm_model(intent)


@router.post("/{intent_id}/confirm", response_model=IntentResponse)
async def confirm_intent(
    intent_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], "intents:write")),
):
    intent = await intent_service.confirm_intent(db, current_workspace.id, intent_id, auth_ctx.user_id)
    return IntentResponse.from_orm_model(intent)


@router.post("/{intent_id}/pause", response_model=IntentResponse)
async def pause_intent(
    intent_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], "intents:write")),
):
    intent = await intent_service.pause_intent(db, current_workspace.id, intent_id, auth_ctx.user_id)
    return IntentResponse.from_orm_model(intent)


@router.post("/{intent_id}/revoke", response_model=IntentResponse)
async def revoke_intent(
    intent_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN], "intents:write")),
):
    intent = await intent_service.revoke_intent(db, current_workspace.id, intent_id, auth_ctx.user_id)
    return IntentResponse.from_orm_model(intent)


@router.get("/{intent_id}/versions", response_model=List[IntentVersionResponse])
async def list_intent_versions(
    intent_id: str,
    auth_ctx: ApiRequestContext = Depends(get_auth_context),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: Optional[WorkspaceMember] = Depends(RequireScopeOrRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.VIEWER], "intents:read")),
):
    return await intent_service.list_intent_versions(db, current_workspace.id, intent_id)


@router.post("/extract", response_model=ExtractionProposal)
async def extract_intent_proposal(
    data: ExtractionRequest,
    _: User = Depends(get_current_user),
):
    """
    Propose a structured intent from natural language text.
    This does NOT create any intent — it returns a proposal for user review.
    """
    return extract_intent(data.text)


@router.post("/evaluate", response_model=AlignmentResult)
async def evaluate_intent_alignment(
    data: IntentEvaluationRequest,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Evaluate how well a proposed action aligns with an existing intent."""
    intent = await intent_service.get_intent(db, current_workspace.id, data.intent_id)
    return evaluate_alignment(
        constraints=intent.structured_constraints,
        action=data.action,
        amount=data.amount,
        currency=data.currency,
        product_category=data.product_category,
        merchant_id=data.merchant_id,
    )
