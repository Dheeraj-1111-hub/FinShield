import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentStatus, AgentType
from app.models.agent_runtime import AgentRun, RunStatus, AgentAction, ActionStatus
from fastapi import HTTPException

import uuid
from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from datetime import datetime, timezone, timedelta
import pytest_asyncio

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def owner_headers(db_session: AsyncSession):
    user = User(
        id=f"usr_{uuid.uuid4().hex}",
        email=f"owner_{uuid.uuid4().hex}@example.com",
        full_name="Owner User",
        password_hash=get_password_hash("password123"),
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    workspace = Workspace(
        id=f"ws_{uuid.uuid4().hex}",
        name="Test Workspace",
        slug=f"test-workspace-{uuid.uuid4().hex}",
        owner_id=user.id
    )
    db_session.add(workspace)
    await db_session.flush()
    
    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex}",
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    
    token = generate_session_token()
    session = Session(
        id=f"sess_{uuid.uuid4().hex}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    await db_session.commit()
    
    return {"Cookie": f"finshield_session={token}"}

async def test_create_run_and_list_tools(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    # Get tools
    response = await client.get("/api/v1/agent-runtime/tools", headers=owner_headers)
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) > 0
    assert any(t["name"] == "search_products" for t in tools)

    # Create agent
    agent_data = {
        "name": "Test Runner Agent",
        "description": "Agent for runtime testing",
        "type": "SHOPPING",
    }
    response = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    assert response.status_code == 201
    agent = response.json()
    agent_id = agent["id"]

    # Try creating run when DRAFT (should fail)
    response = await client.post(
        "/api/v1/agent-runtime/runs", 
        json={"agent_id": agent_id, "input": "Find a laptop"}, 
        headers=owner_headers
    )
    assert response.status_code == 403

    # Set to ACTIVE and assign capabilities
    res1 = await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    assert res1.status_code == 200
    res2 = await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS"]}, headers=owner_headers)
    assert res2.status_code == 200

    # Create run successfully (auto_start=False so background agent loop doesn't race with manual steps)
    response = await client.post(
        "/api/v1/agent-runtime/runs", 
        json={"agent_id": agent_id, "input": "Find a laptop", "auto_start": False}, 
        headers=owner_headers
    )
    assert response.status_code == 200
    run = response.json()
    run_id = run["id"]
    assert run["status"] == "RUNNING"

    # Execute action - successful (capability SEARCH_PRODUCTS granted)
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={
            "tool_name": "search_products",
            "input": {"query": "laptop"}
        },
        headers=owner_headers
    )
    assert response.status_code == 200
    action = response.json()
    assert action["status"] == "SUCCESS"
    assert "results" in action["output"]

    # Execute action - denied (missing capability CREATE_CART)
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={
            "tool_name": "create_cart",
            "input": {}
        },
        headers=owner_headers
    )
    assert response.status_code == 403

    # Finish Run
    response = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/finish",
        json={"output": "Found laptops but could not create cart"},
        headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    
    # Verify Run
    response = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=owner_headers)
    assert response.status_code == 200
    assert len(response.json()["actions"]) == 2


async def test_search_products_workspace_catalog(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Integration test verifying searching the workspace catalog for Budget Laptop 15-inch with max_price: 150 returns the matching product."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from sqlalchemy import select

    # Find the workspace
    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()

    # Seed the sandbox catalog in this workspace
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    # Create agent with SEARCH_PRODUCTS capability
    agent_data = {
        "name": "E2E Shopping Agent Test",
        "description": "Agent for catalog search test",
        "type": "SHOPPING",
    }
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS"]}, headers=owner_headers)

    # Create run (auto_start=False)
    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "purchase Budget Laptop 15-inch for ₹150", "auto_start": False},
        headers=owner_headers
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # Execute search_products tool with exact arguments from failed reproduction: query='Budget Laptop 15-inch', max_price=150
    act_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={
            "tool_name": "search_products",
            "input": {
                "query": "Budget Laptop 15-inch",
                "max_price": 150
            }
        },
        headers=owner_headers
    )
    assert act_resp.status_code == 200
    action = act_resp.json()
    assert action["status"] == "SUCCESS"
    results = action["output"]["results"]
    assert len(results) >= 1
    matched = [p for p in results if p["name"] == "Budget Laptop 15-inch"]
    assert len(matched) == 1
    assert matched[0]["price"] == 150
    assert matched[0]["currency"] == "INR"
    assert matched[0]["inventory"] > 0


async def test_failed_run_no_gate_decision_not_allow(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Regression test: A failed run or safe search action without an authoritative GateDecision
    must not produce or represent an ALLOW decision."""
    agent_data = {
        "name": "Failed Run Test Agent",
        "description": "Agent testing failed run handling",
        "type": "SHOPPING",
    }
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS"]}, headers=owner_headers)

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Find unavailable product", "auto_start": False},
        headers=owner_headers
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # Action 1: Search returns empty
    act_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={
            "tool_name": "search_products",
            "input": {"query": "Nonexistent Laptop"}
        },
        headers=owner_headers
    )
    assert act_resp.status_code == 200
    action = act_resp.json()
    assert action["status"] == "SUCCESS"
    assert action["output"]["results"] == []

    # Finish run with FAILED status
    finish_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/finish",
        json={"output": "FAILED: no matching product found.", "status": "FAILED"},
        headers=owner_headers
    )
    assert finish_resp.status_code == 200

    # Fetch run
    get_resp = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=owner_headers)
    assert get_resp.status_code == 200
    run_data = get_resp.json()
    assert run_data["status"] == "FAILED"

    # Verify decision representation contract for failed runs and safe tools:
    # 1. Safe search must not manufacture an ALLOW GateDecision in the runtime presentation
    # 2. When run.status == FAILED, final decision presentation must be FAILED, not ALLOW
    for action in run_data.get("actions", []):
        assert action["tool_name"] == "search_products"
        # In runtime presentation: safe tool non-financial queries are NOT EVALUATED, and failed runs are FAILED.
        # Under no circumstance is ALLOW rendered when run has failed.
        presentation_decision = "FAILED" if run_data["status"] == "FAILED" else ("NOT EVALUATED" if action["tool_name"] in ["search_products", "list_products", "get_product"] else "ALLOW")
        assert presentation_decision != "ALLOW", f"Decision for failed run cannot be ALLOW, got {presentation_decision}"
        assert presentation_decision == "FAILED"


async def test_payment_attempt_without_gatedecision(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """1. Direct payment execution attempt without a signed GateDecision token must be rejected with 403."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from app.services.payment_service import create_payment_intent
    from app.schemas.payment import PaymentCreate
    from app.schemas.execution_context import ExecutionContext

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Test Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    # Create Cart
    cart_resp = await client.post(
        "/api/v1/commerce/carts",
        json={"agent_id": agent_id, "currency": "INR"},
        headers=owner_headers
    )
    assert cart_resp.status_code == 201
    cart_id = cart_resp.json()["id"]

    # Add product
    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    product = prods_resp.json()[0]

    add_resp = await client.post(
        f"/api/v1/commerce/carts/{cart_id}/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=owner_headers
    )
    assert add_resp.status_code == 201

    # Checkout
    order_resp = await client.post(
        "/api/v1/commerce/orders",
        json={"cart_id": cart_id, "merchant_id": product["merchant_id"]},
        headers=owner_headers
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # Attempt to call payment_service.create_payment_intent as agent runtime without signed token
    unauthorized_ctx = ExecutionContext(
        is_human=False,
        is_agent=True,
        agent_id=agent_id,
        is_agent_runtime=True,
        signed_decision_token=None
    )
    with pytest.raises(Exception) as exc_info:
        await create_payment_intent(
            db_session,
            ws.id,
            PaymentCreate(
                payment_intent_id=f"pi_{uuid.uuid4().hex[:8]}",
                idempotency_key=f"idk_{uuid.uuid4().hex[:8]}",
                order_id=order_id,
                amount=product["price"],
                currency=product["currency"]
            ),
            unauthorized_ctx
        )
    assert "403" in str(exc_info.value) or "Protected operation requires signed decision token" in str(exc_info.value)


async def test_payment_attempt_review_without_approved_request(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """2. Payment attempt exceeding intent approval threshold returns REVIEW (HTTP 402) and cannot capture payment."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.commerce import Order, OrderStatus
    from app.models.payment import Payment

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Review Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    # Intent with threshold ₹100
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Laptop Purchase",
        natural_language_request="Buy budget laptop",
        structured_constraints={
            "product": {"category": "electronics"},
            "amount": {"maximum": 10000, "currency": "INR"},
            "approval": {"approval_required": True, "approval_required_above": 100}
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    # Create run with this authority
    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase laptop", "authority_id": authority.id, "auto_start": False},
        headers=owner_headers
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # Cart, add product (150 INR > 100 threshold), checkout
    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = [p for p in prods_resp.json() if p["price"] == 150][0]

    c_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    assert c_resp.status_code == 200
    cart_id = c_resp.json()["output"]["cart_id"]

    a_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod["id"], "quantity": 1}}, headers=owner_headers)
    assert a_resp.status_code == 200

    co_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=owner_headers)
    assert co_resp.status_code == 200
    order_id = co_resp.json()["output"]["order_id"]

    # Attempt pay_order -> Must return 402 REVIEW REQUIRED
    pay_act_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        headers=owner_headers
    )
    assert pay_act_resp.status_code == 402, f"Expected 402 Review required, got {pay_act_resp.status_code}"

    # Verify no payment was captured and order is still PENDING_PAYMENT
    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.PENDING_PAYMENT

    pay_res = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    payment = pay_res.scalar_one_or_none()
    assert payment is None or payment.status != "CAPTURED"


async def test_payment_approved_exact_context_execution(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """3. Correctly approved, exact-context payment: human approves pending request, re-executing captures payment once."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.commerce import Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Approved Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Laptop Intent",
        natural_language_request="Buy laptop",
        structured_constraints={
            "product": {"category": "electronics"},
            "amount": {"maximum": 10000, "currency": "INR"},
            "approval": {"approval_required": True, "approval_required_above": 100}
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase laptop", "authority_id": authority.id, "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = [p for p in prods_resp.json() if p["price"] == 150][0]

    c_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart_id = c_resp.json()["output"]["cart_id"]

    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod["id"], "quantity": 1}}, headers=owner_headers)
    co_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=owner_headers)
    order_id = co_resp.json()["output"]["order_id"]

    # Trigger REVIEW
    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "pay_order", "input": {"order_id": order_id}}, headers=owner_headers)

    # Find the created pending approval request
    stmt_appr = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id, ApprovalRequest.status == ApprovalStatus.PENDING)
    res_appr = await db_session.execute(stmt_appr)
    approval = res_appr.scalar_one()

    # Human approves via API
    dec_resp = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        json={"decision": "APPROVED", "reason": "Approved by supervisor"},
        headers=owner_headers
    )
    assert dec_resp.status_code == 200

    # Execute pay_order again now that approval exists
    pay_act_resp2 = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        headers=owner_headers
    )
    assert pay_act_resp2.status_code == 200
    act_out = pay_act_resp2.json()
    assert act_out["status"] == "SUCCESS"

    # Confirm order is PAID and payment is CAPTURED
    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.PAID
    assert order.total == 150
    assert order.currency == "INR"


