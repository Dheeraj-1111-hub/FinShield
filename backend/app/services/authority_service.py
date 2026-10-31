import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.authority import DelegatedAuthority, AuthorityVersion, AuthorityStatus
from app.models.agent import Agent
from app.models.intent import Intent
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
from app.schemas.authority import AuthorityCreate, AuthorityUpdate


async def _log_authority_activity(
    db: AsyncSession,
    authority_id: str,
    workspace_id: str,
    action: str,
    actor_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=action,
        event_category=EventCategory.AUTHORITY,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
        actor_id=actor_id,
        entity_type="AUTHORITY",
        entity_id=authority_id,
        payload=details or {},
    )


def _make_snapshot(authority: DelegatedAuthority) -> dict:
    return {
        "allowed_capabilities": authority.allowed_capabilities,
        "prohibited_actions": authority.prohibited_actions,
        "monetary_limit": authority.monetary_limit,
        "currency": authority.currency,
        "approval_threshold": authority.approval_threshold,
        "valid_from": authority.valid_from.isoformat() if authority.valid_from else None,
        "valid_until": authority.valid_until.isoformat() if authority.valid_until else None,
    }


async def create_authority(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    data: AuthorityCreate,
) -> DelegatedAuthority:
    # Verify agent belongs to workspace
    agent = await db.get(Agent, data.agent_id)
    if not agent or agent.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Agent not found in this workspace")

    # Optionally verify intent belongs to workspace
    if data.intent_id:
        stmt = select(Intent).where(Intent.id == data.intent_id, Intent.workspace_id == workspace_id)
        result = await db.execute(stmt)
        intent = result.scalar_one_or_none()
        if not intent:
            raise HTTPException(status_code=404, detail="Intent not found in this workspace")

    authority = DelegatedAuthority(
        workspace_id=workspace_id,
        intent_id=data.intent_id,
        agent_id=data.agent_id,
        status=AuthorityStatus.DRAFT,
        allowed_capabilities=data.allowed_capabilities,
        prohibited_actions=data.prohibited_actions,
        monetary_limit=data.monetary_limit,
        currency=data.currency,
        approval_threshold=data.approval_threshold,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        version=1,
        created_by=user_id,
    )
    db.add(authority)
    await db.flush()

    version = AuthorityVersion(
        authority_id=authority.id,
        version_number=1,
        snapshot=_make_snapshot(authority),
        created_by=user_id,
    )
    db.add(version)

    await _log_authority_activity(db, authority.id, workspace_id, "AUTHORITY_CREATED",
                                  actor_id=user_id, details={"version": 1})
    await db.commit()
    return await get_authority(db, workspace_id, authority.id)


async def get_authority(
    db: AsyncSession,
    workspace_id: str,
    authority_id: str,
) -> DelegatedAuthority:
    stmt = (
        select(DelegatedAuthority)
        .options(selectinload(DelegatedAuthority.versions))
        .where(
            DelegatedAuthority.id == authority_id,
            DelegatedAuthority.workspace_id == workspace_id,
        )
    )
    result = await db.execute(stmt)
    authority = result.scalar_one_or_none()
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    return authority


