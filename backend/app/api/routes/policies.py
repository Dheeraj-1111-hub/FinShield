from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyResponse, PolicyEvaluationRequest, PolicyEvaluationResponse
import app.services.policy_service as policy_service

router = APIRouter()

@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: PolicyCreate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    return await policy_service.create_policy(db, current_workspace.id, current_user.id, policy_data)

@router.get("", response_model=List[PolicyResponse])
async def list_policies(
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await policy_service.get_policies(db, current_workspace.id)

@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await policy_service.get_policy(db, current_workspace.id, policy_id)

@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    policy_data: PolicyUpdate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    return await policy_service.update_policy(db, current_workspace.id, policy_id, current_user.id, policy_data)

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    await policy_service.delete_policy(db, current_workspace.id, policy_id, current_user.id)
    return None

@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policies(
    request: PolicyEvaluationRequest,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await policy_service.evaluate_policies(db, current_workspace.id, request)