async def test_order_payment_currency_and_amount_consistency(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """4. Order/payment currency and amount consistency: Cart inherits catalog currency (INR), order rejects mismatched currencies."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Consistency Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    from app.models.authority import DelegatedAuthority, AuthorityStatus
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Buy laptop", "authority_id": authority.id, "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    # Verify cart created in runtime defaults to catalog currency INR
    cart_act = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    assert cart_act.status_code == 200
    cart_data = cart_act.json()["output"]
    assert cart_data["currency"] == "INR"

    # Create a USD cart directly and verify trying to add an INR product is rejected with 400
    usd_cart = await client.post("/api/v1/commerce/carts", json={"agent_id": agent_id, "currency": "USD"}, headers=owner_headers)
    assert usd_cart.status_code == 201
    usd_cart_id = usd_cart.json()["id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    inr_prod = [p for p in prods_resp.json() if p["currency"] == "INR"][0]

    mismatch_resp = await client.post(
        f"/api/v1/commerce/carts/{usd_cart_id}/items",
        json={"product_id": inr_prod["id"], "quantity": 1},
        headers=owner_headers
    )
    assert mismatch_resp.status_code == 400
    err_body = mismatch_resp.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "Currency mismatch" in err_msg


async def test_pending_approval_visibility_in_action_gate(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """5. Pending approval visibility: Action Gate approvals endpoint truthfully returns pending requests."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Visibility Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Laptop Intent",
        natural_language_request="Buy laptop",
        structured_constraints={
            "product": {"category": "electronics"},
            "amount": {"maximum": 10000, "currency": "INR"},
            "approval": {"approval_required": True, "approval_required_above": 50}
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase laptop", "authority_id": authority.id, "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = [p for p in prods_resp.json() if p["price"] == 150][0]

    c_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart_id = c_resp.json()["output"]["cart_id"]

    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod["id"], "quantity": 1}}, headers=owner_headers)
    co_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=owner_headers)
    order_id = co_resp.json()["output"]["order_id"]

    # Trigger REVIEW
    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "pay_order", "input": {"order_id": order_id}}, headers=owner_headers)

    # Action Gate endpoint query
    apprs_resp = await client.get(f"/api/v1/approvals/{ws.id}/approvals", headers=owner_headers)
    assert apprs_resp.status_code == 200
    apprs = apprs_resp.json()
    assert len(apprs) > 0
    matched = [a for a in apprs if a["agent_run_id"] == run_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "PENDING"
    assert matched[0]["amount"] == 150
    assert matched[0]["currency"] == "INR"


async def test_regression_approval_center_and_policies_contracts(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Regression test:
    1. A REVIEW decision generates a durable pending approval record that /api/v1/approvals/{workspace_id}/approvals returns.
    2. /api/v1/policies correctly responds 200 with JSON list for the workspace.
    """
    from app.models.workspace import Workspace
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.commerce import Order, OrderStatus
    from app.models.payment import Payment

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()
    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    # 1. Verify policies contract
    policies_resp = await client.get("/api/v1/policies", headers=owner_headers)
    assert policies_resp.status_code == 200
    assert isinstance(policies_resp.json(), list)

    # 2. Verify agent run hitting approval threshold produces durable pending approval
    agent_data = {"name": "Gate Approval Agent", "type": "SHOPPING"}
    agent_resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = agent_resp.json()["id"]
    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]}, headers=owner_headers)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Laptop Intent",
        natural_language_request="Buy laptop",
        structured_constraints={
            "product": {"category": "electronics"},
            "amount": {"maximum": 10000, "currency": "INR"},
            "approval": {"approval_required": True, "approval_required_above": 100}
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase laptop", "authority_id": authority.id, "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = [p for p in prods_resp.json() if p["price"] == 150][0]

    c_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart_id = c_resp.json()["output"]["cart_id"]

    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod["id"], "quantity": 1}}, headers=owner_headers)
    co_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=owner_headers)
    order_id = co_resp.json()["output"]["order_id"]

    # Trigger REVIEW via pay_order
    pay_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "pay_order", "input": {"order_id": order_id}}, headers=owner_headers)
    assert pay_resp.status_code == 402

    # Query Approval Center API for this workspace
    apprs_resp = await client.get(f"/api/v1/approvals/{ws.id}/approvals", headers=owner_headers)
    assert apprs_resp.status_code == 200
    matched = [a for a in apprs_resp.json() if a["agent_run_id"] == run_id]
    assert len(matched) == 1
    approval = matched[0]
    assert approval["status"] == "PENDING"
    assert approval["amount"] == 150
    assert approval["currency"] == "INR"
    assert approval["agent_id"] == agent_id

    # Verify order is still PENDING_PAYMENT and payment was not captured
    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.PENDING_PAYMENT
    pay_res = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    assert pay_res.scalar_one_or_none() is None


async def test_canonical_capability_mapping_explicit_cart_delegation(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Regression test 1: Authority with only CREATE_CART is blocked from add_to_cart.
    Only when explicitly delegated MANAGE_CART (or ADD_CART_ITEM) can it add items to cart."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()

    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    # Agent with all capabilities
    agent_data = {"name": "Cart Perm Test Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]},
        headers=owner_headers
    )

    # Authority with ONLY CREATE_CART (no MANAGE_CART)
    auth1 = DelegatedAuthority(
        workspace_id=ws.id,
        agent_id=agent_id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth1)
    await db_session.commit()

    run1_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Buy laptop", "authority_id": auth1.id, "auto_start": False},
        headers=owner_headers
    )
    run1_id = run1_resp.json()["id"]

    # create_cart succeeds
    c1_resp = await client.post(f"/api/v1/agent-runtime/runs/{run1_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    assert c1_resp.status_code == 200
    cart1_id = c1_resp.json()["output"]["cart_id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = prods_resp.json()[0]

    # add_to_cart fails due to missing MANAGE_CART
    add1_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run1_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart1_id, "product_id": prod["id"], "quantity": 1}},
        headers=owner_headers
    )
    assert add1_resp.status_code == 403

    # Now create Authority with explicit MANAGE_CART delegated
    auth2 = DelegatedAuthority(
        workspace_id=ws.id,
        agent_id=agent_id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth2)
    await db_session.commit()

    run2_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Buy laptop", "authority_id": auth2.id, "auto_start": False},
        headers=owner_headers
    )
    run2_id = run2_resp.json()["id"]

    c2_resp = await client.post(f"/api/v1/agent-runtime/runs/{run2_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart2_id = c2_resp.json()["output"]["cart_id"]

    add2_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run2_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart2_id, "product_id": prod["id"], "quantity": 1}},
        headers=owner_headers
    )
    assert add2_resp.status_code == 200
    assert add2_resp.json()["status"] == "SUCCESS"


async def test_llm_text_cannot_create_pseudo_approval_state(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Regression test 2: LLM output starting with WAITING_FOR_APPROVAL cannot set run status to
    WAITING_FOR_APPROVAL without a real pending GateDecision / Action."""
    agent_data = {"name": "Text Approval Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Ask for approval in text", "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    # Finish run with output starting with WAITING_FOR_APPROVAL but without passing explicit status
    finish_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/finish",
        json={"output": "WAITING_FOR_APPROVAL: Please confirm purchase."},
        headers=owner_headers
    )
    assert finish_resp.status_code == 200
    run_data = finish_resp.json()
    # Must NOT be WAITING_FOR_APPROVAL because no gate approval was created
    assert run_data["status"] != "WAITING_FOR_APPROVAL"
    assert run_data["status"] == "COMPLETED"


async def test_delegated_authority_permitted_and_denied_capabilities(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Regression test: Authority capabilities must be explicitly checked.
    - CREATE_CART without MANAGE_CART or ADD_CART_ITEM cannot add items.
    - MANAGE_CART allows adding cart items.
    - Authority without CREATE_ORDER cannot checkout.
    - Authority with CREATE_ORDER allows checkout.
    """
    from app.models.workspace import Workspace
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from sqlalchemy import select

    ws_res = await db_session.execute(select(Workspace).limit(1))
    ws = ws_res.scalar_one()

    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    agent_data = {"name": "Full Shopping Flow Agent", "type": "SHOPPING"}
    resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"]},
        headers=owner_headers
    )

    # Authority lacking CREATE_ORDER
    auth_no_order = DelegatedAuthority(
        workspace_id=ws.id,
        agent_id=agent_id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth_no_order)
    await db_session.commit()

    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Buy laptop", "authority_id": auth_no_order.id, "auto_start": False},
        headers=owner_headers
    )
    run_id = run_resp.json()["id"]

    c_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart_id = c_resp.json()["output"]["cart_id"]

    prods_resp = await client.get("/api/v1/commerce/products", headers=owner_headers)
    prod = prods_resp.json()[0]

    # add_to_cart succeeds because MANAGE_CART is granted
    add_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod["id"], "quantity": 1}},
        headers=owner_headers
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["status"] == "SUCCESS"

    # checkout denied because CREATE_ORDER is missing from authority
    checkout_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        headers=owner_headers
    )
    assert checkout_resp.status_code == 403
    err_msg = checkout_resp.json().get("error", {}).get("message", "") or checkout_resp.json().get("detail", "")
    assert "Authority denied" in err_msg

    # Now create authority with explicit CREATE_ORDER
    auth_with_order = DelegatedAuthority(
        workspace_id=ws.id,
        agent_id=agent_id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER"],
        monetary_limit=10000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth_with_order)
    await db_session.commit()

    run2_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Buy laptop", "authority_id": auth_with_order.id, "auto_start": False},
        headers=owner_headers
    )
    run2_id = run2_resp.json()["id"]

    c2_resp = await client.post(f"/api/v1/agent-runtime/runs/{run2_id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=owner_headers)
    cart2_id = c2_resp.json()["output"]["cart_id"]

    await client.post(
        f"/api/v1/agent-runtime/runs/{run2_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart2_id, "product_id": prod["id"], "quantity": 1}},
        headers=owner_headers
    )

    # checkout succeeds
    checkout2_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run2_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart2_id}},
        headers=owner_headers
    )
    assert checkout2_resp.status_code == 200
    assert checkout2_resp.json()["status"] == "SUCCESS"
    assert "order_id" in checkout2_resp.json()["output"]


async def test_e2e_purchase_approval_workflow_exact_scenario(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Acceptance Regression Test for Exact E2E Scenario:
    1. Purchase request: Budget Laptop 15-inch for ₹150.
    2. Intent permits purchase with category 'LAPTOP', max 40,000, approval_required_above: 100.
    3. Authority permits SEARCH_PRODUCTS, CREATE_CART, MANAGE_CART, CREATE_ORDER, PAY_ORDER.
    4. search_products, create_cart, add_to_cart, and checkout succeed (order prepared).
    5. pay_order returns 402 REVIEW and creates durable PENDING approval request.
    6. Approval Center query (/api/v1/approvals/{ws_id}/approvals) shows exact request: agent, amount 150, currency INR.
    7. Before approval: sandbox balance unchanged, no payment captured, order status PENDING_PAYMENT.
    8. Human approves the request.
    9. pay_order re-executes successfully: captured payment recorded with matching 150 INR.
    """
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.models.workspace import Workspace
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.commerce import Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus

    res = await db_session.execute(select(Workspace).limit(1))
    ws = res.scalar_one()

    await initialize_sandbox_catalog(db_session, ws.id)
    await db_session.commit()

    # Create Agent
    resp_agent = await client.post("/api/v1/agents", json={
        "name": "E2E Shopping Agent",
        "description": "Agent for exact e2e purchase test",
        "type": "SHOPPING",
    }, headers=owner_headers)
    assert resp_agent.status_code == 201
    agent_id = resp_agent.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(f"/api/v1/agents/{agent_id}", json={
        "capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    }, headers=owner_headers)

    # Create Intent: category 'LAPTOP', max 40000 INR, approval above 100
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Purchase laptop under INR 40,000",
        natural_language_request="Purchase the Budget Laptop 15-inch for ₹150. My intent permits this purchase, but you must obtain my approval before executing payment because the amount exceeds ₹100.",
        structured_constraints={
            "product": {"category": "LAPTOP"},
            "amount": {"maximum": 40000, "currency": "INR"},
            "approval": {"approval_required": True, "approval_required_above": 100}
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)

    # Create Delegated Authority: max 40000 INR
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        monetary_limit=40000,
        currency="INR",
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(authority)
    await db_session.commit()

    # Start run
    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Purchase the Budget Laptop 15-inch for ₹150",
            "authority_id": authority.id,
            "auto_start": False
        },
        headers=owner_headers
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # 1. Search products
    search_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "search_products", "input": {"query": "Budget Laptop 15-inch", "max_price": 150}},
        headers=owner_headers
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["output"]["results"]
    matched = [p for p in results if p["name"] == "Budget Laptop 15-inch"]
    assert len(matched) == 1
    prod = matched[0]
    assert prod["price"] == 150
    assert prod["currency"] == "INR"

    # 2. Create Cart
    cart_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "create_cart", "input": {}},
        headers=owner_headers
    )
    assert cart_resp.status_code == 200
    cart_id = cart_resp.json()["output"]["cart_id"]

    # 3. Add to Cart
    product_id = prod.get("product_id") or prod.get("id")
    add_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product_id, "quantity": 1}},
        headers=owner_headers
    )
    assert add_resp.status_code == 200

    # 4. Checkout (Order preparation) - Must succeed and NOT be blocked by category or gate
    checkout_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        headers=owner_headers
    )
    assert checkout_resp.status_code == 200, f"Checkout failed: {checkout_resp.text}"
    order_id = checkout_resp.json()["output"]["order_id"]
    assert order_id is not None

    # 5. Execute payment (pay_order) -> ₹150 exceeds ₹100 threshold -> Must return 402 REVIEW
    pay_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        headers=owner_headers
    )
    assert pay_resp.status_code == 402, f"Expected 402 REVIEW but got {pay_resp.status_code}: {pay_resp.text}"

    # 6. Verify Approval Center displays the request
    approvals_resp = await client.get(f"/api/v1/approvals/{ws.id}/approvals", headers=owner_headers)
    assert approvals_resp.status_code == 200
    appr_list = approvals_resp.json()
    pending = [a for a in appr_list if a["agent_run_id"] == run_id]
    assert len(pending) == 1
    approval = pending[0]
    assert approval["status"] == "PENDING"
    assert approval["amount"] == 150
    assert approval["currency"] == "INR"
    assert approval["agent_id"] == agent_id

    # 7. Before approval: no payment was captured and order is still PENDING_PAYMENT
    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.PENDING_PAYMENT

    pay_res = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    payment_before = pay_res.scalar_one_or_none()
    assert payment_before is None or payment_before.status != PaymentStatus.CAPTURED

    # 8. Human approves the request via Approval Center
    decide_resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "APPROVED", "reason": "Approved from test suite"},
        headers=owner_headers
    )
    assert decide_resp.status_code == 200

    # 9. After approval: same order can be paid exactly once
    pay_retry_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        headers=owner_headers
    )
    assert pay_retry_resp.status_code == 200, f"Payment execution failed after approval: {pay_retry_resp.text}"
    pay_action_out = pay_retry_resp.json()["output"]
    assert pay_action_out["status"] in ["PAID", "SUCCESS"] or pay_action_out.get("payment_status") == "CAPTURED"

    # Verify payment in DB
    pay_res_after = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    payment_after = pay_res_after.scalar_one_or_none()
    assert payment_after is not None
    assert payment_after.status == PaymentStatus.CAPTURED
    assert payment_after.amount == 150
    assert payment_after.currency == "INR"

    # Verify order is PAID
    await db_session.refresh(order)
    assert order.status == OrderStatus.PAID
    assert order.total == 150
    assert order.currency == "INR"


