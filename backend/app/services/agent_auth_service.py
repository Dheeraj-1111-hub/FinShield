from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import logging

from app.models.agent import AgentCredential, Agent, AgentStatus
from app.core.security import verify_password

logger = logging.getLogger(__name__)

async def validate_agent_token(db: AsyncSession, token: str) -> AgentCredential:
    """
    Validates an agent token formatted as 'client_id:client_secret'.
    """
    if ":" not in token:
        raise HTTPException(status_code=401, detail="Invalid agent credential format. Expected client_id:client_secret")
        
    client_id, client_secret = token.split(":", 1)
    
    stmt = select(AgentCredential).options(joinedload(AgentCredential.agent)).where(AgentCredential.client_id == client_id)
    result = await db.execute(stmt)
    cred = result.scalar_one_or_none()
    
    if not cred:
        raise HTTPException(status_code=401, detail="Invalid agent credential")
        
    if not verify_password(client_secret, cred.client_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid agent credential")
        
    if cred.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Agent credential is not active")
        
    if cred.agent.status != AgentStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Agent is not active")
        
    return cred
