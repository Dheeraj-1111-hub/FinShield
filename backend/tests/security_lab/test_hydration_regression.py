import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentType, AgentStatus
from app.models.intent import Intent, IntentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.commerce import Merchant, Product, Cart, CartItem, Order, OrderStatus
from tests.test_api_workspaces import create_test_user_and_workspace
from app.models.workspace import WorkspaceRole
from app.services.agent_service import create_agent_credential
from app.schemas.agent import AgentCredentialCreate


@pytest.fixture
async def hydration_env(client: AsyncClient, db_session: AsyncSession):
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, f"hydr_{uuid.uuid4().hex}@test.com", WorkspaceRole.OWNER)
    
    agent_id = f"agt_{uuid.uuid4().hex}"
    agent = Agent(
        id=agent_id, 
        workspace_id=ws_id, 
        name="Hydration Agent", 
        type=AgentType.SHOPPING, 
        status=AgentStatus.ACTIVE,
        capabilities=["CREATE_ORDER", "PAY_ORDER", "CREATE_CART", "MANAGE_CART"]
    )
    db_session.add(agent)
    
    # Intent with a category constraint "laptop"
    intent_id = f"int_{uuid.uuid4().hex}"
    intent = Intent(
        id=intent_id,
        workspace_id=ws_id,
        agent_id=agent_id,
        status=IntentStatus.ACTIVE,
        intent_type="PURCHASE",
        title="Buy a laptop",
        natural_language_request="Buy a laptop under 1 lakh",
        structured_constraints={
            "product": {"category": "laptop"},
            "amount": {"maximum": 100000}
        }
    )
    db_session.add(intent)
    
    auth_id = f"auth_{uuid.uuid4().hex}"
    auth = DelegatedAuthority(
        id=auth_id,
        workspace_id=ws_id,
        intent_id=intent_id,
        agent_id=agent_id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=100000,
        allowed_capabilities=["CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(auth)
    await db_session.flush()

    cred, secret = await create_agent_credential(db_session, ws_id, agent_id, user_id, AgentCredentialCreate(name="Test Key"))
    agent_token = f"Bearer {cred.client_id}:{secret}"

    merchant_id = f"mer_{uuid.uuid4().hex}"
    merchant = Merchant(id=merchant_id, workspace_id=ws_id, name="Test Merchant")
    db_session.add(merchant)
    
    product_laptop = Product(
        id=f"prd_{uuid.uuid4().hex}_lap", merchant_id=merchant_id, name="Work Laptop", category="laptop", price=50000, currency="USD", inventory=10
    )
    product_gaming = Product(
        id=f"prd_{uuid.uuid4().hex}_gam", merchant_id=merchant_id, name="Gaming Laptop", category="gaming-laptop", price=65000, currency="USD", inventory=10
    )
    db_session.add_all([product_laptop, product_gaming])
    
    # Cart for legitimate laptop
    cart_laptop = Cart(id=f"crt_{uuid.uuid4().hex}_lap", workspace_id=ws_id, agent_id=agent_id, currency="USD")
    db_session.add(cart_laptop)
    await db_session.flush()
    cart_item_laptop = CartItem(id=f"cti_{uuid.uuid4().hex}_lap", cart_id=cart_laptop.id, product_id=product_laptop.id, quantity=1)
    db_session.add(cart_item_laptop)

    # Cart for gaming laptop (semantic drift)
    cart_gaming = Cart(id=f"crt_{uuid.uuid4().hex}_gam", workspace_id=ws_id, agent_id=agent_id, currency="USD")
    db_session.add(cart_gaming)
    await db_session.flush()
    cart_item_gaming = CartItem(id=f"cti_{uuid.uuid4().hex}_gam", cart_id=cart_gaming.id, product_id=product_gaming.id, quantity=1)
    db_session.add(cart_item_gaming)
    
    await db_session.commit()

    return {
        "ws_id": ws_id,
        "agent_id": agent_id,
        "agent_token": agent_token,
        "user_token": f"Bearer {token}",
        "auth_id": auth_id,
        "cart_laptop_id": cart_laptop.id,
        "cart_gaming_id": cart_gaming.id,
    }


async def create_run(client, ws_id, agent_id, token, auth_id):
    res = await client.post("/api/v1/agent-runtime/runs", json={"agent_id": agent_id, "input": "checkout", "authority_id": auth_id}, headers={"Authorization": token})
    assert res.status_code == 200, f"Failed to create run: {res.text}"
    return res.json()["id"]


@pytest.mark.asyncio
async def test_hydration_legitimate_control(client: AsyncClient, hydration_env):
    run_id = await create_run(client, hydration_env["ws_id"], hydration_env["agent_id"], hydration_env["user_token"], hydration_env["auth_id"])
    payload = {
        "tool_name": "checkout",
        "input": {
            "cart_id": hydration_env["cart_laptop_id"]
        }
    }
    
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json=payload,
        headers={"Authorization": hydration_env["agent_token"]}
    )
    assert response.status_code == 200, f"Expected ALLOW, got {response.status_code}: {response.text}"
    # Wait, the action execution returns AgentActionResponse. The actual order_id is in `result`.
    # Actually wait: The Action Gate might block or allow. If it allows, it returns the tool result.
    assert response.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_hydration_fake_category_override(client: AsyncClient, hydration_env):
    run_id = await create_run(client, hydration_env["ws_id"], hydration_env["agent_id"], hydration_env["user_token"], hydration_env["auth_id"])
    payload = {
        "tool_name": "checkout",
        "input": {
            "cart_id": hydration_env["cart_gaming_id"],
            "category": "laptop"  # Spoofing
        }
    }
    
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json=payload,
        headers={"Authorization": hydration_env["agent_token"]}
    )
    
    assert response.status_code == 403, f"Expected BLOCK, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_hydration_missing_category_fail_closed(client: AsyncClient, hydration_env):
    run_id = await create_run(client, hydration_env["ws_id"], hydration_env["agent_id"], hydration_env["user_token"], hydration_env["auth_id"])
    payload = {
        "tool_name": "checkout",
        "input": {
            "cart_id": hydration_env["cart_gaming_id"]
        }
    }
    
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json=payload,
        headers={"Authorization": hydration_env["agent_token"]}
    )
    
    assert response.status_code == 403, f"Expected BLOCK, got {response.status_code}: {response.text}"
