import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.intent import Intent, IntentVersion, IntentStatus, IntentType
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
from app.schemas.intent import IntentCreate, IntentUpdate


async def _log_intent_activity(
    db: AsyncSession,
    intent_id: str,
    workspace_id: str,
    action: str,
    actor_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO,
):
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=action,
        event_category=EventCategory.INTENT,
        severity=severity,
        actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
        actor_id=actor_id,
        entity_type="INTENT",
        entity_id=intent_id,
        payload=details or {},
    )


def _make_version_snapshot(intent: Intent) -> IntentVersion:
    return IntentVersion(
        intent_id=intent.id,
        version_number=intent.version,
        structured_constraints=intent.structured_constraints or {},
        intent_type=intent.intent_type,
        title=intent.title,
        created_by=intent.created_by,
    )


async def create_intent(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    data: IntentCreate,
) -> Intent:
    intent = Intent(
        workspace_id=workspace_id,
        created_by=user_id,
        agent_id=data.agent_id,
        status=IntentStatus.DRAFT,
        intent_type=data.intent_type,
        title=data.title,
        natural_language_request=data.natural_language_request,
        structured_constraints=data.structured_constraints.model_dump() if data.structured_constraints else {},
        version=1,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        metadata_=data.metadata,
    )
    db.add(intent)
    await db.flush()

    snapshot = _make_version_snapshot(intent)
    db.add(snapshot)

    await _log_intent_activity(db, intent.id, workspace_id, "INTENT_CREATED",
                               actor_id=user_id, details={"version": 1})
    await db.commit()
    return await get_intent(db, workspace_id, intent.id)


async def get_intent(db: AsyncSession, workspace_id: str, intent_id: str) -> Intent:
    stmt = (
        select(Intent)
        .options(selectinload(Intent.versions))
        .where(Intent.id == intent_id, Intent.workspace_id == workspace_id)
    )
    result = await db.execute(stmt)
    intent = result.scalar_one_or_none()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    return intent


async def list_intents(
    db: AsyncSession,
    workspace_id: str,
    status: Optional[IntentStatus] = None,
    agent_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Intent]:
    stmt = (
        select(Intent)
        .where(Intent.workspace_id == workspace_id)
        .order_by(Intent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Intent.status == status)
    if agent_id:
        stmt = stmt.where(Intent.agent_id == agent_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_intent(
    db: AsyncSession,
    workspace_id: str,
    intent_id: str,
    user_id: str,
    data: IntentUpdate,
) -> Intent:
    intent = await get_intent(db, workspace_id, intent_id)
    if intent.status in [IntentStatus.REVOKED, IntentStatus.CANCELLED, IntentStatus.EXPIRED]:
        raise HTTPException(status_code=400, detail=f"Cannot update an intent with status {intent.status}")

    if data.title is not None:
        intent.title = data.title
    if data.intent_type is not None:
        intent.intent_type = data.intent_type
    if data.natural_language_request is not None:
        intent.natural_language_request = data.natural_language_request
    if data.structured_constraints is not None:
        intent.structured_constraints = data.structured_constraints.model_dump()
    if data.agent_id is not None:
        intent.agent_id = data.agent_id
    if data.valid_from is not None:
        intent.valid_from = data.valid_from
    if data.valid_until is not None:
        intent.valid_until = data.valid_until
    if data.metadata is not None:
        intent.metadata_ = data.metadata

    intent.version += 1
    intent.updated_at = datetime.now(timezone.utc)

    snapshot = _make_version_snapshot(intent)
    snapshot.created_by = user_id
    db.add(snapshot)

    await _log_intent_activity(db, intent.id, workspace_id, "INTENT_UPDATED",
                               actor_id=user_id, details={"new_version": intent.version})
    await db.commit()
    return await get_intent(db, workspace_id, intent_id)


async def confirm_intent(
    db: AsyncSession,
    workspace_id: str,
    intent_id: str,
    user_id: str,
) -> Intent:
    intent = await get_intent(db, workspace_id, intent_id)
    if intent.status != IntentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT intents can be confirmed")
    intent.status = IntentStatus.ACTIVE
    intent.updated_at = datetime.now(timezone.utc)
    await _log_intent_activity(db, intent.id, workspace_id, "INTENT_CONFIRMED",
                               actor_id=user_id)
    await db.commit()
    return await get_intent(db, workspace_id, intent_id)


async def pause_intent(
    db: AsyncSession,
    workspace_id: str,
    intent_id: str,
    user_id: str,
) -> Intent:
    intent = await get_intent(db, workspace_id, intent_id)
    if intent.status != IntentStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only ACTIVE intents can be paused")
    intent.status = IntentStatus.PAUSED
    intent.updated_at = datetime.now(timezone.utc)
    await _log_intent_activity(db, intent.id, workspace_id, "INTENT_PAUSED",
                               actor_id=user_id)
    await db.commit()
    return await get_intent(db, workspace_id, intent_id)


async def revoke_intent(
    db: AsyncSession,
    workspace_id: str,
    intent_id: str,
    user_id: str,
) -> Intent:
    intent = await get_intent(db, workspace_id, intent_id)
    if intent.status in [IntentStatus.REVOKED, IntentStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Intent is already revoked or cancelled")
    intent.status = IntentStatus.REVOKED
    intent.updated_at = datetime.now(timezone.utc)
    await _log_intent_activity(db, intent.id, workspace_id, "INTENT_REVOKED",
                               actor_id=user_id)
    await db.commit()
    return await get_intent(db, workspace_id, intent_id)


async def list_intent_versions(
    db: AsyncSession,
    workspace_id: str,
    intent_id: str,
) -> List[IntentVersion]:
    # First verify workspace isolation
    await get_intent(db, workspace_id, intent_id)
    stmt = (
        select(IntentVersion)
        .where(IntentVersion.intent_id == intent_id)
        .order_by(IntentVersion.version_number.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def expire_stale_intents(db: AsyncSession) -> int:
    """Mark all expired intents (valid_until < now) as EXPIRED. Returns count."""
    now = datetime.now(timezone.utc)
    stmt = select(Intent).where(
        Intent.valid_until < now,
        Intent.status.in_([IntentStatus.ACTIVE, IntentStatus.PAUSED])
    )
    result = await db.execute(stmt)
    intents = result.scalars().all()
    for intent in intents:
        intent.status = IntentStatus.EXPIRED
        intent.updated_at = now
        await _log_intent_activity(db, intent.id, intent.workspace_id, "INTENT_EXPIRED")
    await db.commit()
    return len(intents)
