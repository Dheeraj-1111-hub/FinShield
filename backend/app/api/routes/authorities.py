from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.authority import AuthorityStatus
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.schemas.authority import (
    AuthorityCreate, AuthorityUpdate, AuthorityResponse,
    AuthorityVersionResponse, AuthorityEvaluationRequest, AuthoritySimulationRequest, AuthorityEvaluationResult,
)
import app.services.authority_service as authority_service
from app.services.authority_evaluator import evaluate_authority
from app.services.alignment_engine import evaluate_alignment

router = APIRouter()


@router.post("", response_model=AuthorityResponse, status_code=status.HTTP_201_CREATED)
async def create_authority(
    data: AuthorityCreate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    return await authority_service.create_authority(db, current_workspace.id, current_user.id, data)


@router.get("", response_model=List[AuthorityResponse])
async def list_authorities(
    agent_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    status_enum = AuthorityStatus(status_filter) if status_filter else None
    return await authority_service.list_authorities(
        db, current_workspace.id, agent_id=agent_id, intent_id=intent_id,
        status=status_enum, skip=skip, limit=limit,
    )


@router.get("/{authority_id}", response_model=AuthorityResponse)
async def get_authority(
    authority_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await authority_service.get_authority(db, current_workspace.id, authority_id)


@router.patch("/{authority_id}", response_model=AuthorityResponse)
async def update_authority(
    authority_id: str,
    data: AuthorityUpdate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    return await authority_service.update_authority(db, current_workspace.id, authority_id, current_user.id, data)


@router.post("/{authority_id}/activate", response_model=AuthorityResponse)
async def activate_authority(
    authority_id: str,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    return await authority_service.activate_authority(db, current_workspace.id, authority_id, current_user.id)


@router.post("/{authority_id}/revoke", response_model=AuthorityResponse)
async def revoke_authority(
    authority_id: str,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    return await authority_service.revoke_authority(db, current_workspace.id, authority_id, current_user.id)


@router.get("/{authority_id}/versions", response_model=List[AuthorityVersionResponse])
async def list_authority_versions(
    authority_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await authority_service.list_authority_versions(db, current_workspace.id, authority_id)


@router.post("/evaluate", response_model=AuthorityEvaluationResult)
async def evaluate_authority_endpoint(
    data: AuthorityEvaluationRequest,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Simulate whether a given action would be authorized by the specified authority.
    This does NOT execute the action — it is purely evaluative.
    """
    from app.models.agent import Agent
    from app.models.intent import Intent

    authority = await authority_service.get_authority(db, current_workspace.id, data.authority_id)
    
    # Verify agent binding
    if authority.agent_id != data.agent_id:
        return AuthorityEvaluationResult(
            authorized=False,
            reasons=["Authority is not bound to the specified agent"],
            effective_monetary_limit=None,
            authority_version=authority.version,
        )

    agent = await db.get(Agent, data.agent_id)
    if not agent or agent.workspace_id != current_workspace.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent not found")

    # Fetch intent if linked
    intent = None
    if authority.intent_id:
        intent = await db.get(Intent, authority.intent_id)

    eval_result = evaluate_authority(
        authority=authority,
        agent=agent,
        action=data.action,
        amount=data.amount,
        currency=data.currency,
        intent=intent,
    )

    if intent and intent.structured_constraints:
        alignment = evaluate_alignment(
            constraints=intent.structured_constraints,
            action=data.action,
            amount=data.amount,
            currency=data.currency,
        )
        eval_result.alignment_result = alignment.alignment
        eval_result.alignment_signals = [s.model_dump() for s in alignment.signals]

    return eval_result


@router.post("/{authority_id}/simulate", response_model=AuthorityEvaluationResult)
async def simulate_authority_endpoint(
    authority_id: str,
    data: AuthoritySimulationRequest,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Simulate what happens if an action is attempted under this specific authority.
    Purely evaluative: does not create carts, orders, or payments.
    Evaluates active authority, bound agent, monetary constraints, and linked intent.
    """
    from app.models.agent import Agent
    from app.models.intent import Intent
    from fastapi import HTTPException

    authority = await authority_service.get_authority(db, current_workspace.id, authority_id)

    agent = await db.get(Agent, authority.agent_id)
    if not agent or agent.workspace_id != current_workspace.id:
        raise HTTPException(status_code=404, detail="Agent bound to authority not found in workspace")

    intent = None
    if authority.intent_id:
        intent = await db.get(Intent, authority.intent_id)

    eval_result = evaluate_authority(
        authority=authority,
        agent=agent,
        action=data.action,
        amount=data.amount,
        currency=data.currency,
        intent=intent,
    )

    if intent and intent.structured_constraints:
        alignment = evaluate_alignment(
            constraints=intent.structured_constraints,
            action=data.action,
            amount=data.amount,
            currency=data.currency,
        )
        eval_result.alignment_result = alignment.alignment
        eval_result.alignment_signals = [s.model_dump() for s in alignment.signals]

    return eval_result

