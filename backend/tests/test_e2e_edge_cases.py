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
        "full_name": "E2E User Edge Cases"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}

@pytest.mark.asyncio
async def test_payment_failure_journey(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.18 - Payment failure journey
    """
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]

    # 1. Setup agent
    agent_res = await client.post("/api/v1/agents", json={
        "name": "Edge Case Agent",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    assert agent_res.status_code == 201
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    # 2. Setup authority large enough to pass Gate
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
        "monetary_limit": 200000,
        "currency": "USD",
    }, cookies=cookies, headers=headers)
    assert auth_res.status_code == 201
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)

    # 3. Create run
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Buy a failing item",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # 4. Trigger failure amount (from SandboxPaymentProcessor: 1000.00 = 100000 cents)
    action_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 100000,
            "currency": "USD",
            "order_id": "ord_fail_1"
        }
    }, cookies=cookies, headers=headers)
    
    # 5. Verify failure propagates
    # The action should fail because payment failed and throw 400
    assert action_res.status_code == 400
    action_data = action_res.json()
    error_msg = action_data["error"]["message"].lower()
    assert "processor" in error_msg or "fail" in error_msg or "decline" in error_msg

@pytest.mark.asyncio
async def test_approval_replay_journey(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.21 - Approval replay journey
    """
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]

    # Setup agent and authority
    agent_res = await client.post("/api/v1/agents", json={
        "name": "Edge Case Agent 2",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    # Authority of 50000, Policy REVIEW at > 10000
    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
        "monetary_limit": 50000,
        "approval_threshold": 10000,
        "currency": "USD",
    }, cookies=cookies, headers=headers)
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)

    policy_res = await client.post("/api/v1/policies", json={
        "name": "Review over 100",
        "policy_type": "TRANSACTION_LIMIT",
        "actions": {"action": "REVIEW"},
        "conditions": {"max_amount": 10000}
    }, cookies=cookies, headers=headers)
    policy_id = policy_res.json()["id"]
    await client.post(f"/api/v1/policies/{policy_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    # Run
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Buy a laptop for 200",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    run_id = run_res.json()["id"]

    # Action (Amount 20000 -> requires review)
    action_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 20000,
            "currency": "USD",
            "order_id": "ord_review_1"
        }
    }, cookies=cookies, headers=headers)
    
    assert action_res.status_code == 402
    msg = action_res.json()["error"]["message"]
    # msg: "Action requires human approval. Approval ID: xyz"
    approval_id = msg.split("Approval ID: ")[1].strip()

    # Approve
    app_res = await client.post(f"/api/v1/approvals/{approval_id}/decision", json={"decision": "APPROVED"}, cookies=cookies, headers=headers)
    assert app_res.status_code == 200

    # Retry Action (Success)
    action_res_2 = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 20000,
            "currency": "USD",
            "order_id": "ord_review_1"
        }
    }, cookies=cookies, headers=headers)
    assert action_res_2.status_code == 200
    assert action_res_2.json()["status"] == "SUCCESS"

    # Attempt replay with different amount (should fail with 402 because approval is stale/different)
    action_res_replay = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {
            "amount": 25000,
            "currency": "USD",
            "order_id": "ord_review_1"
        }
    }, cookies=cookies, headers=headers)
    assert action_res_replay.status_code == 402

@pytest.mark.asyncio
async def test_duplicate_transaction_journey(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.20 - Duplicate transaction journey
    """
    ctx = e2e_context
    cookies = ctx["cookies"]
    headers = ctx["headers"]

    # Setup agent and authority
    agent_res = await client.post("/api/v1/agents", json={
        "name": "Edge Case Agent 3",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
    }, cookies=cookies, headers=headers)
    agent_id = agent_res.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, cookies=cookies, headers=headers)

    auth_res = await client.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"],
        "monetary_limit": 50000,
        "currency": "USD",
    }, cookies=cookies, headers=headers)
    auth_id = auth_res.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", cookies=cookies, headers=headers)

    # Run
    run_res = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id,
        "input": "Buy a laptop",
        "authority_id": auth_id
    }, cookies=cookies, headers=headers)
    run_id = run_res.json()["id"]

    # Send 3 requests sequentially to avoid SQLite db locking issues during tests, 
    # but ensure they have the same idempotency logic under the hood.
    # The first should succeed (or be queued), subsequent should fail with idempotency error.
    payload = {
        "tool_name": "pay_order",
        "input": {
            "amount": 5000,
            "currency": "USD",
            "order_id": "ord_dup_1"
        }
    }
    
    responses = []
    for _ in range(3):
        res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json=payload, cookies=cookies, headers=headers)
        responses.append(res)
    
    successes = 0
    errors = 0
    for r in responses:
        if r.status_code == 200 and r.json().get("status") == "SUCCESS":
            successes += 1
        elif r.status_code == 400 or r.status_code == 409: # Bad request / Conflict (Idempotency)
            errors += 1
            
    # Depending on idempotency implementation, either 1 succeeds and 2 fail, 
    # or all return the same successful response. Let's just check that we 
    # don't get multiple logical payments.
    assert successes >= 1
    
    # Check payments
    payments_res = await client.get("/api/v1/payments", cookies=cookies, headers=headers)
    assert payments_res.status_code == 200
    
    # We should only have 1 payment created for this run
    run_payments = [p for p in payments_res.json() if p.get("agent_id") == agent_id]
    assert len(run_payments) == 1