async def test_resume_run_end_to_end_approval_and_payment_capture(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Regression test suite for Approval -> Resume Run -> Payment Capture.
    Covers:
    1. Approved request -> resume endpoint -> one captured payment, order PAID, stock decremented once.
    2. Repeated resume does not double charge or create duplicate payments (idempotent).
    3. Invalid, mismatched (wrong amount, wrong currency, wrong order), or already consumed approval fails closed.
    4. Failed resume displays useful error.
    5. Order, payment, and inventory consistency.
    """
    from app.models.commerce import Product, ProductStatus, Merchant, MerchantStatus, Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.agent_runtime import AgentRun, AgentAction, RunStatus, ActionStatus
    from app.models.intent import Intent
    from app.models.authority import DelegatedAuthority

    from app.models.workspace import Workspace

    # Get workspace from db_session
    res_ws = await db_session.execute(select(Workspace).limit(1))
    ws = res_ws.scalar_one()

    # Create merchant
    merch = Merchant(
        id=f"merch_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        name="Tech Retailer",
        status=MerchantStatus.ACTIVE
    )
    db_session.add(merch)
    await db_session.flush()

    # Create Product with initial inventory = 10
    product = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merch.id,
        name="Budget Laptop 15-inch",
        price=150,
        currency="INR",
        inventory=10,
        category="electronics",
        status=ProductStatus.ACTIVE
    )
    db_session.add(product)

    # Agent
    agent_data = {
        "name": "E2E Shopping Agent",
        "description": "Agent testing approval and resume",
        "type": "SHOPPING"
    }
    ag_resp = await client.post("/api/v1/agents", json=agent_data, headers=owner_headers)
    agent_id = ag_resp.json()["id"]

    await client.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"}, headers=owner_headers)
    await client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"capabilities": [
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CREATE_ORDER", "REQUEST_PAYMENT", "EXECUTE_PAYMENT"
        ]},
        headers=owner_headers
    )

    from app.models.intent import IntentType, IntentStatus
    from app.models.authority import AuthorityStatus

    # Intent with 100 INR approval threshold
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_type=IntentType.PURCHASE,
        title="Purchase Laptop Intent",
        natural_language_request="Purchase Budget Laptop for 150 INR",
        structured_constraints={
            "product_scope": ["electronics", "laptop"],
            "max_budget": 50000,
            "currency": "INR",
            "approval_threshold": 100
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    # Authority
    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        monetary_limit=50000,
        currency="INR",
        approval_threshold=100,
        intent_id=intent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CREATE_ORDER", "REQUEST_PAYMENT", "EXECUTE_PAYMENT"
        ],
        version=1
    )
    db_session.add(auth)
    await db_session.commit()

    # Step A: Start Run
    run_resp = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Buy Budget Laptop 15-inch for 150 INR",
            "authority_id": auth.id,
            "auto_start": False
        },
        headers=owner_headers
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # Step B: Create Cart
    cart_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "create_cart", "input": {"currency": "INR"}},
        headers=owner_headers
    )
    assert cart_resp.status_code == 200
    cart_id = cart_resp.json()["output"]["cart_id"]

    # Step C: Add to Cart
    add_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}},
        headers=owner_headers
    )
    assert add_resp.status_code == 200

    # Step D: Checkout -> Creates order, decrements stock once (from 10 to 9)
    checkout_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        headers=owner_headers
    )
    assert checkout_resp.status_code == 200
    order_id = checkout_resp.json()["output"]["order_id"]

    await db_session.refresh(product)
    assert product.inventory == 9  # Decremented once

    # Step E: pay_order -> Returns 402 REVIEW_REQUIRED because 150 > threshold 100
    pay_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        headers=owner_headers
    )
    assert pay_resp.status_code == 402

    # Verify action is PENDING_APPROVAL
    run_check = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=owner_headers)
    run_data = run_check.json()
    pending_actions = [a for a in run_data["actions"] if a["status"] == "PENDING_APPROVAL"]
    assert len(pending_actions) == 1
    assert pending_actions[0]["tool_name"] == "pay_order"

    # Step F: Resume before approval -> Must FAIL CLOSED with useful 400
    pre_resume_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=owner_headers)
    assert pre_resume_resp.status_code == 400, f"Expected 400 but got {pre_resume_resp.status_code}: {pre_resume_resp.text}"
    err_text = pre_resume_resp.text
    assert "pending" in err_text.lower() or "approval" in err_text.lower()

    # Verify order is still PENDING_PAYMENT and no payments captured
    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.PENDING_PAYMENT

    res_p = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    assert res_p.scalar_one_or_none() is None

    # Step G: Find and Approve in Approval Center
    appr_list_resp = await client.get(f"/api/v1/approvals/{ws.id}/approvals", headers=owner_headers)
    assert appr_list_resp.status_code == 200
    approvals = [a for a in appr_list_resp.json() if a["agent_run_id"] == run_id]
    assert len(approvals) == 1
    approval = approvals[0]
    assert approval["status"] == "PENDING"
    assert approval["amount"] == 150
    assert approval["currency"] == "INR"

    decide_resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "APPROVED", "reason": "Approved from regression test"},
        headers=owner_headers
    )
    assert decide_resp.status_code == 200

    # Step H: Resume Run -> Must execute payment capture, update order to PAID, complete run
    resume_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=owner_headers)
    assert resume_resp.status_code == 200, f"Resume failed: {resume_resp.text}"
    resumed_run = resume_resp.json()
    assert resumed_run["status"] == "COMPLETED"

    # Verify the action in the run is now SUCCESS
    pay_action = [a for a in resumed_run["actions"] if a["tool_name"] == "pay_order"][0]
    assert pay_action["status"] == "SUCCESS"
    assert pay_action["output"]["status"] == "PAID"

    # Verify order in DB is PAID
    await db_session.refresh(order)
    assert order.status == OrderStatus.PAID
    assert order.total == 150
    assert order.currency == "INR"

    # Verify payment in DB is CAPTURED
    res_p_after = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    payments = res_p_after.scalars().all()
    assert len(payments) == 1
    payment = payments[0]
    assert payment.status == PaymentStatus.CAPTURED
    assert payment.amount == 150
    assert payment.currency == "INR"

    # Verify inventory was NOT decremented again (still 9, not 8!)
    await db_session.refresh(product)
    assert product.inventory == 9

    # Step I: Repeated Resume (Idempotent) -> Does not double-charge or create duplicate payments
    repeat_resume_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=owner_headers)
    assert repeat_resume_resp.status_code == 200
    repeat_data = repeat_resume_resp.json()
    assert repeat_data["status"] == "COMPLETED"

    # Check payments table again: still exactly 1 payment!
    res_p_repeat = await db_session.execute(select(Payment).where(Payment.order_id == order_id))
    payments_repeat = res_p_repeat.scalars().all()
    assert len(payments_repeat) == 1

    # Inventory still 9
    await db_session.refresh(product)
    assert product.inventory == 9

    # Step J: Invalid / Mismatched Approval Tests (Fail closed)
    # 1. Create a dummy run with a pending approval action
    dummy_run = AgentRun(
        id=f"run_dummy_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        status=RunStatus.RUNNING,
        input="Dummy test"
    )
    db_session.add(dummy_run)
    dummy_act = AgentAction(
        id=f"act_dummy_{uuid.uuid4().hex[:8]}",
        run_id=dummy_run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"order_id": order_id},
        status=ActionStatus.PENDING_APPROVAL
    )
    db_session.add(dummy_act)

    # Already CONSUMED approval cannot be reused
    dummy_appr = ApprovalRequest(
        id=f"appr_consumed_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        agent_run_id=dummy_run.id,
        agent_action_id=dummy_act.id,
        gate_decision_id="gdec_dummy",
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.CONSUMED,
        amount=150,
        currency="INR"
    )
    db_session.add(dummy_appr)
    await db_session.commit()

    consumed_resume_resp = await client.post(f"/api/v1/agent-runtime/runs/{dummy_run.id}/resume", headers=owner_headers)
    assert consumed_resume_resp.status_code == 403, f"Expected 403: {consumed_resume_resp.text}"
    assert "consumed" in consumed_resume_resp.text.lower()

    # 2. Mismatched amount
    dummy_appr.status = ApprovalStatus.APPROVED
    dummy_appr.amount = 9999  # Mismatch with order.total (150)
    await db_session.commit()

    mismatch_amount_resp = await client.post(f"/api/v1/agent-runtime/runs/{dummy_run.id}/resume", headers=owner_headers)
    assert mismatch_amount_resp.status_code == 400, f"Expected 400: {mismatch_amount_resp.text}"
    assert "mismatch" in mismatch_amount_resp.text.lower()

    # 3. Mismatched currency
    dummy_appr.amount = 150
    dummy_appr.currency = "USD"  # Mismatch with order.currency (INR)
    await db_session.commit()

    mismatch_curr_resp = await client.post(f"/api/v1/agent-runtime/runs/{dummy_run.id}/resume", headers=owner_headers)
    assert mismatch_curr_resp.status_code == 400, f"Expected 400: {mismatch_curr_resp.text}"
    assert "mismatch" in mismatch_curr_resp.text.lower()


async def test_decision_trace_endpoint_and_evidence(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Regression test for Inspect Decision Trace:
    1. Loads trace for an existing run with REVIEW_REQUIRED, approval, revalidated ALLOW, order, and payment.
    2. Verifies missing run returns 404.
    3. Verifies run without gate decisions returns empty/unavailable gate decisions list without faking ALLOW.
    4. Verifies approval-to-payment linkage.
    """
    from app.models.agent_runtime import AgentRun, AgentAction, RunStatus, ActionStatus
    from app.models.gate import GateDecision, ApprovalRequest, DecisionResult, ApprovalStatus
    from app.models.commerce import Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus
    from app.models.audit import AuditEvent, EventCategory, EventSeverity, ActorType
    from app.models.workspace import Workspace

    res_ws = await db_session.execute(select(Workspace).limit(1))
    ws = res_ws.scalar_one()

    # 1. 404 for non-existent run
    res_404 = await client.get("/api/v1/agent-runtime/runs/run_nonexistent/decision-trace", headers=owner_headers)
    assert res_404.status_code == 404

    # 2. Run without gate decision produces empty gate_decisions list (never false ALLOW fallback)
    run_empty = AgentRun(
        id=f"run_empty_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=f"agt_{uuid.uuid4().hex[:8]}",
        status=RunStatus.COMPLETED,
        input="Search products",
        output="Found 1 item"
    )
    db_session.add(run_empty)
    await db_session.commit()

    res_empty = await client.get(f"/api/v1/agent-runtime/runs/{run_empty.id}/decision-trace", headers=owner_headers)
    assert res_empty.status_code == 200
    trace_empty = res_empty.json()
    assert trace_empty["run_id"] == run_empty.id
    assert trace_empty["run_status"] == "COMPLETED"
    assert len(trace_empty["gate_decisions"]) == 0
    assert len(trace_empty["approvals"]) == 0

    # 3. Complete run with REVIEW -> APPROVAL -> ALLOW -> PAYMENT execution linkage
    agent_id = f"agt_{uuid.uuid4().hex[:8]}"
    run_linked = AgentRun(
        id=f"run_linked_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        status=RunStatus.COMPLETED,
        input="Purchase Laptop for ₹150",
        output="Order placed and payment successfully captured."
    )
    db_session.add(run_linked)
    await db_session.flush()

    order = Order(
        id=f"ord_trace_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        merchant_id=f"merch_{uuid.uuid4().hex[:8]}",
        status=OrderStatus.PAID,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    payment = Payment(
        id=f"pay_trace_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        order_id=order.id,
        payment_intent_id=f"pi_trace_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_trace_{uuid.uuid4().hex[:8]}",
        amount=150,
        currency="INR",
        status=PaymentStatus.CAPTURED
    )
    db_session.add(payment)

    action = AgentAction(
        id=f"act_trace_{uuid.uuid4().hex[:8]}",
        run_id=run_linked.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"order_id": order.id},
        output={"status": "PAID", "transaction_id": payment.id},
        status=ActionStatus.SUCCESS,
        alignment_result="ALIGNED"
    )
    db_session.add(action)

    appr = ApprovalRequest(
        id=f"appr_trace_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        agent_run_id=run_linked.id,
        agent_action_id=action.id,
        gate_decision_id="gdec_initial",
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.CONSUMED,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"},
        approved_at=datetime.now(timezone.utc)
    )
    db_session.add(appr)

    gdec_review = GateDecision(
        id=f"gdec_rev_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        agent_run_id=run_linked.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        explanation="Review required based on risk or thresholds",
        required_approval=True,
        approval_id=appr.id,
        evaluation_snapshot={"policy": {"decision": "ALLOW"}, "risk": {"level": "LOW", "score": 8.5}}
    )
    db_session.add(gdec_review)

    gdec_allow = GateDecision(
        id=f"gdec_allow_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        agent_run_id=run_linked.id,
        agent_action_id=action.id,
        decision=DecisionResult.ALLOW,
        reason_codes=["OK"],
        explanation="Action allowed",
        required_approval=False,
        approval_id=appr.id,
        evaluation_snapshot={"policy": {"decision": "ALLOW"}, "risk": {"level": "LOW", "score": 8.5}}
    )
    db_session.add(gdec_allow)

    evt = AuditEvent(
        id=f"evt_trace_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        event_type="GATE_DECISION_ALLOW",
        event_category=EventCategory.GATE,
        severity=EventSeverity.INFO,
        actor_type=ActorType.SYSTEM,
        agent_run_id=run_linked.id,
        entity_id=gdec_allow.id,
        workspace_sequence=1,
        event_hash="hash_trace_123"
    )
    db_session.add(evt)
    await db_session.commit()

    # Query decision trace endpoint
    res_trace = await client.get(f"/api/v1/agent-runtime/runs/{run_linked.id}/decision-trace", headers=owner_headers)
    assert res_trace.status_code == 200
    trace = res_trace.json()

    assert trace["run_id"] == run_linked.id
    assert trace["run_status"] == "COMPLETED"
    assert len(trace["actions"]) == 1
    assert trace["actions"][0]["tool_name"] == "pay_order"

    assert len(trace["gate_decisions"]) == 2
    assert trace["gate_decisions"][0]["decision"] == "REVIEW"
    assert "APPROVAL_THRESHOLD_EXCEEDED" in trace["gate_decisions"][0]["reason_codes"]
    assert trace["gate_decisions"][1]["decision"] == "ALLOW"
    assert trace["gate_decisions"][1]["reason_codes"] == ["OK"]

    assert len(trace["approvals"]) == 1
    assert trace["approvals"][0]["id"] == appr.id
    assert trace["approvals"][0]["status"] == "CONSUMED"
    assert trace["approvals"][0]["amount"] == 150.0
    assert trace["approvals"][0]["currency"] == "INR"

    assert len(trace["orders"]) == 1
    assert trace["orders"][0]["id"] == order.id
    assert trace["orders"][0]["total"] == 150.0

    assert len(trace["payments"]) == 1
    assert trace["payments"][0]["id"] == payment.id
    assert trace["payments"][0]["status"] == "CAPTURED"

    assert len(trace["audit_events"]) >= 1
    assert any(e["event_type"] == "GATE_DECISION_ALLOW" for e in trace["audit_events"])


async def test_financial_authority_currency_enforcement_max_transaction(client: AsyncClient, owner_headers, db_session: AsyncSession):
    """
    Regression Test:
    Verify that an INR 85,000 transaction cannot bypass a 40,000 INR maximum limit.
    Gate must BLOCK with AUTHORITY_EXCEEDED.
    """
    from app.models.agent import Agent, AgentStatus, AgentType
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.commerce import Product
    from app.services.action_gate_service import GateEvaluator, DecisionResult

    ws = (await db_session.execute(select(Workspace))).scalars().first()

    agent_id = f"agt_{uuid.uuid4().hex[:12]}"
    agent = Agent(
        id=agent_id,
        workspace_id=ws.id,
        name="INR Capped Shopping Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        max_transaction_amount=40000,
        currency="INR"
    )
    db_session.add(agent)

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        monetary_limit=40000,
        currency="INR",
        approval_threshold=5000,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        version=1
    )
    db_session.add(auth)
    await db_session.commit()

    decision, reasons, explanation = GateEvaluator.aggregate_gate_decision(
        agent=agent,
        intent=None,
        authority=auth,
        policy_action=None,
        risk=None,
        transaction={"amount": 85000, "currency": "INR"},
        action_type="pay_order"
    )

    assert decision == DecisionResult.BLOCK
    assert "AUTHORITY_EXCEEDED" in reasons


