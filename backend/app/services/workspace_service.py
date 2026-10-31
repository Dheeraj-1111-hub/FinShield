import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.workspace import Workspace
from app.models.workspace_settings import WorkspaceSettings
from app.models.audit import EventCategory, EventSeverity, ActorType, EventTypes
from app.services.audit_service import AuditService
import re

async def get_or_create_workspace_settings(db: AsyncSession, workspace_id: str) -> WorkspaceSettings:
    result = await db.execute(select(WorkspaceSettings).where(WorkspaceSettings.workspace_id == workspace_id))
    settings = result.scalars().first()
    
    if not settings:
        settings = WorkspaceSettings(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings

async def update_workspace_settings(db: AsyncSession, workspace_id: str, update_data: dict, actor_id: str) -> WorkspaceSettings:
    settings = await get_or_create_workspace_settings(db, workspace_id)
    
    # Extract values for validation
    new_risk = update_data.get("risk_threshold", settings.risk_threshold)
    new_review = update_data.get("review_threshold", settings.review_threshold)
    
    if "risk_threshold" in update_data or "review_threshold" in update_data:
        if new_review >= new_risk:
            raise HTTPException(status_code=400, detail="Review threshold must be less than risk threshold.")
        if not (0 <= new_risk <= 100) or not (0 <= new_review <= 100):
            raise HTTPException(status_code=400, detail="Thresholds must be between 0 and 100.")
            
    # Optimistic concurrency check if version is provided
    if "version" in update_data and update_data["version"] != settings.version:
        raise HTTPException(status_code=409, detail="Settings have been modified by another user. Please refresh and try again.")
        
    # Apply updates
    for key, value in update_data.items():
        if hasattr(settings, key) and key not in ["id", "workspace_id", "version", "updated_at"]:
            setattr(settings, key, value)
            
    # Increment version
    settings.version += 1
    
    await db.commit()
    await db.refresh(settings)

    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=EventTypes.WORKSPACE_SETTINGS_UPDATED,
        event_category=EventCategory.WORKSPACE,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
        actor_id=actor_id,
        entity_type="WORKSPACE",
        entity_id=workspace_id,
        payload=update_data
    )

    return settings

async def update_workspace(db: AsyncSession, workspace: Workspace, update_data: dict, actor_id: str) -> Workspace:
    # Validate currency/timezone if needed, etc.
    if "slug" in update_data:
        new_slug = update_data["slug"]
        if not new_slug or type(new_slug) != str:
            raise HTTPException(status_code=400, detail="Slug cannot be empty.")
        if len(new_slug) < 3 or len(new_slug) > 40:
            raise HTTPException(status_code=400, detail="Slug must be between 3 and 40 characters long.")
        if not re.match(r"^[a-z0-9-]+$", new_slug):
            raise HTTPException(status_code=400, detail="Slug can only contain lowercase letters, numbers, and hyphens.")
            
        # Check uniqueness
        result = await db.execute(select(Workspace).where(Workspace.slug == new_slug).where(Workspace.id != workspace.id))
        if result.scalars().first():
            raise HTTPException(status_code=409, detail="Workspace slug already exists.")

    for key, value in update_data.items():
        if hasattr(workspace, key) and key not in ["id", "owner_id", "created_at", "updated_at"]:
            setattr(workspace, key, value)
            
    await db.commit()
    await db.refresh(workspace)

    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace.id,
        event_type=EventTypes.WORKSPACE_UPDATED,
        event_category=EventCategory.WORKSPACE,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
        actor_id=actor_id,
        entity_type="WORKSPACE",
        entity_id=workspace.id,
        payload=update_data
    )

    return workspace
