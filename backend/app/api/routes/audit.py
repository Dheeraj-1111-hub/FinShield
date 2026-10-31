from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import json

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.models.audit import AuditEvent, EventCategory, EventSeverity
from app.schemas.audit import AuditEventResponse, AuditIntegrityResponse
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/", response_model=List[AuditEventResponse])
async def list_audit_events(
    skip: int = Query(0, ge=0),
    offset: Optional[int] = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[EventCategory] = None,
    severity: Optional[EventSeverity] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditEvent).where(AuditEvent.workspace_id == current_workspace.id)
    
    if category:
        stmt = stmt.where(AuditEvent.event_category == category)
    if severity:
        stmt = stmt.where(AuditEvent.severity == severity)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
        
    actual_skip = offset if offset is not None else skip
    stmt = stmt.order_by(desc(AuditEvent.workspace_sequence)).offset(actual_skip).limit(limit)
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    return events

@router.post("/integrity/verify", response_model=AuditIntegrityResponse)
@router.get("/integrity/verify", response_model=AuditIntegrityResponse)
async def verify_audit_integrity(
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    audit_service = AuditService(db)
    result = await audit_service.verify_integrity(current_workspace.id)
    return result

@router.get("/export", response_model=List[AuditEventResponse])
async def export_audit_log(
    current_workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    audit_service = AuditService(db)
    
    # Log the export request
    from app.models.audit import ActorType, EventTypes
    
    await audit_service.record_event(
        workspace_id=current_workspace.id,
        event_type=EventTypes.AUDIT_EXPORT_REQUESTED,
        event_category=EventCategory.SYSTEM,
        severity=EventSeverity.HIGH,
        actor_type=ActorType.USER,
        actor_id=current_user.id,
        metadata={"export_format": "JSON"}
    )
    await db.commit()

    stmt = select(AuditEvent).where(
        AuditEvent.workspace_id == current_workspace.id
    ).order_by(AuditEvent.workspace_sequence)
    
    result = await db.execute(stmt.limit(5000))
    return result.scalars().all()

@router.get("/entities/{entity_type}/{entity_id}", response_model=List[AuditEventResponse])
async def get_audit_entity_history(
    entity_type: str,
    entity_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditEvent).where(
        AuditEvent.workspace_id == current_workspace.id,
        AuditEvent.entity_type == entity_type.upper(),
        AuditEvent.entity_id == entity_id
    ).order_by(desc(AuditEvent.workspace_sequence))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/correlations/{correlation_id}", response_model=List[AuditEventResponse])
async def get_audit_correlation_history(
    correlation_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditEvent).where(
        AuditEvent.workspace_id == current_workspace.id,
        AuditEvent.correlation_id == correlation_id
    ).order_by(desc(AuditEvent.workspace_sequence))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: str,
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditEvent).where(
        AuditEvent.workspace_id == current_workspace.id,
        AuditEvent.id == event_id
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")
        
    return event