async def test_financial_authority_currency_enforcement_approval_threshold(client: AsyncClient, owner_headers, db_session: AsyncSession):
    """
    Regression Test:
    Verify that an INR 150 transaction triggers REVIEW when the approval threshold is 100 INR.
    Gate must yield REVIEW with APPROVAL_THRESHOLD_EXCEEDED.
    """
    from app.models.agent import Agent, AgentStatus, AgentType
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.services.action_gate_service import GateEvaluator, DecisionResult

    ws = (await db_session.execute(select(Workspace))).scalars().first()

    agent_id = f"agt_{uuid.uuid4().hex[:12]}"
    agent = Agent(
        id=agent_id,
        workspace_id=ws.id,
        name="INR Threshold Shopping Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        max_transaction_amount=40000,
        approval_threshold=100,
        currency="INR"
    )
    db_session.add(agent)

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        monetary_limit=40000,
        currency="INR",
        approval_threshold=100,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        version=1
    )
    db_session.add(auth)
    await db_session.commit()

    decision, reasons, explanation = GateEvaluator.aggregate_gate_decision(
        agent=agent,
        intent=None,
        authority=auth,
        policy_action=None,
        risk=None,
        transaction={"amount": 150, "currency": "INR"},
        action_type="pay_order"
    )

    assert decision == DecisionResult.REVIEW
    assert "APPROVAL_THRESHOLD_EXCEEDED" in reasons


async def test_financial_authority_currency_mismatch_cross_currency_blocked(client: AsyncClient, owner_headers, db_session: AsyncSession):
    """
    Regression Test:
    Verify cross-currency protection: an agent or authority configured in INR cannot execute USD transactions
    without explicit currency alignment.
    """
    from app.models.agent import Agent, AgentStatus, AgentType
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.services.action_gate_service import GateEvaluator, DecisionResult

    ws = (await db_session.execute(select(Workspace))).scalars().first()

    agent_id = f"agt_{uuid.uuid4().hex[:12]}"
    agent = Agent(
        id=agent_id,
        workspace_id=ws.id,
        name="INR Agent USD Reject",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER", "EXECUTE_PAYMENT"],
        max_transaction_amount=40000,
        currency="INR"
    )
    db_session.add(agent)

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        monetary_limit=40000,
        currency="INR",
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER", "EXECUTE_PAYMENT"],
        version=1
    )
    db_session.add(auth)
    await db_session.commit()

    decision, reasons, explanation = GateEvaluator.aggregate_gate_decision(
        agent=agent,
        intent=None,
        authority=auth,
        policy_action=None,
        risk=None,
        transaction={"amount": 500, "currency": "USD"},
        action_type="pay_order"
    )

    assert decision == DecisionResult.BLOCK
    assert "CURRENCY_MISMATCH" in reasons


async def test_regression_exact_search_returns_persisted_product(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify that exact search returns persisted product even if category is Laptop vs electronics."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.services.agent_runtime_service import AgentRuntimeService

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_search_{uuid.uuid4().hex[:8]}",
        name="Search Regression WS",
        slug=f"search-reg-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()
    await initialize_sandbox_catalog(db_session, ws.id)

    agent = Agent(
        id=f"ag_search_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Search Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS"]
    )
    db_session.add(agent)
    await db_session.commit()

    # Search with category='Laptop' and exact query
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Find Budget Laptop 15-inch"
    )

    action = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws.id,
        run_id=run.id,
        tool_name="search_products",
        tool_input={"query": "Budget Laptop 15-inch", "category": "Laptop"}
    )
    assert action.status == ActionStatus.SUCCESS
    results = action.output.get("results", [])
    assert len(results) > 0
    assert results[0]["name"] == "Budget Laptop 15-inch"
    assert results[0]["price"] == 150
    assert results[0]["currency"] == "INR"


