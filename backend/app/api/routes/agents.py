from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentStatusUpdate
import app.services.agent_service as agent_service

router = APIRouter()

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    return await agent_service.create_agent(db, current_workspace.id, current_user.id, agent_data)

@router.get("", response_model=List[AgentResponse])
async def list_agents(
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await agent_service.get_agents(db, current_workspace.id)

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await agent_service.get_agent(db, current_workspace.id, agent_id)

@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    return await agent_service.update_agent(db, current_workspace.id, agent_id, current_user.id, agent_data)

@router.post("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: str,
    status_data: AgentStatusUpdate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    return await agent_service.update_agent_status(db, current_workspace.id, agent_id, current_user.id, status_data.status)

from app.schemas.agent import AgentCredentialCreate, AgentCredentialResponse, AgentCredentialSecretResponse

@router.post("/{agent_id}/credentials", response_model=AgentCredentialSecretResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_credential(
    agent_id: str,
    cred_data: AgentCredentialCreate,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    cred, secret = await agent_service.create_agent_credential(db, current_workspace.id, agent_id, current_user.id, cred_data)
    base_cred = AgentCredentialResponse.model_validate(cred)
    response_data = AgentCredentialSecretResponse(**base_cred.model_dump(), client_secret=secret)
    return response_data

@router.get("/{agent_id}/credentials", response_model=List[AgentCredentialResponse])
async def list_agent_credentials(
    agent_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await agent_service.list_agent_credentials(db, current_workspace.id, agent_id)

@router.delete("/{agent_id}/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_credential(
    agent_id: str,
    credential_id: str,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    await agent_service.revoke_agent_credential(db, current_workspace.id, agent_id, current_user.id, credential_id)

@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    return await agent_service.get_agent_activity(db, current_workspace.id, agent_id)
