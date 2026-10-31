import pytest
import uuid
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app

@pytest.fixture
async def e2e_context(client: AsyncClient, db_session: AsyncSession):
    email = f"e2e_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "E2E User"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}

@pytest.mark.asyncio
async def test_journey_1_legitimate_purchase(client: AsyncClient, db_session: AsyncSession, e2e_context):
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]
    ws_id = ctx["ws_id"]
    
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E Shopping Assistant",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        "max_transaction_amount": 500000,
        "currency": "USD"
    }, cookies=cookies, headers=headers)
    assert agent_res.status_code == 201, agent_res.text
    agent_id = agent_res.json()["id"]
    
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    intent_res = await client.post("/api/v1/intents", json={
        "title": "Buy a Laptop",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy a high-end laptop for work",
        "structured_constraints": {
            "amount": {"maximum": 250000, "currency": "USD"},
            "product": {"category": "electronics"}
        }
    }, cookies=cookies, headers=headers)
    assert intent_res.status_code == 201, intent_res.text
    intent_id = intent_res.json()["id"]
    await client.post(f"/api/v1/intents/{intent_id}/confirm", cookies=cookies, headers=headers)

    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        "monetary_limit": 300000,
        "currency": "USD",
        "approval_threshold": 200000
    }, cookies=cookies, headers=headers)
    assert auth_res.status_code == 201, auth_res.text
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)
    
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Buy a macbook pro",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]
    
    pay_action_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 150000, "currency": "USD", "order_id": "ord_123"}
    }, cookies=cookies, headers=headers)
    assert pay_action_res.status_code == 200, pay_action_res.text
    assert pay_action_res.json()["status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_journey_2_and_3_gate_review(client: AsyncClient, db_session: AsyncSession, e2e_context):
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]
    
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E High Value Agent",
        "type": "FINANCE",
        "capabilities": ["PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)
    
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["PAY_ORDER"],
        "monetary_limit": 1000000,
        "currency": "USD",
        "approval_threshold": 50000
    }, cookies=cookies, headers=headers)
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)
    
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Make a payment of 60k",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    run_id = run_res.json()["id"]
    
    pay_action_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 60000, "currency": "USD", "order_id": "ord_456"}
    }, cookies=cookies, headers=headers)
    
    assert pay_action_res.status_code == 402, pay_action_res.text
    message = pay_action_res.json()["error"]["message"]
    assert "Approval ID: " in message
    approval_id = message.split("Approval ID: ")[1].strip()
    
    appr_res = await client.post(f"/api/v1/approvals/{approval_id}/decision", json={
        "decision": "APPROVED",
        "reason": "Looks good"
    }, cookies=cookies, headers=headers)
    assert appr_res.status_code == 200
    
    pay_action_retry = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 60000, "currency": "USD", "order_id": "ord_456"}
    }, cookies=cookies, headers=headers)
    assert pay_action_retry.status_code == 200
    assert pay_action_retry.json()["status"] == "SUCCESS"

    pay_action_2 = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 70000, "currency": "USD", "order_id": "ord_789"}
    }, cookies=cookies, headers=headers)
    assert pay_action_2.status_code == 402
    approval_id_2 = pay_action_2.json()["error"]["message"].split("Approval ID: ")[1].strip()
    
    rej_res = await client.post(f"/api/v1/approvals/{approval_id_2}/decision", json={
        "decision": "REJECTED",
        "reason": "Too much"
    }, cookies=cookies, headers=headers)
    assert rej_res.status_code == 200

@pytest.mark.asyncio
async def test_journey_4_gate_block(client: AsyncClient, db_session: AsyncSession, e2e_context):
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]
    
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E Limited Agent",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)
    
    auth_res2 = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["PAY_ORDER"],
        "monetary_limit": 100,
        "currency": "USD"
    }, cookies=cookies, headers=headers)
    auth_id2 = auth_res2.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id2}/activate", cookies=cookies, headers=headers)
    
    run_res2 = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Make a payment of 500",
        "authority_id": auth_id2
    }, cookies=cookies, headers=headers)
    run_id2 = run_res2.json()["id"]
    
    pay_action_block = await client.post(f"/api/v1/agent-runtime/runs/{run_id2}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 500, "currency": "USD", "order_id": "ord_999"}
    }, cookies=cookies, headers=headers)
    
    assert pay_action_block.status_code == 403
    assert "Action blocked by Action Gate" in pay_action_block.text