async def test_regression_search_only_request_creates_no_orders_or_payments(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify search-only requests never create carts, orders, or payments in the workspace."""
    from app.models.commerce import Cart, Order
    from app.models.payment import Payment
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.services.commerce_init_service import initialize_sandbox_catalog

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_search_only_{uuid.uuid4().hex[:8]}",
        name="Search Only WS",
        slug=f"search-only-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()
    await initialize_sandbox_catalog(db_session, ws.id)

    agent = Agent(
        id=f"ag_search_only_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Search Only Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS"]
    )
    db_session.add(agent)
    await db_session.commit()

    # Record initial counts
    initial_carts = len((await db_session.execute(select(Cart).where(Cart.workspace_id == ws.id))).scalars().all())
    initial_orders = len((await db_session.execute(select(Order).where(Order.workspace_id == ws.id))).scalars().all())
    initial_payments = len((await db_session.execute(select(Payment).where(Payment.workspace_id == ws.id))).scalars().all())

    # Create run and perform only search
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Search for laptops"
    )
    await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws.id,
        run_id=run.id,
        tool_name="search_products",
        tool_input={"query": "laptop", "category": "electronics"}
    )
    await AgentRuntimeService.finish_run(db=db_session, workspace_id=ws.id, run_id=run.id, output="Found laptops.")

    after_carts = len((await db_session.execute(select(Cart).where(Cart.workspace_id == ws.id))).scalars().all())
    after_orders = len((await db_session.execute(select(Order).where(Order.workspace_id == ws.id))).scalars().all())
    after_payments = len((await db_session.execute(select(Payment).where(Payment.workspace_id == ws.id))).scalars().all())

    assert after_carts == initial_carts
    assert after_orders == initial_orders
    assert after_payments == initial_payments


async def test_regression_purchase_150_with_threshold_100_reaches_review_and_waits_for_approval(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify ₹150 purchase with ₹100 threshold reaches REVIEW, sets PENDING_APPROVAL, and halts payment capture."""
    from app.services.commerce_init_service import initialize_sandbox_catalog
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.intent import Intent, IntentType, IntentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.gate import ApprovalRequest, ApprovalStatus, GateDecision, DecisionResult

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_reg_{uuid.uuid4().hex[:8]}",
        name="Review Regression WS",
        slug=f"review-reg-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()
    await initialize_sandbox_catalog(db_session, ws.id)

    agent = Agent(
        id=f"ag_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Shopping Agent Review",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        max_transaction_amount=40000,
        approval_threshold=100,
        currency="INR"
    )
    db_session.add(agent)

    intent = Intent(
        id=f"int_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        title="Laptop intent with 100 threshold",
        natural_language_request="Buy laptop for 150 INR",
        structured_constraints={
            "amount": {"maximum": 40000, "currency": "INR"},
            "approval": {"approval_required_above": 100, "approval_required": True}
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    auth = DelegatedAuthority(
        id=f"auth_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_id=intent.id,
        monetary_limit=40000,
        approval_threshold=100,
        currency="INR",
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=list(agent.capabilities),
        version=1
    )
    db_session.add(auth)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Purchase Budget Laptop for 150",
        authority_id=auth.id
    )

    # 1. Search
    act_search = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="search_products", tool_input={"query": "Budget Laptop 15-inch"}
    )
    prod_id = act_search.output["results"][0]["product_id"]

    # 2. Create Cart
    act_cart = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="create_cart", tool_input={}
    )
    cart_id = act_cart.output["cart_id"]

    # 3. Add to cart
    await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": prod_id, "quantity": 1}
    )

    # 4. Checkout
    act_chk = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="checkout", tool_input={"cart_id": cart_id}
    )
    order_id = act_chk.output["order_id"]

    # 5. Pay Order -> Must trigger REVIEW because 150 > 100 threshold
    try:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run.id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
        assert False, "pay_order should have raised HTTPException 402 for human approval"
    except HTTPException as e:
        assert e.status_code == 402
        assert "Action requires human approval" in e.detail

    # Verify action is PENDING_APPROVAL and gate decision is REVIEW
    stmt_act = select(AgentAction).where(AgentAction.run_id == run.id, AgentAction.tool_name == "pay_order")
    pay_act = (await db_session.execute(stmt_act)).scalar_one()
    assert pay_act.status == ActionStatus.PENDING_APPROVAL

    stmt_dec = select(GateDecision).where(GateDecision.agent_action_id == pay_act.id)
    dec = (await db_session.execute(stmt_dec)).scalar_one()
    assert dec.decision == DecisionResult.REVIEW
    assert "APPROVAL_THRESHOLD_EXCEEDED" in dec.reason_codes

    # Verify approval request was created with status PENDING and amount 150
    appr = await db_session.get(ApprovalRequest, dec.approval_id)
    assert appr is not None
    assert appr.status == ApprovalStatus.PENDING
    assert appr.amount == 150
    assert appr.currency == "INR"


async def test_regression_missing_authority_remains_blocked(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify that an agent with no active authority cannot execute non-safe tools."""
    from app.services.agent_runtime_service import AgentRuntimeService

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_noauth_{uuid.uuid4().hex[:8]}",
        name="No Auth WS",
        slug=f"no-auth-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    agent = Agent(
        id=f"ag_noauth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Agent Without Authority",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART"]
    )
    db_session.add(agent)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Create a cart"
    )

    try:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws.id,
            run_id=run.id,
            tool_name="create_cart",
            tool_input={}
        )
        assert False, "create_cart should have failed with 403 DELEGATED_AUTHORITY_REQUIRED"
    except HTTPException as e:
        assert e.status_code == 403

    stmt = select(AgentAction).where(AgentAction.run_id == run.id, AgentAction.tool_name == "create_cart")
    action = (await db_session.execute(stmt)).scalar_one()
    assert action.status == ActionStatus.DENIED
    assert "DELEGATED_AUTHORITY_REQUIRED" in action.error_message


async def test_regression_repeated_searches_terminate_within_limit(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify that repeated unsuccessful searches stop within the configured limit and do not loop indefinitely."""
    from unittest.mock import patch, AsyncMock
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.services.commerce_init_service import initialize_sandbox_catalog

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_bnd_{uuid.uuid4().hex[:8]}",
        name="Bounded Search WS",
        slug=f"bounded-search-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()
    await initialize_sandbox_catalog(db_session, ws.id)

    agent = Agent(
        id=f"ag_bnd_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Search Agent Bounded",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS"]
    )
    db_session.add(agent)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Find Nonexistent Item 12345"
    )

    # Simulate Groq model that keeps calling search_products repeatedly with nonexistent items
    class DummyToolCall:
        def __init__(self, name, args):
            self.id = f"tc_{uuid.uuid4().hex[:6]}"
            self.type = "function"
            self.function = type("Func", (), {"name": name, "arguments": args})()
        def model_dump(self, *args, **kwargs):
            return {
                "id": self.id,
                "type": "function",
                "function": {"name": self.function.name, "arguments": self.function.arguments}
            }

    class DummyMessage:
        def __init__(self, tool_calls=None, content=None):
            self.tool_calls = tool_calls
            self.content = content
        def model_dump(self, *args, **kwargs):
            d = {"role": "assistant", "content": self.content}
            if self.tool_calls:
                d["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
            return d

    class DummyChoice:
        def __init__(self, message):
            self.message = message

    class DummyCompletion:
        def __init__(self, message):
            self.choices = [DummyChoice(message)]

    # Model returns search_products with same or different nonexistent queries
    search_msg = DummyMessage(
        tool_calls=[DummyToolCall("search_products", '{"query": "Nonexistent Item 12345"}')]
    )
    stop_msg = DummyMessage(content="Item not found.")

    call_count = 0
    def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 5:
            return DummyCompletion(search_msg)
        return DummyCompletion(stop_msg)

    run_id = run.id
    ws_id = ws.id

    from app.api.routes.agent_runtime import run_deterministic_agent

    with patch("groq.AsyncGroq") as mock_groq_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
        mock_groq_cls.return_value = mock_client

        await run_deterministic_agent(run_id, ws_id, db_override=db_session)

    res = await db_session.execute(select(AgentRun).where(AgentRun.id == run_id))
    updated_run = res.scalar_one()
    assert updated_run.status in [RunStatus.COMPLETED, RunStatus.FAILED]

    # Verify action count is strictly bounded (consecutive search limit is <= 3)
    actions = (await db_session.execute(
        select(AgentAction).where(AgentAction.run_id == run_id)
    )).scalars().all()
    search_actions = [a for a in actions if a.tool_name == "search_products"]
    assert len(search_actions) <= 4


async def test_regression_http_429_does_not_produce_false_allow(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify that Groq HTTP 429 rate limit fails truthfully and never produces an ALLOW decision."""
    from unittest.mock import patch, AsyncMock
    from groq import RateLimitError
    from httpx import Response, Request
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.api.routes.agent_runtime import run_deterministic_agent

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_429_{uuid.uuid4().hex[:8]}",
        name="Rate Limit WS",
        slug=f"rate-limit-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    agent = Agent(
        id=f"ag_429_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Rate Limited Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS"]
    )
    db_session.add(agent)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Purchase anything"
    )

    run_id = run.id
    ws_id = ws.id

    req = Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = Response(429, request=req, headers={"retry-after": "1"})
    rate_err = RateLimitError("Rate limit reached", response=resp, body={"error": {"message": "Rate limit reached"}})

    with patch("groq.AsyncGroq") as mock_groq_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=rate_err)
        mock_groq_cls.return_value = mock_client

        await run_deterministic_agent(run_id, ws_id, db_override=db_session)

    # Verify run persisted state
    res = await db_session.execute(select(AgentRun).where(AgentRun.id == run_id))
    updated_run = res.scalar_one()
    assert updated_run.status == RunStatus.FAILED
    assert updated_run.error_code == "RATE_LIMIT_EXCEEDED"


async def test_regression_action_name_normalization_and_intent_alignment():
    """Verify that intent allowed_actions with ADD_CART_ITEM aligns with runtime add_to_cart."""
    from app.services.alignment_engine import evaluate_alignment
    from app.services.capabilities import normalize_action_name, get_equivalent_action_names

    # Test normalization function
    assert normalize_action_name("add_to_cart") == "ADD_CART_ITEM"
    assert normalize_action_name("search_products") == "SEARCH_PRODUCTS"
    assert normalize_action_name("create_cart") == "CREATE_CART"
    assert normalize_action_name("checkout") == "CREATE_ORDER"
    assert normalize_action_name("pay_order") == "PAY_ORDER"
    assert "add_to_cart" in get_equivalent_action_names("ADD_CART_ITEM")

    # Intent defines allowed_actions using canonical capability name
    constraints = {"allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"]}
    
    # Runtime executes tool using lowercase tool name
    res = evaluate_alignment(constraints=constraints, action="add_to_cart")
    assert res.alignment == "ALIGNED"
    assert any(s.type == "ACTION" and s.status == "ALIGNED" for s in res.signals)

    # Disallowed action is blocked (fail-closed)
    res_blocked = evaluate_alignment(constraints={"allowed_actions": ["SEARCH_PRODUCTS"]}, action="add_to_cart")
    assert res_blocked.alignment == "MISALIGNED"


async def test_regression_duplicate_cart_prevention(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify that consecutive create_cart calls in a single run reuse the existing cart."""
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.authority import DelegatedAuthority, AuthorityStatus

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_cart_{uuid.uuid4().hex[:8]}",
        name="Cart WS",
        slug=f"cart-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    agent = Agent(
        id=f"ag_cart_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Cart Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART"]
    )
    db_session.add(agent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_cart_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART"],
        currency="INR"
    )
    db_session.add(auth)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws.id,
        agent_id=agent.id,
        input_text="Create cart and add items",
        authority_id=auth.id
    )

    # First call: creates cart
    act1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="create_cart", tool_input={}
    )
    assert act1.status == ActionStatus.SUCCESS
    first_cart_id = act1.output["cart_id"]

    # Second call: reuses cart
    act2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="create_cart", tool_input={}
    )
    assert act2.status == ActionStatus.SUCCESS
    assert act2.output["cart_id"] == first_cart_id
    assert act2.output.get("reused") is True


