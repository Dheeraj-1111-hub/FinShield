from typing import List
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.db.database import get_db
from app.models.user import User, UserStatus
from app.models.session import Session
from app.models.workspace import WorkspaceMember, Workspace, WorkspaceRole
from app.core.security import hash_session_token

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    session_token = request.cookies.get("finshield_session")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
            
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    token_hash = hash_session_token(session_token)
    
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
        
    if session.revoked_at is not None or (session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
        
    # Update last seen
    session.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    
    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalars().first()
    
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled or suspended")
        
    return user

# We define get_current_workspace and RequireScopeOrRole after get_auth_context below.

from pydantic import BaseModel
from typing import List, Optional
class ApiRequestContext(BaseModel):
    workspace_id: str
    client_id: Optional[str] = None
    credential_id: Optional[str] = None
    scopes: List[str]
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    @property
    def is_human(self) -> bool:
        return self.user_id is not None
        
    @property
    def is_agent(self) -> bool:
        return self.agent_id is not None

async def get_auth_context(request: Request, db: AsyncSession = Depends(get_db)) -> ApiRequestContext:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        from app.services.developer_auth import DeveloperAuthService
        auth_svc = DeveloperAuthService(db)
        try:
            cred = await auth_svc.validate_api_key(token)
            return ApiRequestContext(
                workspace_id=cred.workspace_id,
                client_id=cred.api_client_id,
                credential_id=cred.id,
                scopes=cred.scopes,
                user_id=None,
                agent_id=None
            )
        except HTTPException:
            # If it's not a valid Developer API key, check if it's an Agent Credential
            pass
            
        from app.services.agent_auth_service import validate_agent_token
        try:
            agent_cred = await validate_agent_token(db, token)
            return ApiRequestContext(
                workspace_id=agent_cred.agent.workspace_id,
                credential_id=agent_cred.id,
                scopes=agent_cred.agent.capabilities or [],
                user_id=None,
                agent_id=agent_cred.agent_id
            )
        except HTTPException:
            # Not an agent credential either, fallback to UI session
            pass
    
    # Fallback to UI session
    try:
        user = await get_current_user(request, db)
        # We need workspace context for the UI, usually passed via path or body, but default to user's primary
        return ApiRequestContext(
            workspace_id="default", # This might need route-level handling, but for now it satisfies the type
            user_id=user.id,
            scopes=["*"],
            agent_id=None
        )
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication")

async def get_current_workspace(request: Request, auth_ctx: ApiRequestContext = Depends(get_auth_context), db: AsyncSession = Depends(get_db)):
    if auth_ctx.client_id or auth_ctx.agent_id:
        workspace_id_param = request.path_params.get("workspace_id") or request.headers.get("X-Workspace-ID") or request.query_params.get("workspace_id")
        if workspace_id_param and workspace_id_param != auth_ctx.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API credential does not belong to requested workspace")
        result = await db.execute(select(Workspace).where(Workspace.id == auth_ctx.workspace_id))
        workspace = result.scalars().first()
        if not workspace:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API workspace not found")
        return workspace
    else:
        # It's a UI session. Ideally workspace_id is in query params.
        # But get_auth_context doesn't parse it well yet. We should get workspace from URL if provided,
        # otherwise fallback to first workspace for UI backwards compatibility.
        workspace_id_param = request.path_params.get("workspace_id") or request.headers.get("X-Workspace-ID") or request.query_params.get("workspace_id")
        
        stmt = select(Workspace).join(WorkspaceMember).where(WorkspaceMember.user_id == auth_ctx.user_id)
        if workspace_id_param:
            stmt = stmt.where(Workspace.id == workspace_id_param)
            
        result = await db.execute(stmt)
        workspace = result.scalars().first()
        if not workspace:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace found for user")
            
        return workspace

class RequireWorkspaceRole:
    """Legacy alias, functionally identical to RequireScopeOrRole with no required API scope"""
    def __init__(self, allowed_roles: List[WorkspaceRole]):
        self.allowed_roles = allowed_roles
        
    async def __call__(self, auth_ctx: ApiRequestContext = Depends(get_auth_context), current_workspace: Workspace = Depends(get_current_workspace), db: AsyncSession = Depends(get_db)):
        if auth_ctx.client_id:
            # API requests must have admin or wildcard scope if endpoint requires administrative role (OWNER/ADMIN)
            if WorkspaceRole.OWNER in self.allowed_roles or WorkspaceRole.ADMIN in self.allowed_roles:
                if "admin" not in auth_ctx.scopes and "*" not in auth_ctx.scopes:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient API scopes for administrative operation")
            return None # API requests pass role check if scoped appropriately
            
        result = await db.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == auth_ctx.user_id)
            .where(WorkspaceMember.workspace_id == current_workspace.id)
        )
        member = result.scalars().first()
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        if member.role not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions")
        return member

class RequireScopeOrRole(RequireWorkspaceRole):
    def __init__(self, allowed_roles: List[WorkspaceRole], required_scope: str):
        super().__init__(allowed_roles)
        self.required_scope = required_scope

    async def __call__(self, auth_ctx: ApiRequestContext = Depends(get_auth_context), current_workspace: Workspace = Depends(get_current_workspace), db: AsyncSession = Depends(get_db)):
        if auth_ctx.client_id:
            if self.required_scope not in auth_ctx.scopes and "*" not in auth_ctx.scopes:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient API scopes. Requires: {self.required_scope}")
            return None
        return await super().__call__(auth_ctx, current_workspace, db)
