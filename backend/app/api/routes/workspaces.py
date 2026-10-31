from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.services.workspace_service import get_or_create_workspace_settings, update_workspace_settings, update_workspace

router = APIRouter()

@router.get("/current")
async def get_my_workspace(current_workspace: Workspace = Depends(get_current_workspace)):
    return {
        "workspace": {
            "id": current_workspace.id,
            "name": current_workspace.name,
            "slug": current_workspace.slug,
            "environment": current_workspace.environment,
            "currency": current_workspace.currency,
            "timezone": current_workspace.timezone,
            "created_at": current_workspace.created_at,
        }
    }

@router.patch("/current")
async def patch_my_workspace(
    update_data: Dict[str, Any], 
    current_user: User = Depends(get_current_user), 
    current_workspace: Workspace = Depends(get_current_workspace), 
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    updated_workspace = await update_workspace(db, current_workspace, update_data, current_user.id)
    return {
        "message": "Workspace updated successfully",
        "workspace": {
            "id": updated_workspace.id,
            "name": updated_workspace.name,
            "slug": updated_workspace.slug,
            "environment": updated_workspace.environment,
            "currency": updated_workspace.currency,
            "timezone": updated_workspace.timezone,
        }
    }

@router.get("/current/settings")
async def get_my_workspace_settings(current_workspace: Workspace = Depends(get_current_workspace), db: AsyncSession = Depends(get_db)):
    settings = await get_or_create_workspace_settings(db, current_workspace.id)
    return {
        "settings": {
            "risk_threshold": settings.risk_threshold,
            "review_threshold": settings.review_threshold,
            "high_value_transaction_threshold": settings.high_value_transaction_threshold,
            "human_review_for_critical_actions": settings.human_review_for_critical_actions,
            "audit_retention_days": settings.audit_retention_days,
            "investigation_retention_days": settings.investigation_retention_days,
            "session_timeout_hours": settings.session_timeout_hours,
            "version": settings.version,
        }
    }

@router.patch("/current/settings")
async def patch_my_workspace_settings(
    update_data: Dict[str, Any], 
    current_user: User = Depends(get_current_user), 
    current_workspace: Workspace = Depends(get_current_workspace), 
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    updated_settings = await update_workspace_settings(db, current_workspace.id, update_data, current_user.id)
    return {
        "message": "Workspace settings updated successfully",
        "settings": {
            "risk_threshold": updated_settings.risk_threshold,
            "review_threshold": updated_settings.review_threshold,
            "high_value_transaction_threshold": updated_settings.high_value_transaction_threshold,
            "human_review_for_critical_actions": updated_settings.human_review_for_critical_actions,
            "audit_retention_days": updated_settings.audit_retention_days,
            "investigation_retention_days": updated_settings.investigation_retention_days,
            "session_timeout_hours": updated_settings.session_timeout_hours,
            "version": updated_settings.version,
        }
    }