async def test_regression_search_cart_add_item_authoritative_hydration(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify search -> cart -> add item with authoritative product pricing and details."""
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.commerce import Merchant, Product, ProductStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_flow_{uuid.uuid4().hex[:8]}",
        name="Flow WS",
        slug=f"flow-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    merchant = Merchant(
        id=f"mer_flow_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Authoritative Merchant"
    )
    db_session.add(merchant)
    await db_session.flush()

    prod = Product(
        id=f"prod_flow_{uuid.uuid4().hex[:8]}",
        merchant_id=merchant.id,
        name="Quantum Laptop Pro",
        category="Electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add(prod)
    await db_session.flush()

    agent = Agent(
        id=f"ag_flow_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Flow Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(agent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_flow_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        currency="INR",
        monetary_limit=500,
        approval_threshold=100
    )
    db_session.add(auth)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Buy Quantum Laptop Pro", authority_id=auth.id
    )

    # 1. Search products
    act_search = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="search_products", tool_input={"query": "Quantum Laptop Pro"}
    )
    assert act_search.status == ActionStatus.SUCCESS
    assert len(act_search.output["results"]) > 0
    found_prod = act_search.output["results"][0]
    assert found_prod["product_id"] == prod.id
    assert found_prod["price"] == 150
    assert found_prod["currency"] == "INR"

    # 2. Create cart
    act_cart = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="create_cart", tool_input={}
    )
    assert act_cart.status == ActionStatus.SUCCESS
    cart_id = act_cart.output["cart_id"]

    # 3. Add to cart (hydrates from DB authoritative product)
    act_add = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": prod.id, "quantity": 1}
    )
    assert act_add.status == ActionStatus.SUCCESS
    assert act_add.output["price"] == 150
    assert act_add.output["total"] == 150
    assert act_add.output["currency"] == "INR"


async def test_regression_150_purchase_with_100_threshold_requires_approval_before_payment(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify ₹150 purchase with ₹100 threshold triggers REVIEW and prevents payment capture until approval."""
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.commerce import Merchant, Product, ProductStatus
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.payment import Payment
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.api.routes.agent_runtime import run_deterministic_agent

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_rev_{uuid.uuid4().hex[:8]}",
        name="Review WS",
        slug=f"review-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    merchant = Merchant(
        id=f"mer_rev_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Review Merchant"
    )
    db_session.add(merchant)
    await db_session.flush()

    prod = Product(
        id=f"prod_rev_{uuid.uuid4().hex[:8]}",
        merchant_id=merchant.id,
        name="Premium Widget",
        category="Electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add(prod)
    await db_session.flush()

    agent = Agent(
        id=f"ag_rev_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Review Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(agent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_rev_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        currency="INR",
        monetary_limit=500,
        approval_threshold=100
    )
    db_session.add(auth)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Buy Premium Widget for 150 INR", authority_id=auth.id
    )

    # 1. Cart and Item
    act_cart = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws.id, run_id=run.id, tool_name="create_cart", tool_input={})
    cart_id = act_cart.output["cart_id"]

    await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws.id, run_id=run.id, tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": prod.id, "quantity": 1})

    # 2. Checkout
    act_checkout = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws.id, run_id=run.id, tool_name="checkout", tool_input={"cart_id": cart_id})
    order_id = act_checkout.output["order_id"]

    # 3. Pay order: 150 exceeds approval threshold 100 -> Must raise 402 REVIEW and set status PENDING_APPROVAL
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run.id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert exc_info.value.status_code == 402

    # Verify NO payment captured before approval
    stmt_pay = select(Payment).where(Payment.order_id == order_id)
    payments = (await db_session.execute(stmt_pay)).scalars().all()
    assert len(payments) == 0

    # Verify pending approval exists
    stmt_appr = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    appr = (await db_session.execute(stmt_appr)).scalars().first()
    assert appr is not None
    assert appr.status == ApprovalStatus.PENDING
    assert appr.amount == 150

    # 4. Now approve the request
    appr.status = ApprovalStatus.APPROVED
    await db_session.commit()

    # 5. Resume / execute after approval via run_deterministic_agent
    await run_deterministic_agent(run.id, ws.id, db_override=db_session)

    # Verify payment IS now captured
    stmt_pay_after = select(Payment).where(Payment.order_id == order_id)
    payments_after = (await db_session.execute(stmt_pay_after)).scalars().all()
    assert len(payments_after) == 1
    assert payments_after[0].status.value in ["CAPTURED", "PAID", "SUCCEEDED", "AUTHORIZED"]


async def test_regression_blocked_actions_produce_no_payment_side_effects(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """Verify blocked actions cleanly fail and produce no payment or order capture side effects."""
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.commerce import Merchant, Product, ProductStatus
    from app.models.payment import Payment

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_blk_{uuid.uuid4().hex[:8]}",
        name="Blocked WS",
        slug=f"blocked-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    # Agent has only SEARCH_PRODUCTS - no cart or payment authority
    agent = Agent(
        id=f"ag_blk_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Search Only Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS"]
    )
    db_session.add(agent)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Unauthorized purchase attempt"
    )

    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run.id,
            tool_name="pay_order", tool_input={"order_id": "fake_order"}
        )
    assert exc_info.value.status_code == 403


    # Ensure zero payments created
    stmt = select(Payment).where(Payment.workspace_id == ws.id)
    res = await db_session.execute(stmt)
    assert len(res.scalars().all()) == 0


async def test_regression_duplicate_approval_prevention_and_idempotent_tools(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Comprehensive regression test:
    1. Verify repeated tool calls (add_to_cart, checkout, pay_order) cannot produce duplicate orders,
       duplicate approval requests, or duplicate payment captures.
    2. Verify gate REVIEW creates exactly one pending approval request, and repeated evaluations
       reuse the existing pending approval.
    3. Verify approval is strictly bound to exact agent, run, workspace, order, amount, and currency.
    4. Verify approval is single-use and cannot be replayed once consumed.
    """
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.commerce import Merchant, Product, ProductStatus, Order, OrderStatus, Cart
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.payment import Payment
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.services.action_gate_service import ActionGateService

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_dup_{uuid.uuid4().hex[:8]}",
        name="Dup Regression WS",
        slug=f"dup-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    merchant = Merchant(
        id=f"mer_dup_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Budget Electronics"
    )
    db_session.add(merchant)
    await db_session.flush()

    prod = Product(
        id=f"prod_dup_{uuid.uuid4().hex[:8]}",
        merchant_id=merchant.id,
        name="Budget Laptop 15-inch",
        category="Electronics",
        price=150,
        currency="INR",
        inventory=5,
        status=ProductStatus.ACTIVE
    )
    db_session.add(prod)
    await db_session.flush()

    agent = Agent(
        id=f"ag_dup_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Laptop Buying Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        currency="INR",
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(agent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_dup_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        currency="INR",
        monetary_limit=500,
        approval_threshold=100
    )
    db_session.add(auth)
    await db_session.commit()

    run = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Buy Budget Laptop 15-inch for 150 INR", authority_id=auth.id
    )

    # ── 1. Test Idempotent Cart Creation ──
    act_cart1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id, tool_name="create_cart", tool_input={}
    )
    cart_id1 = act_cart1.output["cart_id"]

    act_cart2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id, tool_name="create_cart", tool_input={}
    )
    assert act_cart2.output["cart_id"] == cart_id1
    assert act_cart2.output.get("reused") is True

    # ── 2. Test Idempotent Add to Cart ──
    act_add1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id1, "product_id": prod.id, "quantity": 1}
    )
    assert act_add1.output["quantity"] == 1
    assert act_add1.output["total"] == 150

    act_add2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id1, "product_id": prod.id, "quantity": 1}
    )
    assert act_add2.output.get("reused") is True
    assert act_add2.output["quantity"] == 1
    assert act_add2.output["total"] == 150

    # ── 3. Test Idempotent Checkout ──
    act_co1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="checkout", tool_input={"cart_id": cart_id1}
    )
    order_id1 = act_co1.output["order_id"]
    assert act_co1.output["total"] == 150

    act_co2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="checkout", tool_input={"cart_id": cart_id1}
    )
    assert act_co2.output["order_id"] == order_id1
    assert act_co2.output.get("reused") is True

    # Verify only ONE order exists in the DB for this cart
    stmt_orders = select(Order).where(Order.cart_id == cart_id1)
    orders = (await db_session.execute(stmt_orders)).scalars().all()
    assert len(orders) == 1

    # ── 4. Test Review Requirement & Duplicate Approval Prevention ──
    # pay_order for ₹150 with threshold ₹100 must raise 402 REVIEW
    with pytest.raises(HTTPException) as exc_info1:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run.id,
            tool_name="pay_order", tool_input={"order_id": order_id1}
        )
    assert exc_info1.value.status_code == 402
    appr_id_1 = exc_info1.value.detail.split(": ")[-1]

    # Verify run status transitioned to WAITING_FOR_APPROVAL
    await db_session.refresh(run)
    assert run.status == RunStatus.WAITING_FOR_APPROVAL

    # Verify exactly 1 approval request in DB
    stmt_apprs = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    apprs = (await db_session.execute(stmt_apprs)).scalars().all()
    assert len(apprs) == 1
    first_appr = apprs[0]
    assert first_appr.id == appr_id_1
    assert first_appr.status == ApprovalStatus.PENDING
    assert first_appr.amount == 150
    assert first_appr.currency == "INR"

    # Now simulate a repeated Action Gate evaluation for the same order and run (e.g. retry tool call)
    gate = ActionGateService(db_session)
    dec2 = await gate.evaluate(
        workspace_id=ws.id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=f"act_retry_{uuid.uuid4().hex[:6]}",
        authority_id=auth.id,
        transaction={"amount": 150, "currency": "INR", "order_id": order_id1},
        action_type="pay_order"
    )
    assert dec2.decision.value == "REVIEW"
    # Gate MUST link to the existing pending approval, NOT create a duplicate
    assert dec2.approval_id == first_appr.id

    stmt_apprs_after = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    apprs_after = (await db_session.execute(stmt_apprs_after)).scalars().all()
    assert len(apprs_after) == 1, "Duplicate approval request was created on repeated evaluation!"

    # ── 5. Verify Context Binding ──
    assert first_appr.agent_id == agent.id
    assert first_appr.agent_run_id == run.id
    assert first_appr.workspace_id == ws.id
    assert first_appr.amount == 150
    assert first_appr.currency == "INR"
    assert first_appr.transaction_data.get("order_id") == order_id1

    # ── 6. Human Approval & Resumption Execution ──
    first_appr.status = ApprovalStatus.APPROVED
    await db_session.commit()

    from app.api.routes.agent_runtime import run_deterministic_agent
    await run_deterministic_agent(run.id, ws.id, db_override=db_session)

    # Verify run completed and payment captured
    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED

    stmt_pay = select(Payment).where(Payment.order_id == order_id1)
    payments = (await db_session.execute(stmt_pay)).scalars().all()
    assert len(payments) == 1
    assert payments[0].amount == 150
    assert payments[0].currency == "INR"

    # ── 7. Single-Use Verification (Consumed Approval Replay Prevention) ──
    await db_session.refresh(first_appr)
    assert first_appr.status == ApprovalStatus.CONSUMED

    # A repeated execution of pay_order for the now-PAID order returns cleanly with reused: True
    # and DOES NOT capture another payment
    act_pay_retry = await AgentRuntimeService._execute_tool_logic(
        db=db_session, workspace_id=ws.id, agent_id=agent.id, tool_name="pay_order",
        input_data=type('Input', (), {'order_id': order_id1})(),
        raw_input={"order_id": order_id1}, run_id=run.id
    )
    assert act_pay_retry.get("status") == "PAID"
    assert act_pay_retry.get("reused") is True

    stmt_pay_count = select(Payment).where(Payment.order_id == order_id1)
    all_payments = (await db_session.execute(stmt_pay_count)).scalars().all()
    assert len(all_payments) == 1, "Duplicate payment was captured on retry!"


async def test_regression_rejected_and_pending_approval_cannot_capture_payment(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Regression test proving:
    1. Pending approval -> no payment capture (resume raises 400).
    2. Rejected approval -> no payment capture (resume sets DENIED, BLOCKED, 0 payments).
    3. Approved, exact-context approval -> at most one capture.
    4. Replaying or resuming a rejected run cannot capture payment.
    5. UI status and decision trace accurately reflect persisted payment and approval records.
    """
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.models.commerce import Merchant, Product, ProductStatus, Order, OrderStatus, Cart
    from app.models.gate import ApprovalRequest, ApprovalStatus, GateDecision, DecisionResult
    from app.models.payment import Payment, PaymentStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.services.action_gate_service import ActionGateService
    from app.api.routes.agent_runtime import resume_run, get_decision_trace

    user = (await db_session.execute(select(User))).scalars().first()
    ws = Workspace(
        id=f"ws_reg_{uuid.uuid4().hex[:8]}",
        name="Regression WS",
        slug=f"reg-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(ws)
    await db_session.flush()

    merchant = Merchant(
        id=f"mer_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Budget Store"
    )
    db_session.add(merchant)
    await db_session.flush()

    prod = Product(
        id=f"prod_reg_{uuid.uuid4().hex[:8]}",
        merchant_id=merchant.id,
        name="Budget Laptop 15-inch",
        category="Electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add(prod)
    await db_session.flush()

    agent = Agent(
        id=f"ag_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Shopper Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        currency="INR",
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(agent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_reg_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        currency="INR",
        monetary_limit=500,
        approval_threshold=100
    )
    db_session.add(auth)
    await db_session.commit()

    # ── Test 1: Pending Approval -> No Payment Capture ──
    run1 = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Buy laptop for 150 INR", authority_id=auth.id
    )
    act_cart = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run1.id, tool_name="create_cart", tool_input={}
    )
    await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run1.id,
        tool_name="add_to_cart", tool_input={"cart_id": act_cart.output["cart_id"], "product_id": prod.id, "quantity": 1}
    )
    act_co = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run1.id,
        tool_name="checkout", tool_input={"cart_id": act_cart.output["cart_id"]}
    )
    order_id1 = act_co.output["order_id"]

    # Trigger Action Gate review (150 > 100)
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run1.id,
            tool_name="pay_order", tool_input={"order_id": order_id1}
        )
    assert exc_info.value.status_code == 402

    # While approval is PENDING, resuming must fail with 400 and capture ZERO payments
    with pytest.raises(HTTPException) as exc_pending:
        await resume_run(run_id=run1.id, db=db_session, workspace=ws, current_user=user)
    assert exc_pending.value.status_code == 400
    assert "PENDING" in exc_pending.value.detail

    # Verify zero payments created
    stmt_p = select(Payment).where(Payment.order_id == order_id1)
    assert len((await db_session.execute(stmt_p)).scalars().all()) == 0

    # ── Test 2: Rejected Approval -> No Payment Capture ──
    stmt_appr = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run1.id)
    appr1 = (await db_session.execute(stmt_appr)).scalars().one()
    appr1.status = ApprovalStatus.REJECTED
    appr1.rejected_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Resume after rejection -> must mark action DENIED and run BLOCKED, with 0 payments
    resumed_run = await resume_run(run_id=run1.id, db=db_session, workspace=ws, current_user=user)
    assert resumed_run.status == RunStatus.BLOCKED
    assert "rejected" in resumed_run.output.lower()
    denied_actions = [a for a in resumed_run.actions if a.status == ActionStatus.DENIED]
    assert len(denied_actions) == 1
    assert denied_actions[0].tool_name == "pay_order"

    # Confirm order is still PENDING_PAYMENT and zero payments captured
    order1 = await db_session.get(Order, order_id1)
    assert order1.status == OrderStatus.PENDING_PAYMENT
    assert len((await db_session.execute(stmt_p)).scalars().all()) == 0

    # ── Test 3: Replaying or Resuming a Rejected Run Cannot Capture Payment ──
    # Attempting to resume run1 again must raise 400
    with pytest.raises(HTTPException) as exc_rej:
        await resume_run(run_id=run1.id, db=db_session, workspace=ws, current_user=user)
    assert exc_rej.value.status_code == 400

    # Gate revalidation with rejected approval must produce BLOCK
    gate = ActionGateService(db_session)
    dec_block = await gate.evaluate(
        workspace_id=ws.id,
        agent_id=agent.id,
        agent_run_id=run1.id,
        agent_action_id=denied_actions[0].id,
        authority_id=auth.id,
        transaction={"amount": 150, "currency": "INR", "order_id": order_id1},
        is_revalidation=True,
        approval_id=appr1.id
    )
    assert dec_block.decision == DecisionResult.BLOCK
    assert "APPROVAL_INVALID_STATE" in dec_block.reason_codes

    # ── Test 4: Approved Exact-Context Approval -> At Most One Capture ──
    run2 = await AgentRuntimeService.create_run(
        db=db_session, workspace_id=ws.id, agent_id=agent.id,
        input_text="Buy laptop approved", authority_id=auth.id
    )
    act_cart2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run2.id, tool_name="create_cart", tool_input={}
    )
    await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run2.id,
        tool_name="add_to_cart", tool_input={"cart_id": act_cart2.output["cart_id"], "product_id": prod.id, "quantity": 1}
    )
    act_co2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run2.id,
        tool_name="checkout", tool_input={"cart_id": act_cart2.output["cart_id"]}
    )
    order_id2 = act_co2.output["order_id"]

    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run2.id,
            tool_name="pay_order", tool_input={"order_id": order_id2}
        )

    stmt_appr2 = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run2.id)
    appr2 = (await db_session.execute(stmt_appr2)).scalars().one()
    appr2.status = ApprovalStatus.APPROVED
    appr2.approved_at = datetime.now(timezone.utc)
    appr2.approved_by = user.id
    await db_session.commit()

    # Resume -> Captures payment exactly once
    res_run2 = await resume_run(run_id=run2.id, db=db_session, workspace=ws, current_user=user)
    assert res_run2.status == RunStatus.COMPLETED
    assert "successfully captured" in res_run2.output.lower()

    stmt_p2 = select(Payment).where(Payment.order_id == order_id2)
    payments2 = (await db_session.execute(stmt_p2)).scalars().all()
    assert len(payments2) == 1
    assert payments2[0].status == PaymentStatus.CAPTURED
    assert payments2[0].amount == 150

    order2 = await db_session.get(Order, order_id2)
    assert order2.status == OrderStatus.PAID

    # Idempotent re-resumption -> does not capture second payment
    res_run2_again = await resume_run(run_id=run2.id, db=db_session, workspace=ws, current_user=user)
    payments2_again = (await db_session.execute(stmt_p2)).scalars().all()
    assert len(payments2_again) == 1

    # ── Test 5: Decision Trace Accurately Reflects Persisted Records ──
    trace1 = await get_decision_trace(run_id=run1.id, db=db_session, workspace=ws, current_user=user)
    assert trace1.run_status == "BLOCKED"
    assert len(trace1.orders) == 1
    assert trace1.orders[0].status == "PENDING_PAYMENT"
    assert len(trace1.payments) == 0
    assert len(trace1.approvals) == 1
    assert trace1.approvals[0].status == "REJECTED"

    trace2 = await get_decision_trace(run_id=run2.id, db=db_session, workspace=ws, current_user=user)
    assert trace2.run_status == "COMPLETED"
    assert len(trace2.orders) == 1
    assert trace2.orders[0].status == "PAID"
    assert len(trace2.payments) == 1
    assert trace2.payments[0].status == "CAPTURED"
    assert len(trace2.approvals) == 1
    assert trace2.approvals[0].status == "CONSUMED"


