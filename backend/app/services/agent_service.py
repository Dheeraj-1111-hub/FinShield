import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.agent import Agent, AgentStatus, AgentType
from app.schemas.agent import AgentCreate, AgentUpdate
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService

async def create_agent(db: AsyncSession, workspace_id: str, user_id: str, data: AgentCreate) -> Agent:
    agent_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        type=data.type,
        status=AgentStatus.DRAFT,
        capabilities=data.capabilities,
        max_transaction_amount=data.max_transaction_amount,
        monthly_limit=data.monthly_limit,
        daily_limit=data.daily_limit,
        approval_threshold=data.approval_threshold,
        currency=data.currency or "INR",
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="AGENT_CREATED",
        event_category=EventCategory.AGENT,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="AGENT",
        entity_id=agent_id,
        payload={
            "name": agent.name,
            "type": agent.type
        }
    )
    
    return agent

async def get_agents(db: AsyncSession, workspace_id: str) -> List[Agent]:
    stmt = select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_agent(db: AsyncSession, workspace_id: str, agent_id: str) -> Agent:
    stmt = select(Agent).where(Agent.workspace_id == workspace_id, Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
        
    return agent

async def update_agent(db: AsyncSession, workspace_id: str, agent_id: str, user_id: str, data: AgentUpdate) -> Agent:
    agent = await get_agent(db, workspace_id, agent_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
        
    agent.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(agent)
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="AGENT_UPDATED",
        event_category=EventCategory.AGENT,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="AGENT",
        entity_id=agent_id,
        payload=update_data
    )
    
    return agent

async def update_agent_status(db: AsyncSession, workspace_id: str, agent_id: str, user_id: str, new_status: AgentStatus) -> Agent:
    agent = await get_agent(db, workspace_id, agent_id)
    
    # Valid transitions
    valid_transitions = {
        AgentStatus.DRAFT: [AgentStatus.ACTIVE],
        AgentStatus.ACTIVE: [AgentStatus.PAUSED, AgentStatus.REVOKED],
        AgentStatus.PAUSED: [AgentStatus.ACTIVE, AgentStatus.REVOKED, AgentStatus.ARCHIVED],
        AgentStatus.REVOKED: [],
        AgentStatus.ARCHIVED: []
    }
    
    if new_status not in valid_transitions.get(agent.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition agent from {agent.status} to {new_status}"
        )
        
    old_status = agent.status
    agent.status = new_status
    agent.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(agent)
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="AGENT_STATUS_CHANGED",
        event_category=EventCategory.AGENT,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="AGENT",
        entity_id=agent_id,
        payload={
            "old_status": old_status,
            "new_status": new_status
        }
    )
    
    return agent

import secrets
from app.models.agent import AgentCredential
from app.core.security import get_password_hash
from app.schemas.agent import AgentCredentialCreate

async def create_agent_credential(db: AsyncSession, workspace_id: str, agent_id: str, user_id: str, data: AgentCredentialCreate):
    agent = await get_agent(db, workspace_id, agent_id)
    
    cred_id = str(uuid.uuid4())
    client_id = f"agt_{secrets.token_hex(12)}"
    client_secret = f"sk_live_{secrets.token_hex(24)}"
    
    cred = AgentCredential(
        id=cred_id,
        agent_id=agent.id,
        name=data.name,
        client_id=client_id,
        client_secret_hash=get_password_hash(client_secret),
        status="ACTIVE",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="AGENT_CREDENTIAL_CREATED",
        event_category=EventCategory.AGENT,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="AGENT",
        entity_id=agent_id,
        payload={
            "credential_id": cred.id,
            "credential_name": cred.name
        }
    )
    
    # Return both the credential object and the raw secret
    return cred, client_secret

async def list_agent_credentials(db: AsyncSession, workspace_id: str, agent_id: str) -> List[AgentCredential]:
    agent = await get_agent(db, workspace_id, agent_id)
    stmt = select(AgentCredential).where(AgentCredential.agent_id == agent.id).order_by(AgentCredential.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def revoke_agent_credential(db: AsyncSession, workspace_id: str, agent_id: str, user_id: str, credential_id: str):
    agent = await get_agent(db, workspace_id, agent_id)
    stmt = select(AgentCredential).where(AgentCredential.id == credential_id, AgentCredential.agent_id == agent.id)
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
        
    cred.status = "REVOKED"
    await db.commit()
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="AGENT_CREDENTIAL_REVOKED",
        event_category=EventCategory.AGENT,
        severity=EventSeverity.WARNING,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="AGENT",
        entity_id=agent_id,
        payload={
            "credential_id": cred.id,
            "credential_name": cred.name
        }
    )
    
    return cred

async def get_agent_activity(db: AsyncSession, workspace_id: str, agent_id: str) -> List[dict]:
    # Ensure agent exists and is accessible
    await get_agent(db, workspace_id, agent_id)
    
    from app.models.audit import AuditEvent
    
    stmt = select(AuditEvent).where(
        AuditEvent.workspace_id == workspace_id,
        AuditEvent.entity_type == "AGENT",
        AuditEvent.entity_id == agent_id
    ).order_by(AuditEvent.created_at.desc())
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    activities = []
    for event in events:
        action = event.event_type.replace("AGENT_", "")
        activities.append({
            "id": event.id,
            "action": action,
            "created_at": event.created_at,
            "details": event.payload
        })
    return activities