async def list_authorities(
    db: AsyncSession,
    workspace_id: str,
    agent_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    status: Optional[AuthorityStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DelegatedAuthority]:
    stmt = (
        select(DelegatedAuthority)
        .where(DelegatedAuthority.workspace_id == workspace_id)
        .order_by(DelegatedAuthority.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if agent_id:
        stmt = stmt.where(DelegatedAuthority.agent_id == agent_id)
    if intent_id:
        stmt = stmt.where(DelegatedAuthority.intent_id == intent_id)
    if status:
        stmt = stmt.where(DelegatedAuthority.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_authority(
    db: AsyncSession,
    workspace_id: str,
    authority_id: str,
    user_id: str,
    data: AuthorityUpdate,
) -> DelegatedAuthority:
    authority = await get_authority(db, workspace_id, authority_id)
    if authority.status in [AuthorityStatus.REVOKED, AuthorityStatus.EXPIRED]:
        raise HTTPException(status_code=400, detail=f"Cannot update a {authority.status.value} authority")

    if data.allowed_capabilities is not None:
        authority.allowed_capabilities = data.allowed_capabilities
    if data.prohibited_actions is not None:
        authority.prohibited_actions = data.prohibited_actions
    if data.monetary_limit is not None:
        authority.monetary_limit = data.monetary_limit
    if data.currency is not None:
        authority.currency = data.currency
    if data.approval_threshold is not None:
        authority.approval_threshold = data.approval_threshold
    if data.valid_from is not None:
        authority.valid_from = data.valid_from
    if data.valid_until is not None:
        authority.valid_until = data.valid_until

    authority.version += 1
    authority.updated_at = datetime.now(timezone.utc)

    version = AuthorityVersion(
        authority_id=authority.id,
        version_number=authority.version,
        snapshot=_make_snapshot(authority),
        created_by=user_id,
    )
    db.add(version)

    await _log_authority_activity(db, authority.id, workspace_id, "AUTHORITY_UPDATED",
                                  actor_id=user_id, details={"new_version": authority.version})
    await _log_authority_activity(db, authority.id, workspace_id, "AUTHORITY_VERSION_CREATED",
                                  actor_id=user_id, details={"version": authority.version})
    await db.commit()
    return await get_authority(db, workspace_id, authority_id)


async def activate_authority(
    db: AsyncSession,
    workspace_id: str,
    authority_id: str,
    user_id: str,
) -> DelegatedAuthority:
    authority = await get_authority(db, workspace_id, authority_id)
    if authority.status != AuthorityStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT authorities can be activated")
    authority.status = AuthorityStatus.ACTIVE
    authority.updated_at = datetime.now(timezone.utc)
    await _log_authority_activity(db, authority.id, workspace_id, "AUTHORITY_UPDATED",
                                  actor_id=user_id, details={"status": "ACTIVE"})
    await db.commit()
    return await get_authority(db, workspace_id, authority_id)


async def revoke_authority(
    db: AsyncSession,
    workspace_id: str,
    authority_id: str,
    user_id: str,
) -> DelegatedAuthority:
    authority = await get_authority(db, workspace_id, authority_id)
    if authority.status == AuthorityStatus.REVOKED:
        raise HTTPException(status_code=400, detail="Authority is already revoked")
    authority.status = AuthorityStatus.REVOKED
    authority.updated_at = datetime.now(timezone.utc)
    await _log_authority_activity(db, authority.id, workspace_id, "AUTHORITY_REVOKED",
                                  actor_id=user_id)
    await db.commit()
    return await get_authority(db, workspace_id, authority_id)


async def list_authority_versions(
    db: AsyncSession,
    workspace_id: str,
    authority_id: str,
) -> List[AuthorityVersion]:
    await get_authority(db, workspace_id, authority_id)
    stmt = (
        select(AuthorityVersion)
        .where(AuthorityVersion.authority_id == authority_id)
        .order_by(AuthorityVersion.version_number.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_authority_for_agent(
    db: AsyncSession,
    workspace_id: str,
    agent_id: str,
    authority_id: Optional[str] = None,
) -> Optional[DelegatedAuthority]:
    """Fetch the active authority for an agent, optionally by ID."""
    stmt = (
        select(DelegatedAuthority)
        .where(
            DelegatedAuthority.workspace_id == workspace_id,
            DelegatedAuthority.agent_id == agent_id,
            DelegatedAuthority.status == AuthorityStatus.ACTIVE,
        )
    )
    if authority_id:
        stmt = stmt.where(DelegatedAuthority.id == authority_id)
    result = await db.execute(stmt)
    return result.scalars().first()
