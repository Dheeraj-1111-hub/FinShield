from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.services.overview_service import get_workspace_overview
from app.schemas.overview import OverviewResponse

router = APIRouter()

@router.get("", response_model=OverviewResponse)
async def get_overview(
    time_range: str = Query("30d", description="Time range for aggregation (24h, 7d, 30d, 90d)"),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([
        WorkspaceRole.OWNER, 
        WorkspaceRole.ADMIN, 
        WorkspaceRole.ANALYST,
        WorkspaceRole.DEVELOPER,
        WorkspaceRole.VIEWER
    ]))
):
    """
    Get the workspace overview and command center aggregation.
    """
    return await get_workspace_overview(db, current_workspace.id, time_range)