@pytest.mark.asyncio
async def test_journey_7_revocation_handling(client: AsyncClient, db_session: AsyncSession, e2e_context):
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]
    
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E Revoked Agent",
        "type": "FINANCE",
        "capabilities": ["PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)
    
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["PAY_ORDER"],
        "monetary_limit": 1000
    }, cookies=cookies, headers=headers)
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)
    
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Make a payment",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    run_id = run_res.json()["id"]
    
    await client.post(f"/api/v1/authorities/{auth_id}/revoke", cookies=cookies, headers=headers)
    
    pay_action = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"amount": 50, "currency": "USD", "order_id": "ord_xyz"}
    }, cookies=cookies, headers=headers)
    
    assert pay_action.status_code == 403
    assert "Action blocked by Action Gate" in pay_action.text

@pytest.mark.asyncio
async def test_journey_5_intent_drift(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    Journey 5: Intent Drift
    The agent has a strict intent that blocks a specific merchant.
    When the agent tries to use that merchant, alignment is MISALIGNED,
    and the gate BLOCKS the action — no payment occurs.
    """
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]

    # Create agent with shopping capabilities
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E Drift Agent",
        "type": "SHOPPING",
        "capabilities": ["PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    assert agent_res.status_code == 201, agent_res.text
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    # Create intent with a blocked merchant constraint
    intent_res = await client.post("/api/v1/intents", json={
        "title": "Buy Electronics — Not from FraudMart",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy electronics but never from fraudmart",
        "structured_constraints": {
            "amount": {"maximum": 500000, "currency": "USD"},
            "product": {"category": "electronics"},
            "merchant": {"blocked_merchants": ["fraudmart_001"]}
        }
    }, cookies=cookies, headers=headers)
    assert intent_res.status_code == 201, intent_res.text
    intent_id = intent_res.json()["id"]
    await client.post(f"/api/v1/intents/{intent_id}/confirm", cookies=cookies, headers=headers)

    # Bind authority to the intent
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "intent_id": intent_id,
        "allowed_capabilities": ["PAY_ORDER"],
        "monetary_limit": 500000,
        "currency": "USD",
    }, cookies=cookies, headers=headers)
    assert auth_res.status_code == 201, auth_res.text
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)

    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Buy some headphones",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]

    # Agent drifts: tries to pay a BLOCKED merchant
    drift_action_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 10000,
            "currency": "USD",
            "order_id": "ord_drift",
            "merchant_id": "fraudmart_001"  # Blocked by intent!
        }
    }, cookies=cookies, headers=headers)

    # Must be blocked — not allowed, not a review
    assert drift_action_res.status_code == 403, drift_action_res.text
    assert "Action blocked by Action Gate" in drift_action_res.text


@pytest.mark.asyncio
async def test_journey_6_prompt_injection_tool_poisoning(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    Journey 6: Prompt Injection & Tool Poisoning
    An agent attempts to execute a tool it has no capability for.
    Even if the agent's LLM was told to do this (simulating prompt injection),
    the capability check at the authority/agent layer denies it.
    No payment or privileged action occurs.
    """
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]

    # Create agent with ONLY search capability — no PAY_ORDER
    agent_res = await client.post("/api/v1/agents", json={
        "name": "E2E Read-Only Agent",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS"],  # No PAY_ORDER!
    }, cookies=cookies, headers=headers)
    assert agent_res.status_code == 201, agent_res.text
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    # Grant authority for search only
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],  # PAY_ORDER not allowed
        "monetary_limit": 0,
        "currency": "USD",
    }, cookies=cookies, headers=headers)
    assert auth_res.status_code == 201, auth_res.text
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)

    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Search for phones",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]

    # Simulate prompt injection: agent tries to execute PAY_ORDER despite no capability
    injection_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 99999,
            "currency": "USD",
            "order_id": "ord_injected"
        }
    }, cookies=cookies, headers=headers)

    # Must be denied — capability check blocks it before any gate or payment logic
    assert injection_res.status_code == 403, injection_res.text
    # Verify it's a capability/authority denial (FORBIDDEN code returned by middleware)
    assert injection_res.json()["error"]["code"] in ("ERROR", "FORBIDDEN")