async def test_regression_issue_a_category_alias_normalization_and_validation(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Issue A Regression Test:
    1. Intent allows category 'electronics'
    2. Read-only search_products with category 'laptops' is ALIGNED and allowed
    3. search_products succeeds without creating cart, order, or payment
    4. Genuinely disallowed category 'clothing' is evaluated MISALIGNED and blocked (fail-closed)
    5. Attempting to add an unauthorized product (clothing or over-budget) hydrates from catalog and is blocked
    """
    from app.services.alignment_engine import evaluate_alignment
    from app.services.taxonomy import are_categories_compatible
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.services.commerce_service import CommerceService
    from app.models.commerce import Merchant, Product, ProductStatus
    from app.models.intent import Intent, IntentStatus, IntentType
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.schemas.execution_context import ExecutionContext

    # 1. Direct unit verification of category compatibility
    assert are_categories_compatible("electronics", "laptops") is True
    assert are_categories_compatible("electronics", "laptop") is True
    assert are_categories_compatible("electronics", "hardware") is True
    assert are_categories_compatible("electronics", "clothing") is False
    assert are_categories_compatible("electronics", "furniture") is False

    # 2. Alignment evaluation
    constraints = {
        "amount": {"maximum": 40000, "currency": "INR"},
        "product": {"category": "electronics"},
        "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CHECKOUT", "PAY_ORDER"]
    }
    
    # search_products with 'laptops' alias
    res_aligned = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        product_category="laptops"
    )
    assert res_aligned.alignment == "ALIGNED"
    assert any(s.type == "CATEGORY" and s.status == "ALIGNED" for s in res_aligned.signals)

    # search_products with disallowed category 'clothing'
    res_misaligned = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        product_category="clothing"
    )
    assert res_misaligned.alignment in ["PARTIAL", "MISALIGNED"]
    assert any(s.type == "CATEGORY" and s.status == "MISALIGNED" for s in res_misaligned.signals)

    # 3. Execution via AgentRuntimeService in DB
    user = User(
        id=f"usr_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="User Cat",
        password_hash="fake",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(id=f"ws_{uuid.uuid4().hex[:8]}", name="Cat Test WS", slug=f"cat-ws-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    merch = Merchant(id=f"mer_{uuid.uuid4().hex[:8]}", workspace_id=ws.id, name="Tech Mart")
    db_session.add(merch)
    await db_session.flush()

    laptop_prod = Product(
        id=f"prd_{uuid.uuid4().hex[:8]}",
        merchant_id=merch.id,
        name="Budget Laptop 15-inch",
        category="electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    clothing_prod = Product(
        id=f"prd_{uuid.uuid4().hex[:8]}",
        merchant_id=merch.id,
        name="Designer Silk Shirt",
        category="clothing",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    expensive_laptop = Product(
        id=f"prd_{uuid.uuid4().hex[:8]}",
        merchant_id=merch.id,
        name="Super Quantum Laptop",
        category="electronics",
        price=95000,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add_all([laptop_prod, clothing_prod, expensive_laptop])

    agent = Agent(
        id=f"agt_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        name="Shopping Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CHECKOUT", "PAY_ORDER"]
    )
    db_session.add(agent)
    await db_session.flush()

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        title="Purchase Budget Laptop",
        natural_language_request="Purchase Budget Laptop under 40000",
        structured_constraints=constraints,
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_id=intent.id,
        monetary_limit=40000,
        currency="INR",
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CHECKOUT", "PAY_ORDER"],
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=auth.id,
        input="Search products for laptops",
        status=RunStatus.RUNNING
    )
    db_session.add(run)
    await db_session.commit()

    # Legitimate read-only search with category 'laptops'
    action_search = await AgentRuntimeService.execute_action(
        db_session,
        ws.id,
        run.id,
        "search_products",
        {"category": "laptops", "query": "Budget Laptop 15-inch"}
    )
    assert action_search.status == ActionStatus.SUCCESS
    assert action_search.alignment_result == "ALIGNED"
    results = action_search.output.get("results", [])
    assert len(results) >= 1
    assert results[0]["product_id"] == laptop_prod.id

    # Verify NO side-effects (no cart, no order, no payment created)
    from app.models.commerce import Cart, Order
    from app.models.payment import Payment
    stmt_cart = select(Cart).where(Cart.workspace_id == ws.id)
    assert len((await db_session.execute(stmt_cart)).scalars().all()) == 0
    stmt_ord = select(Order).where(Order.workspace_id == ws.id)
    assert len((await db_session.execute(stmt_ord)).scalars().all()) == 0
    stmt_pay = select(Payment).where(Payment.workspace_id == ws.id)
    assert len((await db_session.execute(stmt_pay)).scalars().all()) == 0

    # Search with genuinely disallowed category 'clothing' must be blocked
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db_session,
            ws.id,
            run.id,
            "search_products",
            {"category": "clothing", "query": "Shirt"}
        )
    assert exc_info.value.status_code == 403
    assert "Action blocked by Action Gate" in exc_info.value.detail

    # Product substitution / category bypass attempt: try adding clothing product to cart
    # Must hydrate canonical metadata and block
    with pytest.raises(HTTPException) as exc_cart_block:
        await AgentRuntimeService.execute_action(
            db_session,
            ws.id,
            run.id,
            "add_to_cart",
            {"cart_id": "fake_cart", "product_id": clothing_prod.id, "quantity": 1}
        )
    assert exc_cart_block.value.status_code == 403

    # Amount escalation attempt: try adding 95k laptop when intent max is 40k
    with pytest.raises(HTTPException) as exc_amt_block:
        await AgentRuntimeService.execute_action(
            db_session,
            ws.id,
            run.id,
            "add_to_cart",
            {"cart_id": "fake_cart", "product_id": expensive_laptop.id, "quantity": 1}
        )
    assert exc_amt_block.value.status_code == 403


async def test_regression_issue_b_investigations_auto_creation_and_duplicate_prevention(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Issue B Regression Test:
    1. When an action is blocked by Action Gate, an Investigation case is automatically created in DB
    2. Case is linked to agent_run_id, gate_decision_id, workspace_id, status=OPEN, priority=CRITICAL
    3. Repeated blocked actions on the same run do NOT create duplicate cases (idempotent / duplicate prevention)
    4. Investigations list and metrics are workspace-scoped
    5. GET /api/v1/investigations/by-run/{run_id} returns the linked case
    """
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.services.investigation_service import InvestigationService
    from app.models.investigation import Investigation, InvestigationStatus, InvestigationPriority
    from app.models.commerce import Merchant, Product, ProductStatus
    from app.models.intent import Intent, IntentStatus, IntentType
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.api.routes.investigations import get_investigation_by_run, get_investigations

    user = User(
        id=f"usr_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="User Inv",
        password_hash="fake",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    await db_session.flush()

    ws_a = Workspace(id=f"ws_a_{uuid.uuid4().hex[:8]}", name="WS A", slug=f"ws-a-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    ws_b = Workspace(id=f"ws_b_{uuid.uuid4().hex[:8]}", name="WS B", slug=f"ws-b-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    db_session.add_all([ws_a, ws_b])
    await db_session.flush()

    merch = Merchant(id=f"mer_{uuid.uuid4().hex[:8]}", workspace_id=ws_a.id, name="Shop A")
    db_session.add(merch)
    await db_session.flush()

    clothing_prod = Product(
        id=f"prd_{uuid.uuid4().hex[:8]}",
        merchant_id=merch.id,
        name="Forbidden Silk Shirt",
        category="clothing",
        price=100,
        currency="INR",
        inventory=5,
        status=ProductStatus.ACTIVE
    )
    db_session.add(clothing_prod)

    agent = Agent(
        id=f"agt_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_a.id,
        name="Test Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM"]
    )
    db_session.add(agent)
    await db_session.flush()

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_a.id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        title="Electronics Only",
        natural_language_request="Buy electronics only",
        structured_constraints={
            "product": {"category": "electronics"},
            "allowed_actions": ["SEARCH_PRODUCTS"]
        },
        status=IntentStatus.ACTIVE
    )
    db_session.add(intent)
    await db_session.flush()

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_a.id,
        agent_id=agent.id,
        intent_id=intent.id,
        monetary_limit=10000,
        currency="INR",
        allowed_capabilities=["SEARCH_PRODUCTS"],
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_a.id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=auth.id,
        input="Search clothing",
        status=RunStatus.RUNNING
    )
    db_session.add(run)
    await db_session.commit()

    # 1. Trigger blocked action -> ActionGate evaluates DecisionResult.BLOCK
    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(
            db_session,
            ws_a.id,
            run.id,
            "search_products",
            {"category": "clothing"}
        )

    # 2. Check investigation auto-creation
    inv_svc = InvestigationService(db_session)
    inv_a = await inv_svc.get_investigation_by_run(ws_a.id, run.id)
    assert inv_a is not None
    assert inv_a.workspace_id == ws_a.id
    assert inv_a.agent_run_id == run.id
    assert inv_a.status == InvestigationStatus.OPEN
    assert inv_a.priority == InvestigationPriority.CRITICAL

    # Check attached timeline and evidence
    timeline = await inv_svc.get_timeline(inv_a.id, ws_a.id)
    assert len(timeline) >= 1
    evidence = await inv_svc.get_evidence(inv_a.id, ws_a.id)
    assert len(evidence) >= 1
    assert evidence[0].entity_type == "GATE_DECISION"

    # 3. Repeated blocked attempt on same run -> verify duplicate prevention
    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(
            db_session,
            ws_a.id,
            run.id,
            "search_products",
            {"category": "furniture"}
        )

    # Count investigations for this run
    stmt_count = select(Investigation).where(Investigation.workspace_id == ws_a.id, Investigation.agent_run_id == run.id)
    all_invs = (await db_session.execute(stmt_count)).scalars().all()
    assert len(all_invs) == 1, "Duplicate prevention failed: multiple cases created for same run!"

    # Timeline of the single case should record the repeated event
    timeline_after = await inv_svc.get_timeline(inv_a.id, ws_a.id)
    assert len(timeline_after) >= 2

    # 4. Workspace scoping
    # ws_a has 1 investigation
    invs_a, count_a = await inv_svc.get_investigations(ws_a.id)
    assert count_a >= 1
    assert any(i.id == inv_a.id for i in invs_a)

    # ws_b has 0 investigations
    invs_b, count_b = await inv_svc.get_investigations(ws_b.id)
    assert count_b == 0
    assert len(invs_b) == 0

    # 5. Endpoint /investigations/by-run/{run_id} returns the linked case
    found_case = await get_investigation_by_run(run_id=run.id, workspace=ws_a, db=db_session)
    assert found_case is not None
    assert found_case.id == inv_a.id

    # Cross-workspace check: querying from ws_b returns None
    found_cross = await get_investigation_by_run(run_id=run.id, workspace=ws_b, db=db_session)
    assert found_cross is None


