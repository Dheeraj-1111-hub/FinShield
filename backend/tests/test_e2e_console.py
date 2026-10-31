import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.agent import Agent
from tests.test_api_workspaces import create_test_user_and_workspace
from app.models.workspace import WorkspaceRole
import uuid

@pytest.fixture
async def console_client(client: AsyncClient, db_session: AsyncSession):
    import uuid
    email = f"e2e_console_{uuid.uuid4().hex[:8]}@test.com"
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, email, WorkspaceRole.OWNER)
    client.cookies.set("finshield_session", token)
    return client, ws_id

async def setup_agent_and_auth(db: AsyncSession, ws_id: str):
    from app.models.agent import Agent, AgentStatus, AgentType
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    
    agent = Agent(
        id=f"ag_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        name="Test Agent",
        type=AgentType.CUSTOM,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        status=AgentStatus.ACTIVE
    )
    db.add(agent)
    
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        title="Laptop Purchase",
        natural_language_request="Buy a laptop for work",
        structured_constraints={
            "product": {"category": "Hardware", "keywords": ["laptop"]},
            "amount": {"maximum": 80000, "currency": "INR"},
            "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_TO_CART", "CHECKOUT", "PAY_ORDER"]
        },
        status=IntentStatus.ACTIVE
    )
    db.add(intent)
    
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=80000,
        currency="INR",
        approval_threshold=50000,
        status=AuthorityStatus.ACTIVE
    )
    db.add(authority)
    from app.models.commerce import Merchant, Product
    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        name="Test Merchant"
    )
    db.add(merchant)
    
    product = Product(
        id=f"prod_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        name="Test Laptop",
        description="A good laptop",
        price=15000,
        currency="INR",
        inventory=10,
        category="laptop"
    )
    db.add(product)
    
    await db.commit()
    await db.refresh(agent)
    await db.refresh(authority)
    
    return agent, intent, authority

@pytest.mark.asyncio
async def test_console_search_only(console_client, db_session: AsyncSession):
    client, ws_id = console_client
    agent, intent, auth = await setup_agent_and_auth(db_session, ws_id)
    
    # 1. Start a Run
    req = {
        "agent_id": agent.id,
        "input": "Find me a laptop under ₹20,000"
    }
    # Create the run (same endpoint frontend uses)
    res = await client.post("/api/v1/agent-runtime/runs", json=req)
    assert res.status_code == 200, res.text
    run_data = res.json()
    run_id = run_data["id"]
    
    # Run polling loop
    status = run_data["status"]
    for _ in range(60):
        if status not in ["RUNNING", "PENDING"]:
            break
        await asyncio.sleep(0.5)
        res = await client.get(f"/api/v1/agent-runtime/runs/{run_id}")
        assert res.status_code == 200
        run_data = res.json()
        status = run_data["status"]
        
    assert status in ["COMPLETED", "BLOCKED"]
    
    actions = run_data.get("actions", [])
    assert len(actions) > 0
    # Search products should be executed, no purchase actions
    for action in actions:
        if action["status"] in ["SUCCESS", "COMPLETED"]:
            assert action["tool_name"] in ["search_products", "list_products", "get_product"]
        
    # Check that NO gate decision was needed to be an ALLOW or at least no financial action was triggered
    # The absence of GateDecision should be verified by ensuring no BLOCK on safe tools.
