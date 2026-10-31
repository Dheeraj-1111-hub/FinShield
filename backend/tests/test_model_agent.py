import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserStatus
from app.models.workspace import Workspace
from app.models.agent import Agent, AgentType, AgentStatus

@pytest.mark.asyncio
async def test_agent_model_insertion(db_session: AsyncSession):
    # Create User
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email="test_agent_creator@example.com",
        password_hash="fake_hash",
        full_name="Agent Creator",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    # Create Workspace
    ws_id = str(uuid.uuid4())
    ws = Workspace(
        id=ws_id,
        name="Test Agent Workspace",
        slug="test-agent-ws",
        owner_id=user_id,
        environment="sandbox"
    )
    db_session.add(ws)
    await db_session.flush()

    # Create Agent
    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id,
        workspace_id=ws_id,
        name="Test Shopping Agent",
        description="A test agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.DRAFT,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART"],
        max_transaction_amount=5000,
        currency="USD",
        created_by=user_id
    )
    db_session.add(agent)
    await db_session.commit()

    # Query back
    result = await db_session.execute(select(Agent).where(Agent.id == agent_id))
    fetched_agent = result.scalar_one_or_none()
    
    assert fetched_agent is not None
    assert fetched_agent.name == "Test Shopping Agent"
    assert fetched_agent.type == AgentType.SHOPPING
    assert fetched_agent.status == AgentStatus.DRAFT
    assert "SEARCH_PRODUCTS" in fetched_agent.capabilities
    assert fetched_agent.max_transaction_amount == 5000