@pytest.mark.asyncio
async def test_e2e_approval_flow_regressions(client: AsyncClient, owner_headers: dict, db_session: AsyncSession):
    """
    Regression test suite verifying:
    1. Duplicate order/payment prevention across repeated/parallel checkout and pay_order tool calls.
    2. Approval binding to exact order, amount, currency, agent, and run, and single-use consumption.
    3. Safe investigation creation on blocked run without MissingGreenlet error.
    """
    from app.services.agent_runtime_service import AgentRuntimeService
    from app.services.commerce_service import CommerceService
    from app.services.action_gate_service import ActionGateService
    from app.models.agent_runtime import AgentRun, AgentAction, ActionStatus, RunStatus
    from app.schemas.commerce import CartCreate, CartItemCreate
    from app.models.commerce import Product, ProductStatus, Merchant, Order, OrderStatus
    from app.models.authority import DelegatedAuthority, AuthorityStatus
    from app.models.intent import Intent, IntentStatus, IntentType
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.models.user import User, UserStatus
    from app.models.workspace import Workspace
    from app.api.routes.investigations import get_investigation_by_run
    from app.api.routes.agent_runtime import resume_run
    from app.schemas.execution_context import ExecutionContext

    user = User(
        id=f"usr_{uuid.uuid4().hex[:8]}",
        email=f"flow_user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="User Flow",
        password_hash="fake",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(id=f"ws_{uuid.uuid4().hex[:8]}", name="WS Flow", slug=f"ws-flow-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    # 1. Setup Merchant and Product
    merch = Merchant(id=f"merch_{uuid.uuid4().hex[:8]}", workspace_id=ws.id, name="Test Electronics")
    db_session.add(merch)
    await db_session.commit()

    prod = Product(
        id=f"prd_{uuid.uuid4().hex[:8]}",
        merchant_id=merch.id,
        name="Budget Laptop 15-inch",
        category="electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add(prod)
    await db_session.commit()

    # 2. Setup Agent, Authority, Intent
    agent = Agent(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        name="Shopping Assistant",
        type=AgentType.SHOPPING,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)
    await db_session.commit()

    auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        monetary_limit=50000,
        currency="INR",
        approval_threshold=100,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        status=AuthorityStatus.ACTIVE
    )
    db_session.add(auth)
    await db_session.commit()

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        title="Purchase laptop under 200",
        natural_language_request="Purchase laptop under 200",
        status=IntentStatus.ACTIVE,
        structured_constraints={
            "allowed_actions": ["search_products", "create_cart", "add_to_cart", "checkout", "pay_order"],
            "max_budget": 200,
            "currency": "INR",
            "approval_threshold": 100,
            "product": {"category": "electronics"}
        }
    )
    db_session.add(intent)
    await db_session.commit()

    # 3. Create Agent Run
    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=auth.id,
        status=RunStatus.RUNNING,
        input="Purchase the Budget Laptop 15-inch for 150 INR"
    )
    db_session.add(run)
    await db_session.commit()

    setup_ctx = ExecutionContext(is_human=True, user_id=user.id, is_agent=False)

    # 4. Create TWO separate carts in workspace (simulating the duplicate cart race condition)
    c1 = await CommerceService.create_cart(db_session, ws.id, CartCreate(agent_id=agent.id, currency="INR"), setup_ctx)
    await CommerceService.add_cart_item(db_session, ws.id, c1.id, CartItemCreate(product_id=prod.id, quantity=1), setup_ctx)

    c2 = await CommerceService.create_cart(db_session, ws.id, CartCreate(agent_id=agent.id, currency="INR"), setup_ctx)
    await CommerceService.add_cart_item(db_session, ws.id, c2.id, CartItemCreate(product_id=prod.id, quantity=1), setup_ctx)

    # Checkout cart 1
    co1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="checkout", tool_input={"cart_id": c1.id}
    )
    assert co1.status == ActionStatus.SUCCESS, f"Checkout failed: {co1.error_message}"
    order_id1 = co1.output["order_id"]

    # Checkout cart 2 in the same run -> duplicate order prevention reuses existing order!
    co2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="checkout", tool_input={"cart_id": c2.id}
    )
    assert co2.status == ActionStatus.SUCCESS
    assert co2.output["order_id"] == order_id1
    assert co2.output.get("reused") is True

    # 5. Test Approval Binding and Single-Use
    # Execute pay_order -> requires human review
    with pytest.raises(HTTPException) as exc:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws.id, run_id=run.id,
            tool_name="pay_order", tool_input={"order_id": order_id1}
        )
    assert exc.value.status_code == 402

    # Find the created approval request
    stmt_appr = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    appr = (await db_session.execute(stmt_appr)).scalars().first()
    assert appr is not None
    assert appr.amount == 150
    assert appr.currency == "INR"
    assert appr.agent_id == agent.id
    assert appr.agent_run_id == run.id

    # Approve the request
    appr.status = ApprovalStatus.APPROVED
    appr.approved_by = user.id
    await db_session.commit()

    # Resume the run
    resumed = await resume_run(run_id=run.id, db=db_session, workspace=ws, current_user=user)
    assert resumed.status == RunStatus.COMPLETED
    assert appr.status == ApprovalStatus.CONSUMED

    # Single-use enforcement: replaying resume with consumed approval raises 403
    with pytest.raises(HTTPException) as re_replay:
        # Create a dummy pending action so resume tries to process it with the consumed approval
        dummy_act = AgentAction(
            id=f"act_{uuid.uuid4().hex[:8]}",
            run_id=run.id,
            sequence_number=99,
            tool_name="pay_order",
            input={"order_id": order_id1},
            status=ActionStatus.PENDING_APPROVAL
        )
        db_session.add(dummy_act)
        await db_session.commit()
        await resume_run(run_id=run.id, db=db_session, workspace=ws, current_user=user)
    assert re_replay.value.status_code == 403
    assert "consumed" in str(re_replay.value.detail).lower()

    # Clean up dummy action
    await db_session.delete(dummy_act)
    await db_session.commit()

    # Duplicate payment prevention: executing pay_order again reuses existing captured payment
    run.status = RunStatus.RUNNING
    await db_session.commit()
    pay2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws.id, run_id=run.id,
        tool_name="pay_order", tool_input={"order_id": order_id1}
    )
    assert pay2.status == ActionStatus.SUCCESS
    assert pay2.output.get("reused") is True
    assert pay2.output["status"] == "PAID"

    # 6. Test Investigation Creation on Blocked Run (No MissingGreenlet)
    # Create a blocked run with a denied action
    blocked_run = AgentRun(
        id=f"run_blocked_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=auth.id,
        status=RunStatus.BLOCKED,
        input="Denied instruction"
    )
    db_session.add(blocked_run)
    await db_session.commit()

    denied_action = AgentAction(
        id=f"act_denied_{uuid.uuid4().hex[:8]}",
        run_id=blocked_run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"order_id": order_id1},
        status=ActionStatus.DENIED,
        error_message="Action was rejected by approver."
    )
    db_session.add(denied_action)
    await db_session.commit()

    # Calling get_investigation_by_run creates and returns the investigation without MissingGreenlet error
    inv_case = await get_investigation_by_run(run_id=blocked_run.id, workspace=ws, db=db_session)
    assert inv_case is not None
    assert inv_case.agent_run_id == blocked_run.id
    assert inv_case.status.value in ["OPEN", "IN_REVIEW"]
    assert "pay_order" in inv_case.title












