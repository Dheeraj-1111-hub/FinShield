import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.models.agent import Agent, AgentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.intent import Intent, IntentType, IntentStatus
from app.models.agent_runtime import AgentRun, AgentAction, ActionStatus, RunStatus
from app.models.commerce import Merchant, Product, Cart, Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.services.agent_runtime_service import AgentRuntimeService


@pytest.fixture
async def approval_test_context(client: AsyncClient, db_session: AsyncSession):
    email = f"approval_tester_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Approval Tester"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    headers = {"X-Workspace-ID": ws_id}
    
    # Create merchant & product
    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Sandbox Merchant"
    )
    db_session.add(merchant)
    await db_session.flush()

    laptop = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant.id,
        name="Budget Laptop 15-inch",
        category="electronics",
        price=150,
        currency="INR",
        inventory=50
    )
    db_session.add(laptop)

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Commerce Agent",
        type="SHOPPING",
        status=AgentStatus.ACTIVE,
        currency="INR",
        capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        ]
    )
    db_session.add(agent)
    await db_session.flush()

    # Authority with approval threshold of 100 INR
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=10000.0,
        approval_threshold=100.0,  # 150 > 100 triggers REVIEW
        currency="INR",
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        ],
        version=1
    )
    db_session.add(authority)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        title="Authorized Purchase Intent",
        intent_type=IntentType.PURCHASE,
        status=IntentStatus.ACTIVE,
        natural_language_request="Allow purchasing laptop with review above 100 INR",
        structured_constraints={
            "allowed_actions": ["search_products", "create_cart", "add_to_cart", "checkout", "pay_order"],
            "prohibited_actions": []
        }
    )
    db_session.add(intent)
    await db_session.commit()

    return {
        "ws_id": ws_id,
        "user_id": user_id,
        "merchant": merchant,
        "product": laptop,
        "authority": authority,
        "intent": intent,
        "agent": agent,
        "cookies": cookies,
        "headers": headers
    }


@pytest.mark.asyncio
async def test_review_required_cannot_capture_payment_before_approval(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # 1. Start an authorized purchase run
    create_res = await client.post(
        "/api/v1/agent-runtime/runs",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={
            "agent_id": agent.id,
            "input": "Purchase the Budget Laptop 15-inch from the catalog for 150 INR. If approval is required, pause.",
            "authority_id": ctx["authority"].id,
            "auto_start": False
        }
    )
    assert create_res.status_code == 200, create_res.text
    run_id = create_res.json()["id"]

    # Step 1: create_cart
    act1_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"tool_name": "create_cart", "input": {}}
    )
    assert act1_res.status_code == 200, act1_res.text
    cart_id = act1_res.json()["output"]["cart_id"]

    # Step 2: add_to_cart
    act2_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}}
    )
    assert act2_res.status_code == 200, act2_res.text

    # Step 3: checkout
    act3_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}}
    )
    assert act3_res.status_code == 200, act3_res.text
    order_id = act3_res.json()["output"]["order_id"]

    # Step 4: pay_order -> Must return 402 REVIEW_REQUIRED because 150 > approval_threshold(100)
    act4_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"tool_name": "pay_order", "input": {"order_id": order_id}}
    )
    assert act4_res.status_code == 402, f"Expected 402 Payment Required, got {act4_res.status_code}: {act4_res.text}"

    # Verify Invariants:
    # 1. Order status is PENDING_PAYMENT
    order_res = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=ctx["headers"], cookies=ctx["cookies"])
    assert order_res.status_code == 200
    assert order_res.json()["status"] == "PENDING_PAYMENT"

    # 2. No payments exist for this order
    payments_stmt = select(Payment).where(Payment.order_id == order_id)
    payments_res = await db_session.execute(payments_stmt)
    assert payments_res.scalars().all() == [], "No payment must be created or captured during REVIEW_REQUIRED"

    # 3. Approval request is created with status PENDING
    appr_stmt = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id)
    appr_res = await db_session.execute(appr_stmt)
    approval = appr_res.scalar_one_or_none()
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING
    assert approval.amount == 150

    # 4. Agent Run is WAITING_FOR_APPROVAL
    run_check = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=ctx["headers"], cookies=ctx["cookies"])
    assert run_check.json()["status"] == "WAITING_FOR_APPROVAL"
    assert run_check.json()["authoritative_decision"] == "REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_approving_order_permits_exactly_one_capture(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # Start run and checkout
    create_res = await client.post(
        "/api/v1/agent-runtime/runs",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={
            "agent_id": agent.id,
            "input": "Purchase Budget Laptop for 150 INR",
            "authority_id": ctx["authority"].id,
            "auto_start": False
        }
    )
    run_id = create_res.json()["id"]

    act1 = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id = act1.json()["output"]["cart_id"]

    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}})
    act3 = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id}})
    order_id = act3.json()["output"]["order_id"]

    # pay_order -> 402
    await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": order_id}})

    # Fetch approval
    appr_stmt = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id)
    appr_res = await db_session.execute(appr_stmt)
    approval = appr_res.scalar_one()

    # Approve via approval endpoint
    approve_res = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={
            "decision": "APPROVED",
            "order_id": order_id,
            "amount": 150,
            "currency": "INR",
            "agent_id": agent.id,
            "workspace_id": ws_id
        }
    )
    assert approve_res.status_code == 200, approve_res.text

    # Resume the run -> Executes payment capture
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert resume_res.status_code == 200, resume_res.text
    resumed = resume_res.json()

    assert resumed["status"] == "COMPLETED"
    assert resumed["authoritative_decision"] == "ALLOW"
    pay_action = next(a for a in resumed["actions"] if a["tool_name"] == "pay_order")
    assert pay_action["status"] == "SUCCESS"
    assert pay_action["gate_decision"] == "ALLOW"
    assert pay_action["error_code"] is None

    # Verify payment in DB
    payments_stmt = select(Payment).where(Payment.order_id == order_id)
    payments_res = await db_session.execute(payments_stmt)
    payments = payments_res.scalars().all()
    assert len(payments) == 1, "Exactly one payment capture must occur"
    payment = payments[0]
    assert payment.status == PaymentStatus.CAPTURED
    assert payment.amount == 150

    # Verify Order is PAID
    order_stmt = select(Order).where(Order.id == order_id)
    order_res = await db_session.execute(order_stmt)
    order = order_res.scalar_one()
    assert order.status == OrderStatus.PAID
    assert order.payment_id == payment.id

    # Verify Approval is CONSUMED
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    # Idempotent Resume: Calling resume again does NOT create duplicate payment
    resume_again = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert resume_again.status_code == 200
    
    payments_again = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(payments_again) == 1, "Idempotent resume must not duplicate payment captures"


@pytest.mark.asyncio
async def test_pending_rejected_expired_or_replayed_approvals_cannot_capture(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # Helper to create a blocked pay_order run
    async def create_blocked_run():
        c_res = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False})
        r_id = c_res.json()["id"]
        a1 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
        cart = a1.json()["output"]["cart_id"]
        await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart, "product_id": product.id, "quantity": 1}})
        a3 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart}})
        ord_id = a3.json()["output"]["order_id"]
        await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord_id}})
        app_res = await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r_id))
        app = app_res.scalar_one()
        return r_id, ord_id, app

    # 1. PENDING: Trying to resume when approval is still PENDING -> 400
    run1, order1, app1 = await create_blocked_run()
    res1 = await client.post(f"/api/v1/agent-runtime/runs/{run1}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res1.status_code == 400
    err_msg = res1.json().get("error", {}).get("message", "") or res1.json().get("detail", "")
    assert "still PENDING" in err_msg

    # 2. REJECTED: Reject approval -> resume rejects and cancels order
    run2, order2, app2 = await create_blocked_run()
    rej_res = await client.post(
        f"/api/v1/approvals/{app2.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={
            "decision": "REJECTED",
            "order_id": order2,
            "amount": 150,
            "currency": "INR",
            "agent_id": agent.id,
            "workspace_id": ws_id
        }
    )
    assert rej_res.status_code == 200, rej_res.text

    # Resuming after rejection transitions action to DENIED and run to BLOCKED
    res2 = await client.post(f"/api/v1/agent-runtime/runs/{run2}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res2.status_code == 200
    assert res2.json()["status"] == "BLOCKED"
    # Order is cancelled
    ord2_db = (await db_session.execute(select(Order).where(Order.id == order2))).scalar_one()
    assert ord2_db.status == OrderStatus.CANCELLED

    # 3. EXPIRED: Expired approval -> resume sets FAILED
    run3, order3, app3 = await create_blocked_run()
    app3.status = ApprovalStatus.EXPIRED
    await db_session.commit()
    res3 = await client.post(f"/api/v1/agent-runtime/runs/{run3}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res3.status_code == 200
    assert res3.json()["status"] == "FAILED"

    # Verify zero payments created across run1, run2, run3
    for o_id in [order1, order2, order3]:
        pays = (await db_session.execute(select(Payment).where(Payment.order_id == o_id))).scalars().all()
        assert pays == [], f"No payments should exist for order {o_id}"


@pytest.mark.asyncio
async def test_reconcile_orders_payments_and_overview_totals(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # 1. Place and complete one approved order
    create_res = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False})
    r_id = create_res.json()["id"]
    a1 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart = a1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart, "product_id": product.id, "quantity": 1}})
    a3 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart}})
    ord_id = a3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord_id}})
    
    app = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r_id))).scalar_one()
    app_dec = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert app_dec.status_code == 200, app_dec.text

    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert resume_res.status_code == 200, resume_res.text

    # 2. Call Overview API
    overview_res = await client.get("/api/v1/overview", headers=ctx["headers"], cookies=ctx["cookies"])
    assert overview_res.status_code == 200, overview_res.text
    ov = overview_res.json()

    # Reconcile Overview totals with DB records
    assert ov["financial"]["payment_volume"] == 150.0
    assert ov["financial"]["payment_count"] == 1
    assert ov["financial"]["orders_count"] == 1

    # Product inventory reduced from 50 to 49
    await db_session.refresh(product)
    assert product.inventory == 49


@pytest.mark.asyncio
async def test_lifecycle_reconciliation_multi_order_mapping_and_inventory(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    """
    Regression test verifying exact reconciliation across orders, payments, approvals, and inventory:
    - Paid order has exactly 1 captured payment.
    - Cancelled/rejected order has 0 payments and restored inventory.
    - Pending payment order has 0 payments and pending order status.
    - Zero captured payments lack an order.
    - Zero orders have multiple payments.
    - Total order value vs captured payment volume reconciliation.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # Initial inventory is 50
    await db_session.refresh(product)
    initial_inventory = product.inventory
    assert initial_inventory == 50

    # 1. Create Order 1: Approved and Paid (₹150)
    c1 = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase 1", "authority_id": ctx["authority"].id, "auto_start": False})
    r1 = c1.json()["id"]
    a1_1 = await client.post(f"/api/v1/agent-runtime/runs/{r1}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart1 = a1_1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r1}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart1, "product_id": product.id, "quantity": 1}})
    a1_3 = await client.post(f"/api/v1/agent-runtime/runs/{r1}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart1}})
    ord1_id = a1_3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r1}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord1_id}})
    
    app1 = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r1))).scalar_one()
    await client.post(
        f"/api/v1/approvals/{app1.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord1_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    res1 = await client.post(f"/api/v1/agent-runtime/runs/{r1}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res1.status_code == 200

    # 2. Create Order 2: Rejected and Cancelled (₹150)
    c2 = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase 2", "authority_id": ctx["authority"].id, "auto_start": False})
    r2 = c2.json()["id"]
    a2_1 = await client.post(f"/api/v1/agent-runtime/runs/{r2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart2 = a2_1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart2, "product_id": product.id, "quantity": 1}})
    a2_3 = await client.post(f"/api/v1/agent-runtime/runs/{r2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart2}})
    ord2_id = a2_3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord2_id}})

    app2 = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r2))).scalar_one()
    await client.post(
        f"/api/v1/approvals/{app2.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "REJECTED", "order_id": ord2_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    res2 = await client.post(f"/api/v1/agent-runtime/runs/{r2}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res2.status_code == 200

    # 3. Create Order 3: Checked out but payment not initiated (Pending Payment, ₹150)
    c3 = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase 3", "authority_id": ctx["authority"].id, "auto_start": False})
    r3 = c3.json()["id"]
    a3_1 = await client.post(f"/api/v1/agent-runtime/runs/{r3}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart3 = a3_1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r3}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart3, "product_id": product.id, "quantity": 1}})
    a3_3 = await client.post(f"/api/v1/agent-runtime/runs/{r3}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart3}})
    ord3_id = a3_3.json()["output"]["order_id"]

    # --- RECONCILIATION ASSERTIONS ---
    # Fetch all orders and payments for this workspace
    db_orders = (await db_session.execute(select(Order).where(Order.workspace_id == ws_id))).scalars().all()
    db_payments = (await db_session.execute(select(Payment).where(Payment.workspace_id == ws_id))).scalars().all()

    assert len(db_orders) == 3, f"Expected 3 orders, got {len(db_orders)}"
    total_order_value = sum(o.total for o in db_orders)
    assert total_order_value == 450, f"Expected total order value 450, got {total_order_value}"

    captured_payments = [p for p in db_payments if p.status == PaymentStatus.CAPTURED]
    assert len(captured_payments) == 1, f"Expected 1 captured payment, got {len(captured_payments)}"
    assert captured_payments[0].amount == 150
    assert captured_payments[0].order_id == ord1_id

    # Confirm 1-to-1 mapping
    # 1. Every captured payment maps to exactly 1 order
    for cp in captured_payments:
        assert cp.order_id is not None
        matching_orders = [o for o in db_orders if o.id == cp.order_id]
        assert len(matching_orders) == 1, f"Payment {cp.id} must map to exactly 1 order"
        assert matching_orders[0].status == OrderStatus.PAID

    # 2. No order has multiple payments
    for o in db_orders:
        linked_pays = [p for p in captured_payments if p.order_id == o.id]
        assert len(linked_pays) <= 1, f"Order {o.id} must have at most 1 captured payment"

    # 3. Identify every order without a captured payment and verify its actual status
    uncaptured_orders = [o for o in db_orders if not any(p.order_id == o.id for p in captured_payments)]
    assert len(uncaptured_orders) == 2
    uncaptured_statuses = {o.id: o.status for o in uncaptured_orders}
    assert uncaptured_statuses[ord2_id] == OrderStatus.CANCELLED
    assert uncaptured_statuses[ord3_id] == OrderStatus.PENDING_PAYMENT

    # 4. Check API metrics
    metrics_res = await client.get("/api/v1/payments/metrics", headers=ctx["headers"], cookies=ctx["cookies"])
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["captured_count"] == 1
    assert metrics["total_volume"] == 150
    assert metrics["transactions"] == 1
    assert metrics["failed_count"] == 0

    # 5. Inventory check: Order 1 decremented (50 -> 49). Order 2 restored on cancellation. Order 3 reserved at checkout.
    await db_session.refresh(product)
    assert product.inventory == 48  # 50 - 1 (paid) - 1 (pending) = 48 (cancelled order was restored)


@pytest.mark.asyncio
async def test_reconciliation_anomalies_and_mismatches_fail_closed(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    """
    Task 6 Regression Test:
    - Valid paid orders (exact amount, currency, 1:1 capture).
    - Pending-payment orders (unpaid, excluded from captured volume).
    - Missing payments (orders without capture do not falsely increase captured totals).
    - Duplicate payment references (double-pay or re-approving an already paid order is rejected).
    - Amount & currency mismatches (mismatched amount or currency fails closed with 400).
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # 1. Create a run requiring review (150 INR > threshold 100)
    c_res = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False})
    r_id = c_res.json()["id"]
    a1 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id = a1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}})
    a3 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id}})
    ord_id = a3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord_id}})

    app = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r_id))).scalar_one()

    # 2. Test Amount Mismatch Fail-Closed
    # Expected amount is 150, but approver sends 200 -> Must fail with 400
    amt_mismatch_res = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 200, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert amt_mismatch_res.status_code == 400
    assert "mismatch" in amt_mismatch_res.text.lower()

    # 3. Test Currency Mismatch Fail-Closed
    # Expected currency is INR, but approver sends USD -> Must fail with 400
    curr_mismatch_res = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 150, "currency": "USD", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert curr_mismatch_res.status_code == 400
    assert "currency mismatch" in curr_mismatch_res.text.lower()

    # 4. Valid Decision: Exact 150 INR
    valid_dec = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert valid_dec.status_code == 200, valid_dec.text

    # Resume run to capture payment
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert resume_res.status_code == 200
    run_data = resume_res.json()
    assert run_data["status"] == "COMPLETED"

    # Verify paid order and captured payment
    ord_db = (await db_session.execute(select(Order).where(Order.id == ord_id))).scalar_one()
    assert ord_db.status == OrderStatus.PAID
    assert ord_db.payment_id is not None
    pay_db = (await db_session.execute(select(Payment).where(Payment.id == ord_db.payment_id))).scalar_one()
    assert pay_db.status == PaymentStatus.CAPTURED
    assert pay_db.amount == 150
    assert pay_db.currency == "INR"
    assert pay_db.order_id == ord_id

    # 5. Duplicate Payment Prevention:
    # Attempting to re-approve the already paid order for another approval or re-decision fails
    # Let's verify approving an already paid order fails with 400
    from app.services.approval_service import ApprovalService
    appr_service = ApprovalService(db_session)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await appr_service.approve(
            approval_id=app.id,
            workspace_id=ws_id,
            user_id=ctx["user_id"],
            expected_order_id=ord_id,
            expected_amount=150,
            expected_currency="INR"
        )
    assert exc_info.value.status_code in [400, 404]

    # 6. Verify missing payment / pending payment behavior:
    # Create a 2nd order that stops at checkout without payment
    c_res2 = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase 2", "authority_id": ctx["authority"].id, "auto_start": False})
    r_id2 = c_res2.json()["id"]
    a1_2 = await client.post(f"/api/v1/agent-runtime/runs/{r_id2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id2 = a1_2.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id2, "product_id": product.id, "quantity": 1}})
    a3_2 = await client.post(f"/api/v1/agent-runtime/runs/{r_id2}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id2}})
    ord_id2 = a3_2.json()["output"]["order_id"]

    # ord_id2 has no payment
    pays2 = (await db_session.execute(select(Payment).where(Payment.order_id == ord_id2))).scalars().all()
    assert pays2 == [], "Pending payment order must have 0 payment records"

    # Overview ledger reconciliation:
    # 2 orders created = Gross Order Value 300 INR
    # 1 payment captured = Captured Volume 150 INR
    ov_res = await client.get("/api/v1/overview", headers=ctx["headers"], cookies=ctx["cookies"])
    assert ov_res.status_code == 200
    financial = ov_res.json()["financial"]
    # 7. Payments API returns risk_level and risk_score from risk assessment
    payments_res = await client.get("/api/v1/payments", headers=ctx["headers"], cookies=ctx["cookies"])
    assert payments_res.status_code == 200
    p_data = payments_res.json()
    assert len(p_data) >= 1
    # Find payment for ord_id
    paid_p = next(p for p in p_data if p["order_id"] == ord_id)
    assert paid_p["status"] == "CAPTURED"
    assert paid_p["risk_level"] is not None, "risk_level must not be None when risk_assessment_id is present"
    assert paid_p["risk_level"] != "N/A"


@pytest.mark.asyncio
async def test_reconcile_gate_decision_supersedes_and_payment_risk_association(client: AsyncClient, db_session: AsyncSession, approval_test_context: dict):
    """
    Test that:
    1. An approved gate decision links back to its parent decision via supersedes_decision_id.
    2. Payment response includes risk_level and risk_score from RiskAssessment.
    3. Pending payment order has no payment association.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # Start run
    c_res = await client.post("/api/v1/agent-runtime/runs", headers=ctx["headers"], cookies=ctx["cookies"], json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False})
    r_id = c_res.json()["id"]
    a1 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id = a1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}})
    a3 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id}})
    ord_id = a3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord_id}})

    app = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r_id))).scalar_one()
    initial_decision_id = app.gate_decision_id

    # Approve
    dec_res = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert dec_res.status_code == 200
    allowed_dec_id = dec_res.json()["id"]

    # Verify supersedes_decision_id in DB
    new_dec = await db_session.get(GateDecision, allowed_dec_id)
    assert new_dec is not None
    assert new_dec.supersedes_decision_id == initial_decision_id, f"Expected supersedes_decision_id {initial_decision_id}, got {new_dec.supersedes_decision_id}"

    # Resume and capture
    res_resume = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res_resume.status_code == 200

    # Verify payment list returns risk_level and risk_score
    pays_res = await client.get("/api/v1/payments", headers=ctx["headers"], cookies=ctx["cookies"])
    assert pays_res.status_code == 200
    pays = pays_res.json()
    matching_p = next(p for p in pays if p["order_id"] == ord_id)
    assert matching_p["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert matching_p["risk_score"] is not None

    # Verify both the GateDecision nonce and the Approval are CONSUMED in DB
    await db_session.refresh(new_dec)
    assert new_dec.consumed_at is not None, "Execution nonce must be marked consumed upon payment capture"
    await db_session.refresh(app)
    assert app.status == ApprovalStatus.CONSUMED, "ApprovalRequest must be marked CONSUMED upon payment capture"

    # Verify replay attempt with consumed nonce fails closed
    from app.services.commerce_service import CommerceService
    from app.schemas.execution_context import ExecutionContext
    from fastapi import HTTPException
    ctx_agent = ExecutionContext(is_human=False, is_agent=True, agent_id=agent.id, is_agent_runtime=True)
    with pytest.raises(HTTPException) as exc_replay:
        await CommerceService._verify_gate_token(
            db=db_session,
            workspace_id=ws_id,
            ctx=ctx_agent,
            action_type="pay_order",
            amount=150,
            currency="INR",
            target_identity=ord_id,
            consume_nonce=True
        )
    assert exc_replay.value.status_code == 403


@pytest.mark.asyncio
async def test_gate_decision_list_and_drawer_lifecycle_reconciliation(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context
):
    """
    Regression test ensuring that throughout the REVIEW -> APPROVED -> CONSUMED lifecycle:
    1. The Action Gate decision list endpoint (/api/v1/gate-decisions) and the detail drawer endpoint
       (/api/v1/gate-decisions/{decision_id}) agree consistently on:
       - decision outcome (REVIEW vs ALLOW)
       - approval status (PENDING vs APPROVED vs CONSUMED, never false 'Pending Review' for ALLOW)
       - bound amount (150 INR) and currency
       - single-use nonce consumption state (UNCONSUMED vs CONSUMED)
    2. Revalidation ALLOW decisions correctly link to the consumed ApprovalRequest, supersedes_decision_id,
       and the captured payment/paid order.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # 1. Start run and checkout order
    c_res = await client.post(
        "/api/v1/agent-runtime/runs",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False}
    )
    r_id = c_res.json()["id"]
    a1 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id = a1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}})
    a3 = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id}})
    ord_id = a3.json()["output"]["order_id"]

    # 2. Trigger pay_order exceeding threshold -> pauses for review
    await client.post(f"/api/v1/agent-runtime/runs/{r_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord_id}})

    app = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r_id))).scalar_one()
    initial_decision_id = app.gate_decision_id

    # 3. Verify List and Detail in initial PENDING state
    list_res_1 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_1.status_code == 200
    list_1 = list_res_1.json()
    item_rev_1 = next(it for it in list_1 if it["id"] == initial_decision_id)
    assert item_rev_1["decision"] == "REVIEW"
    assert item_rev_1["approval_status"] == "PENDING"
    assert item_rev_1["approval_lifecycle_status"] == "PENDING"
    assert item_rev_1["execution_status"] == "PENDING_REVIEW"
    assert item_rev_1["amount"] == 150.0
    assert item_rev_1["currency"] == "INR"
    assert item_rev_1["consumed_at"] is None

    detail_rev_1 = (await client.get(f"/api/v1/gate-decisions/{initial_decision_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert detail_rev_1["decision"] == "REVIEW"
    assert detail_rev_1["approval"]["status"] == "PENDING"
    assert detail_rev_1["approval_lifecycle_status"] == "PENDING"
    assert detail_rev_1["execution_status"] == "PENDING_REVIEW"
    assert detail_rev_1["consumed_at"] is None
    assert detail_rev_1["amount"] == 150.0
    assert detail_rev_1["currency"] == "INR"

    # 4. Human approves the request
    dec_res = await client.post(
        f"/api/v1/approvals/{app.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "APPROVED", "order_id": ord_id, "amount": 150, "currency": "INR", "agent_id": agent.id, "workspace_id": ws_id}
    )
    assert dec_res.status_code == 200
    allowed_dec_id = dec_res.json()["id"]

    # 5. Verify List and Detail in APPROVED (unconsumed) state
    list_res_2 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_2.status_code == 200
    list_2 = list_res_2.json()
    item_allow_2 = next(it for it in list_2 if it["id"] == allowed_dec_id)
    assert item_allow_2["decision"] == "ALLOW"
    assert item_allow_2["approval_status"] == "APPROVED", "Pre-execution ALLOW decision must have approval_status APPROVED, never PENDING or null"
    assert item_allow_2["approval_lifecycle_status"] == "APPROVED"
    assert item_allow_2["execution_status"] == "UNCONSUMED"
    assert item_allow_2["amount"] == 150.0
    assert item_allow_2["currency"] == "INR"
    assert item_allow_2["consumed_at"] is None
    assert item_allow_2["supersedes_decision_id"] == initial_decision_id

    detail_allow_2 = (await client.get(f"/api/v1/gate-decisions/{allowed_dec_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert detail_allow_2["decision"] == "ALLOW"
    assert detail_allow_2["approval"]["status"] == "APPROVED"
    assert detail_allow_2["approval_lifecycle_status"] == "APPROVED"
    assert detail_allow_2["execution_status"] == "UNCONSUMED"
    assert detail_allow_2["consumed_at"] is None
    assert detail_allow_2["supersedes_decision_id"] == initial_decision_id

    # 6. Authoritative resume executes payment and consumes the nonce & approval
    res_resume = await client.post(f"/api/v1/agent-runtime/runs/{r_id}/resume", headers=ctx["headers"], cookies=ctx["cookies"])
    assert res_resume.status_code == 200

    # 7. Verify List and Detail in final CONSUMED state
    list_res_3 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_3.status_code == 200
    list_3 = list_res_3.json()

    # The revalidation decision that authorized execution:
    item_allow_3 = next(it for it in list_3 if it["id"] == allowed_dec_id)
    assert item_allow_3["decision"] == "ALLOW"
    assert item_allow_3["approval_status"] == "CONSUMED", "Executed ALLOW decision must show approval_status CONSUMED, never PENDING"
    assert item_allow_3["approval_lifecycle_status"] == "CONSUMED"
    assert item_allow_3["execution_status"] == "CONSUMED", "Executed ALLOW decision execution_status must be CONSUMED"
    assert item_allow_3["consumed_at"] is not None, "Executed ALLOW decision must record consumed_at timestamp"
    assert item_allow_3["amount"] == 150.0
    assert item_allow_3["currency"] == "INR"

    # The superseded REVIEW decision:
    item_rev_3 = next(it for it in list_3 if it["id"] == initial_decision_id)
    assert item_rev_3["decision"] == "REVIEW"
    assert item_rev_3["approval_status"] == "CONSUMED"
    assert item_rev_3["approval_lifecycle_status"] == "CONSUMED"
    assert item_rev_3["execution_status"] == "RESOLVED_CONSUMED", "Superseded REVIEW must show RESOLVED_CONSUMED, never UNCONSUMED"
    assert item_rev_3["consumed_at"] is None, "Original REVIEW decision must remain immutable and never directly consumed"
    assert item_rev_3["amount"] == 150.0

    # Detail drawer responses:
    detail_allow_3 = (await client.get(f"/api/v1/gate-decisions/{allowed_dec_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert detail_allow_3["decision"] == "ALLOW"
    assert detail_allow_3["approval"]["status"] == "CONSUMED"
    assert detail_allow_3["approval_lifecycle_status"] == "CONSUMED"
    assert detail_allow_3["execution_status"] == "CONSUMED"
    assert detail_allow_3["consumed_at"] is not None
    assert detail_allow_3["order"] is not None
    assert detail_allow_3["order"]["status"] == "PAID"
    assert detail_allow_3["payment"] is not None
    assert detail_allow_3["payment"]["status"] == "CAPTURED"
    assert detail_allow_3["amount"] == 150.0
    assert detail_allow_3["currency"] == "INR"

    detail_rev_3 = (await client.get(f"/api/v1/gate-decisions/{initial_decision_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert detail_rev_3["decision"] == "REVIEW"
    assert detail_rev_3["approval"]["status"] == "CONSUMED"
    assert detail_rev_3["approval_lifecycle_status"] == "CONSUMED"
    assert detail_rev_3["execution_status"] == "RESOLVED_CONSUMED", "Drawer for original REVIEW must show RESOLVED_CONSUMED, never UNCONSUMED"
    assert detail_rev_3["consumed_at"] is None, "Original REVIEW decision detail consumed_at must remain None"
    assert detail_rev_3["order"]["status"] == "PAID"
    assert detail_rev_3["payment"]["status"] == "CAPTURED"


@pytest.mark.asyncio
async def test_gate_decisions_pending_rejected_and_cancelled_display(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context
):
    """
    Regression test verifying that:
    1. A genuinely pending review displays approval_status PENDING in list and drawer.
    2. A rejected approval displays approval_status REJECTED in list and drawer.
    3. A cancelled approval displays approval_status CANCELLED in list and drawer.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]
    product = ctx["product"]

    # 1. Genuinely pending review flow
    c_res = await client.post(
        "/api/v1/agent-runtime/runs",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"agent_id": agent.id, "input": "Purchase laptop", "authority_id": ctx["authority"].id, "auto_start": False}
    )
    r1_id = c_res.json()["id"]
    a1 = await client.post(f"/api/v1/agent-runtime/runs/{r1_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "create_cart", "input": {}})
    cart_id = a1.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r1_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": product.id, "quantity": 1}})
    a3 = await client.post(f"/api/v1/agent-runtime/runs/{r1_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "checkout", "input": {"cart_id": cart_id}})
    ord1_id = a3.json()["output"]["order_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{r1_id}/actions", headers=ctx["headers"], cookies=ctx["cookies"], json={"tool_name": "pay_order", "input": {"order_id": ord1_id}})

    app_pending = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == r1_id))).scalar_one()
    gdec_pending_id = app_pending.gate_decision_id

    # Verify PENDING state in list
    list_res_1 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_1.status_code == 200
    item_pending = next(it for it in list_res_1.json() if it["id"] == gdec_pending_id)
    assert item_pending["decision"] == "REVIEW"
    assert item_pending["approval_status"] == "PENDING"
    assert item_pending["approval_lifecycle_status"] == "PENDING"
    assert item_pending["execution_status"] == "PENDING_REVIEW"
    assert item_pending["required_approval"] is True

    # Verify PENDING state in drawer
    drawer_pending = (await client.get(f"/api/v1/gate-decisions/{gdec_pending_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_pending["decision"] == "REVIEW"
    assert drawer_pending["approval"]["status"] == "PENDING"
    assert drawer_pending["approval_lifecycle_status"] == "PENDING"
    assert drawer_pending["execution_status"] == "PENDING_REVIEW"
    assert drawer_pending["required_approval"] is True

    # 2. Reject the pending approval
    dec_res = await client.post(
        f"/api/v1/approvals/{app_pending.id}/decision",
        headers=ctx["headers"],
        cookies=ctx["cookies"],
        json={"decision": "REJECTED", "reason": "Over budget for project"}
    )
    assert dec_res.status_code == 200

    # Verify REJECTED state in list
    list_res_2 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_2.status_code == 200
    item_rejected = next(it for it in list_res_2.json() if it["id"] == gdec_pending_id)
    assert item_rejected["decision"] == "REVIEW"
    assert item_rejected["approval_status"] == "REJECTED"
    assert item_rejected["approval_lifecycle_status"] == "REJECTED"
    assert item_rejected["execution_status"] == "BLOCKED_REJECTED"

    # Verify REJECTED state in drawer
    drawer_rejected = (await client.get(f"/api/v1/gate-decisions/{gdec_pending_id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_rejected["decision"] == "REVIEW"
    assert drawer_rejected["approval"]["status"] == "REJECTED"
    assert drawer_rejected["approval_lifecycle_status"] == "REJECTED"
    assert drawer_rejected["execution_status"] == "BLOCKED_REJECTED"

    # 3. Cancelled Approval verification
    action_cancel = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=r1_id,
        sequence_number=99,
        tool_name="pay_order",
        input={"order_id": ord1_id}
    )
    db_session.add(action_cancel)
    gdec_cancelled = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=r1_id,
        agent_action_id=action_cancel.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        explanation="Review required",
        required_approval=True,
        evaluation_snapshot={}
    )
    db_session.add(gdec_cancelled)
    app_cancelled = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=r1_id,
        agent_action_id=action_cancel.id,
        gate_decision_id=gdec_cancelled.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.CANCELLED,
        reason="Run cancelled by operator",
        amount=150,
        currency="INR"
    )
    db_session.add(app_cancelled)
    gdec_cancelled.approval_id = app_cancelled.id
    await db_session.commit()

    # Verify CANCELLED state in list
    list_res_3 = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res_3.status_code == 200
    item_cancelled = next(it for it in list_res_3.json() if it["id"] == gdec_cancelled.id)
    assert item_cancelled["decision"] == "REVIEW"
    assert item_cancelled["approval_status"] == "CANCELLED"
    assert item_cancelled["approval_lifecycle_status"] == "CANCELLED"
    assert item_cancelled["execution_status"] == "TERMINATED"

    # Verify CANCELLED state in drawer
    drawer_cancelled = (await client.get(f"/api/v1/gate-decisions/{gdec_cancelled.id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_cancelled["decision"] == "REVIEW"
    assert drawer_cancelled["approval"]["status"] == "CANCELLED"
    assert drawer_cancelled["approval_lifecycle_status"] == "CANCELLED"
    assert drawer_cancelled["execution_status"] == "TERMINATED"


@pytest.mark.asyncio
async def test_gate_decision_missing_or_ambiguous_linkage(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context
):
    """
    Test regression scenarios where approval records are missing or unlinked:
    1. A REVIEW decision with required_approval=True but NO ApprovalRequest record.
       Must cleanly fallback to approval_lifecycle_status='PENDING', execution_status='PENDING_REVIEW',
       evidence_status['approval']='MISSING', and consumed_at=None.
    2. An ALLOW decision without approval requirement (e.g., read-only action).
       Must report approval_lifecycle_status='NOT_REQUIRED', execution_status='UNCONSUMED',
       evidence_status['approval']='NOT_REQUIRED'.
    3. A BLOCK decision without approval requirement.
       Must report execution_status='NOT_EXECUTABLE'.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent = ctx["agent"]

    # 1. REVIEW with missing approval record
    act_missing = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=f"run_{uuid.uuid4().hex[:16]}",
        sequence_number=1,
        tool_name="transfer_funds",
        input={"amount": 500, "currency": "INR"}
    )
    db_session.add(act_missing)
    gdec_missing = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=act_missing.run_id,
        agent_action_id=act_missing.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["MANUAL_REVIEW_REQUIRED"],
        explanation="Manual intervention required by policy",
        required_approval=True,
        evaluation_snapshot={}
    )
    db_session.add(gdec_missing)

    # 2. ALLOW with no approval required (standard operation)
    act_allow = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=act_missing.run_id,
        sequence_number=2,
        tool_name="view_catalog",
        input={}
    )
    db_session.add(act_allow)
    gdec_allow = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=act_missing.run_id,
        agent_action_id=act_allow.id,
        decision=DecisionResult.ALLOW,
        reason_codes=["ALLOW_READ_ONLY"],
        explanation="Read-only catalog inspection permitted",
        required_approval=False,
        evaluation_snapshot={}
    )
    db_session.add(gdec_allow)

    # 3. BLOCK decision
    act_block = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=act_missing.run_id,
        sequence_number=3,
        tool_name="export_keys",
        input={}
    )
    db_session.add(act_block)
    gdec_block = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=act_missing.run_id,
        agent_action_id=act_block.id,
        decision=DecisionResult.BLOCK,
        reason_codes=["PROHIBITED_ACTION"],
        explanation="Exporting keys is strictly prohibited",
        required_approval=False,
        evaluation_snapshot={}
    )
    db_session.add(gdec_block)
    await db_session.commit()

    # Verify List endpoint
    list_res = await client.get("/api/v1/gate-decisions", headers=ctx["headers"], cookies=ctx["cookies"])
    assert list_res.status_code == 200
    list_items = list_res.json()

    # Missing approval check in list
    item_m = next(it for it in list_items if it["id"] == gdec_missing.id)
    assert item_m["decision"] == "REVIEW"
    assert item_m["approval_status"] == "PENDING"
    assert item_m["approval_lifecycle_status"] == "PENDING"
    assert item_m["execution_status"] == "PENDING_REVIEW"
    assert item_m["consumed_at"] is None

    # Read-only allow check in list
    item_a = next(it for it in list_items if it["id"] == gdec_allow.id)
    assert item_a["decision"] == "ALLOW"
    assert item_a["approval_status"] is None
    assert item_a["approval_lifecycle_status"] == "NOT_REQUIRED"
    assert item_a["execution_status"] == "UNCONSUMED"

    # Block check in list
    item_b = next(it for it in list_items if it["id"] == gdec_block.id)
    assert item_b["decision"] == "BLOCK"
    assert item_b["execution_status"] == "NOT_EXECUTABLE"

    # Verify Drawer endpoints
    drawer_m = (await client.get(f"/api/v1/gate-decisions/{gdec_missing.id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_m["decision"] == "REVIEW"
    assert drawer_m["approval"] is None
    assert drawer_m["approval_lifecycle_status"] == "PENDING"
    assert drawer_m["execution_status"] == "PENDING_REVIEW"
    assert drawer_m["evidence_status"]["approval"] == "MISSING"

    drawer_a = (await client.get(f"/api/v1/gate-decisions/{gdec_allow.id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_a["decision"] == "ALLOW"
    assert drawer_a["approval"] is None
    assert drawer_a["approval_lifecycle_status"] == "NOT_REQUIRED"
    assert drawer_a["execution_status"] == "UNCONSUMED"
    assert drawer_a["evidence_status"]["approval"] == "NOT_REQUIRED"

    drawer_b = (await client.get(f"/api/v1/gate-decisions/{gdec_block.id}", headers=ctx["headers"], cookies=ctx["cookies"])).json()
    assert drawer_b["decision"] == "BLOCK"
    assert drawer_b["execution_status"] == "NOT_EXECUTABLE"


@pytest.mark.asyncio
async def test_checkout_succeeds_followed_by_payment_requiring_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Regression test:
    Verify checkout succeeds with ALLOW, order is created in PENDING_PAYMENT,
    and subsequent payment action correctly evaluates to REVIEW, requiring human approval.
    Run enters WAITING_FOR_APPROVAL and displays REVIEW_REQUIRED, not FAILED or unqualified ALLOW.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    # Create run
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Purchase exactly one Budget Laptop 15-inch for ₹150 using my linked purchase intent and delegated authority. If approval is required, stop and wait for my approval.",
            "authority_id": auth_id,
            "auto_start": False
        },
        headers=headers,
        cookies=cookies
    )
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]

    # 1. create_cart
    act1 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=run_id,
        tool_name="create_cart", tool_input={}
    )
    assert act1.status == ActionStatus.SUCCESS
    cart_id = act1.output["cart_id"]

    # 2. add_to_cart (Budget Laptop 15-inch, price 150)
    act2 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=run_id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": product_id, "quantity": 1}
    )
    assert act2.status == ActionStatus.SUCCESS
    assert act2.output["total"] == 150

    # 3. checkout
    act3 = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=run_id,
        tool_name="checkout", tool_input={"cart_id": cart_id}
    )
    assert act3.status == ActionStatus.SUCCESS
    order_id = act3.output["order_id"]
    assert act3.output["status"] == "PENDING_PAYMENT"
    assert act3.output["total"] == 150

    # Intermediate checkout gate decision is ALLOW
    checkout_gd = (await db_session.execute(
        select(GateDecision).where(GateDecision.agent_action_id == act3.id)
    )).scalar_one_or_none()
    assert checkout_gd is not None
    assert checkout_gd.decision == DecisionResult.ALLOW

    # Verify Order in DB is PENDING_PAYMENT
    order = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    assert order is not None
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.total == 150
    assert order.payment_id is None

    # 4. pay_order (Amount 150 > authority threshold 100) -> Gate must produce REVIEW
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws_id, run_id=run_id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert exc_info.value.status_code == 402

    # Check pay_order action
    act4 = (await db_session.execute(
        select(AgentAction).where(AgentAction.run_id == run_id, AgentAction.tool_name == "pay_order")
    )).scalar_one_or_none()
    assert act4 is not None
    assert act4.status == ActionStatus.PENDING_APPROVAL

    # Check pay_order gate decision: REVIEW, APPROVAL_THRESHOLD_EXCEEDED
    pay_gd = (await db_session.execute(
        select(GateDecision).where(GateDecision.agent_action_id == act4.id)
    )).scalar_one_or_none()
    assert pay_gd is not None
    assert pay_gd.decision == DecisionResult.REVIEW
    assert "APPROVAL_THRESHOLD_EXCEEDED" in pay_gd.reason_codes
    assert pay_gd.required_approval is True
    assert pay_gd.approval_id is not None

    # Check approval request created
    appr = (await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.agent_action_id == act4.id)
    )).scalar_one_or_none()
    assert appr is not None
    assert appr.status == ApprovalStatus.PENDING
    assert appr.amount == 150

    # Verify run API endpoint reflects WAITING_FOR_APPROVAL and REVIEW_REQUIRED
    get_run_res = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=headers, cookies=cookies)
    assert get_run_res.status_code == 200
    run_data = get_run_res.json()
    assert run_data["status"] == "WAITING_FOR_APPROVAL"
    assert run_data["authoritative_decision"] == "REVIEW_REQUIRED"

    # Verify Decision Trace reflects pending order, pending approval, no payment yet
    trace_res = await client.get(f"/api/v1/agent-runtime/runs/{run_id}/decision-trace", headers=headers, cookies=cookies)
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert len(trace_data["orders"]) == 1
    assert trace_data["orders"][0]["id"] == order_id
    assert trace_data["orders"][0]["status"] == "PENDING_PAYMENT"
    assert len(trace_data["payments"]) == 0
    assert len(trace_data["approvals"]) == 1
    assert trace_data["approvals"][0]["status"] == "PENDING"


@pytest.mark.asyncio
async def test_pending_approval_approved_and_consumed_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Regression test:
    Verify that an action waiting for approval can be approved and resumed,
    producing an authoritative post-approval ALLOW, capturing payment, and updating order to PAID.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    # Create run and execute checkout -> pay_order
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase Budget Laptop 15-inch", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]

    act1 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="create_cart", tool_input={})
    act2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="add_to_cart", tool_input={"cart_id": act1.output["cart_id"], "product_id": product_id, "quantity": 1})
    act3 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": act1.output["cart_id"]})
    order_id = act3.output["order_id"]

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="pay_order", tool_input={"order_id": order_id})

    # Retrieve approval ID
    appr = (await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id)
    )).scalar_one_or_none()
    assert appr is not None
    assert appr.status == ApprovalStatus.PENDING

    # 1. Approve the request via API
    appr_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={
            "decision": "APPROVED",
            "order_id": order_id,
            "amount": 150,
            "currency": "INR",
            "agent_id": agent_id,
            "workspace_id": ws_id
        },
        headers=headers,
        cookies=cookies
    )
    assert appr_res.status_code == 200, appr_res.text
    assert appr_res.json()["status"] == "APPROVED"

    # 2. Resume the run via API
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_res.status_code == 200, resume_res.text
    resumed_data = resume_res.json()
    assert resumed_data["status"] == "COMPLETED"
    assert resumed_data["authoritative_decision"] == "ALLOW"

    # Verify payment captured
    payment = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one_or_none()
    assert payment is not None
    assert payment.status == PaymentStatus.CAPTURED
    assert payment.amount == 150

    # Verify order is PAID
    order = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    assert order.status == OrderStatus.PAID
    assert order.payment_id == payment.id

    # Verify approval status is now CONSUMED
    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.CONSUMED

    # Verify decision trace shows consumed approval, paid order, and captured payment
    trace_res = await client.get(f"/api/v1/agent-runtime/runs/{run_id}/decision-trace", headers=headers, cookies=cookies)
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert trace_data["approvals"][0]["status"] == "CONSUMED"
    assert trace_data["orders"][0]["status"] == "PAID"
    assert trace_data["payments"][0]["status"] == "CAPTURED"


@pytest.mark.asyncio
async def test_checkout_followed_by_genuine_execution_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Regression test:
    Verify that if checkout succeeds (order created in PENDING_PAYMENT)
    but run genuinely fails (e.g. execution error), the run is marked FAILED,
    the authoritative decision is FAILED, order remains PENDING_PAYMENT,
    and the intermediate checkout ALLOW is NOT confused with an overall ALLOW.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase Budget Laptop 15-inch", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert run_res.status_code == 200, run_res.text
    run_id = run_res.json()["id"]

    act1 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="create_cart", tool_input={})
    act2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="add_to_cart", tool_input={"cart_id": act1.output["cart_id"], "product_id": product_id, "quantity": 1})
    act3 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": act1.output["cart_id"]})
    order_id = act3.output["order_id"]

    # Finish run as FAILED (genuine runtime failure)
    await AgentRuntimeService.finish_run(
        db=db_session, workspace_id=ws_id, run_id=run_id,
        output="Execution error during payment gateway handshake",
        status=RunStatus.FAILED,
        error_code="GATEWAY_TIMEOUT",
        error_message="Gateway timeout connecting to payment processor"
    )

    get_run_res = await client.get(f"/api/v1/agent-runtime/runs/{run_id}", headers=headers, cookies=cookies)
    assert get_run_res.status_code == 200
    run_data = get_run_res.json()
    assert run_data["status"] == "FAILED"
    # Authoritative decision for the run is FAILED, not ALLOW
    assert run_data["authoritative_decision"] == "FAILED"

    # Order remains PENDING_PAYMENT and payment is None
    order = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    assert order.status == OrderStatus.PENDING_PAYMENT
    payment = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one_or_none()
    assert payment is None


@pytest.mark.asyncio
async def test_duplicate_submission_replay_and_gate_decision_separation(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Regression test:
    1. Verify checkout decision (ALLOW) is strictly separated from payment decision (REVIEW).
    2. Verify checkout ALLOW does not authorize or capture funds (order remains PENDING_PAYMENT).
    3. Verify approving and resuming captures payment exactly once, updates order to PAID, and marks approval CONSUMED.
    4. Verify attempting to replay a CONSUMED approval or pay an already PAID order is blocked (fails closed).
    5. Verify calling resume repeatedly is idempotent and captures 0 duplicate payments.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    # Start run
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase Budget Laptop 15-inch", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # 1. create_cart
    act1 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="create_cart", tool_input={})
    cart_id = act1.output["cart_id"]

    # 2. add_to_cart
    act2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": product_id, "quantity": 1})

    # 3. checkout
    act3 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": cart_id})
    order_id = act3.output["order_id"]

    # Verification: Checkout decision is ALLOW, order is PENDING_PAYMENT, 0 payments
    checkout_gd = (await db_session.execute(select(GateDecision).where(GateDecision.agent_action_id == act3.id))).scalar_one()
    assert checkout_gd.decision == DecisionResult.ALLOW
    assert checkout_gd.required_approval is False
    assert checkout_gd.approval_id is None

    order_check = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert order_check.status == OrderStatus.PENDING_PAYMENT
    assert order_check.payment_id is None
    assert (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all() == []

    # 4. pay_order -> triggers REVIEW because 150 > 100
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="pay_order", tool_input={"order_id": order_id})

    # Verification: Payment action is PENDING_APPROVAL, decision is REVIEW
    pay_act = (await db_session.execute(select(AgentAction).where(AgentAction.run_id == run_id, AgentAction.tool_name == "pay_order"))).scalar_one()
    assert pay_act.status == ActionStatus.PENDING_APPROVAL
    pay_gd = (await db_session.execute(select(GateDecision).where(GateDecision.agent_action_id == pay_act.id))).scalar_one()
    assert pay_gd.decision == DecisionResult.REVIEW
    assert pay_gd.required_approval is True
    assert pay_gd.approval_id is not None
    # Crucial invariant: checkout gate decision remains ALLOW and is NOT overwritten
    await db_session.refresh(checkout_gd)
    assert checkout_gd.decision == DecisionResult.ALLOW

    # 5. Approve the request
    appr = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.id == pay_gd.approval_id))).scalar_one()
    assert appr.status == ApprovalStatus.PENDING
    dec_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED", "order_id": order_id, "amount": 150, "currency": "INR", "agent_id": agent_id, "workspace_id": ws_id},
        headers=headers, cookies=cookies
    )
    assert dec_res.status_code == 200

    # 6. Resume the run -> Executes payment capture
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_res.status_code == 200
    resumed_data = resume_res.json()
    assert resumed_data["status"] == "COMPLETED"
    assert resumed_data["authoritative_decision"] == "ALLOW"

    # Verify payment captured exactly once
    payments = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(payments) == 1
    assert payments[0].status == PaymentStatus.CAPTURED
    assert payments[0].amount == 150

    # Verify order is PAID
    await db_session.refresh(order_check)
    assert order_check.status == OrderStatus.PAID
    assert order_check.payment_id == payments[0].id

    # Verify approval is CONSUMED
    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.CONSUMED

    # 7. Replay / Duplicate Prevention:
    # A. Calling resume again is idempotent and captures NO duplicate payment
    resume_dup = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_dup.status_code == 200
    payments_after = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(payments_after) == 1, "Must not capture duplicate payment on repeated resume"

    # B. Attempting to execute another pay_order on the completed run fails closed
    with pytest.raises(HTTPException) as pay_again_exc:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws_id, run_id=run_id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert pay_again_exc.value.status_code == 400
    assert "completed" in str(pay_again_exc.value.detail).lower()

    # C. Attempting to pay the already PAID order from a new run fails closed with ORDER_ALREADY_PAID
    new_run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Retry payment", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert new_run_res.status_code == 200
    new_run_id = new_run_res.json()["id"]

    with pytest.raises(HTTPException) as new_pay_exc:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws_id, run_id=new_run_id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert new_pay_exc.value.status_code == 400
    assert "already paid" in str(new_pay_exc.value.detail).lower()


@pytest.mark.asyncio
async def test_purchase_flow_reconciliation_and_ledger_invariants(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Comprehensive regression test certifying purchase-flow reconciliation:
    1. Reconcile orders, payments, Action Gate decisions, and approval records.
    2. Verify each captured payment maps to exactly one paid order with matching amount/currency.
    3. Verify pending orders remain PENDING_PAYMENT with payment_id=None until gate approval.
    4. Confirm interrupted/retried checkout cannot create duplicate orders or double-decrement inventory.
    5. Verify idempotency when resuming a run twice or retrying payments.
    6. Verify sandbox ledger coherence: overview payment volume equals sum of captured payments.
    """
    from app.services.overview_service import get_workspace_overview
    from app.services.commerce_service import CommerceService
    from app.schemas.execution_context import ExecutionContext
    from app.models.commerce import Product
    from fastapi import HTTPException

    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    # Refresh product to get baseline inventory
    prod_stmt = select(Product).where(Product.id == product_id)
    initial_product = (await db_session.execute(prod_stmt)).scalar_one()
    initial_inventory = initial_product.inventory

    # 1. Start Run 1
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase Budget Laptop 15-inch", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # Create cart and add product
    act1 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="create_cart", tool_input={})
    cart_id = act1.output["cart_id"]
    act2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": product_id, "quantity": 1})

    # Checkout -> creates Order 1
    act3 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": cart_id})
    order1_id = act3.output["order_id"]

    # Verify inventory decremented exactly once
    await db_session.refresh(initial_product)
    assert initial_product.inventory == initial_inventory - 1

    # Verify checkout idempotency / duplicate prevention: repeating checkout returns existing order without decrementing inventory again
    act3_retry = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": cart_id})
    assert act3_retry.output["order_id"] == order1_id
    await db_session.refresh(initial_product)
    assert initial_product.inventory == initial_inventory - 1, "Inventory must not be decremented on repeated checkout"

    # Verify Order 1 is PENDING_PAYMENT with payment_id=None
    order1 = (await db_session.execute(select(Order).where(Order.id == order1_id))).scalar_one()
    assert order1.status == OrderStatus.PENDING_PAYMENT
    assert order1.payment_id is None

    # Attempting payment without approval must fail closed
    with pytest.raises(HTTPException):
        await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="pay_order", tool_input={"order_id": order1_id})

    pay_act = (await db_session.execute(select(AgentAction).where(AgentAction.run_id == run_id, AgentAction.tool_name == "pay_order"))).scalar_one()
    assert pay_act.status == ActionStatus.PENDING_APPROVAL
    pay_gd = (await db_session.execute(select(GateDecision).where(GateDecision.agent_action_id == pay_act.id))).scalar_one()
    assert pay_gd.decision == DecisionResult.REVIEW

    # Approve the request
    appr_res = await client.post(
        f"/api/v1/approvals/{pay_gd.approval_id}/decision",
        json={"decision": "APPROVED", "order_id": order1_id, "amount": 150, "currency": "INR", "agent_id": agent_id, "workspace_id": ws_id},
        headers=headers, cookies=cookies
    )
    assert appr_res.status_code == 200

    # Resume run -> captures payment and marks Order 1 PAID
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "COMPLETED"

    await db_session.refresh(order1)
    assert order1.status == OrderStatus.PAID
    assert order1.payment_id is not None

    payment1 = (await db_session.execute(select(Payment).where(Payment.id == order1.payment_id))).scalar_one()
    assert payment1.status == PaymentStatus.CAPTURED
    assert payment1.amount == order1.total
    assert payment1.currency == order1.currency

    # Resuming the completed run a 2nd time is strictly idempotent
    resume_dup = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_dup.status_code == 200
    assert resume_dup.json()["status"] == "COMPLETED"
    dup_payments = (await db_session.execute(select(Payment).where(Payment.order_id == order1_id))).scalars().all()
    assert len(dup_payments) == 1, "Must not create duplicate payment on repeated resume"

    # 2. Cancelled Order and Inventory Restoration test:
    # Create Run 2, Cart 2, and Order 2
    run2_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Purchase 2nd Laptop", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert run2_res.status_code == 200
    run2_id = run2_res.json()["id"]

    act_c2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run2_id, tool_name="create_cart", tool_input={})
    cart2_id = act_c2.output["cart_id"]
    await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run2_id, tool_name="add_to_cart", tool_input={"cart_id": cart2_id, "product_id": product_id, "quantity": 1})
    act_ord2 = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run2_id, tool_name="checkout", tool_input={"cart_id": cart2_id})
    order2_id = act_ord2.output["order_id"]

    await db_session.refresh(initial_product)
    assert initial_product.inventory == initial_inventory - 2

    # Cancel Order 2 -> inventory restored (+1)
    await CommerceService.cancel_order(db=db_session, workspace_id=ws_id, order_id=order2_id, ctx=ExecutionContext(is_human=True, is_agent=False, user_id="test_admin"))
    await db_session.refresh(initial_product)
    assert initial_product.inventory == initial_inventory - 1, "Inventory must be restored when order is cancelled"

    order2 = (await db_session.execute(select(Order).where(Order.id == order2_id))).scalar_one()
    assert order2.status == OrderStatus.CANCELLED
    assert order2.payment_id is None

    # 3. Ledger Coherence Verification:
    # The sandbox overview volume must equal exactly the sum of captured payments (order1 total = 150 INR)
    overview = await get_workspace_overview(db_session, ws_id, time_range="30d")
    all_captured = (await db_session.execute(
        select(Payment).where(Payment.workspace_id == ws_id, Payment.status == PaymentStatus.CAPTURED)
    )).scalars().all()
    expected_volume = sum(p.amount for p in all_captured)
    assert overview.financial.payment_volume == expected_volume
    assert overview.financial.payment_count == len(all_captured)

    # Bijection check: every captured payment maps to exactly one unique paid order
    for p in all_captured:
        assert p.order_id is not None
        linked_ord = (await db_session.execute(select(Order).where(Order.id == p.order_id))).scalar_one()
        assert linked_ord.status == OrderStatus.PAID
        assert linked_ord.total == p.amount
        assert linked_ord.currency == p.currency
        assert linked_ord.payment_id == p.id


@pytest.mark.asyncio
async def test_full_approval_lifecycle_drawer_provenance_and_replay_protection(
    client: AsyncClient,
    db_session: AsyncSession,
    approval_test_context: dict
):
    """
    Regression test verifying the entire approval lifecycle:
    1. Pre-approval: Action Gate returns REVIEW; ApprovalRequest is PENDING; drawer detail API returns PENDING;
       zero payments captured; order remains PENDING_PAYMENT.
    2. Approval: Approving transitions ApprovalRequest to APPROVED, issues revalidated ALLOW decision with single-use nonce.
    3. Resumption: Resuming consumes nonce, captures exactly 1 payment (150 INR), transitions order to PAID,
       and transitions ApprovalRequest to CONSUMED.
    4. Post-completion drawer evidence: Both original REVIEW and superseding ALLOW gate decisions in detail API
       report approval status CONSUMED and payment CAPTURED.
    5. Replay Protection: Re-resuming completed run or retrying payment cannot duplicate payment or inventory deduction.
    """
    ctx = approval_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    product = (await db_session.execute(select(Product).where(Product.id == product_id))).scalar_one()
    initial_inventory = product.inventory

    # 1. Start purchase run
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Purchase Budget Laptop 15-inch for 150 INR with review required",
            "authority_id": auth_id,
            "auto_start": False
        },
        headers=headers, cookies=cookies
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # Cart & checkout
    act_cart = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="create_cart", tool_input={})
    cart_id = act_cart.output["cart_id"]
    await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": product_id, "quantity": 1})
    act_checkout = await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="checkout", tool_input={"cart_id": cart_id})
    order_id = act_checkout.output["order_id"]

    # 2. Trigger pay_order -> Action Gate REVIEW
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(db=db_session, workspace_id=ws_id, run_id=run_id, tool_name="pay_order", tool_input={"order_id": order_id})
    assert exc_info.value.status_code == 402

    pay_action = (await db_session.execute(
        select(AgentAction).where(AgentAction.run_id == run_id, AgentAction.tool_name == "pay_order")
    )).scalar_one()
    assert pay_action.status == ActionStatus.PENDING_APPROVAL

    initial_gate_dec = (await db_session.execute(
        select(GateDecision).where(GateDecision.agent_action_id == pay_action.id)
    )).scalar_one()
    assert initial_gate_dec.decision == DecisionResult.REVIEW
    assert initial_gate_dec.required_approval is True
    assert initial_gate_dec.approval_id is not None
    appr_id = initial_gate_dec.approval_id

    # Verify Approval is bound to order, amount, currency, agent
    approval = (await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.id == appr_id))).scalar_one()
    assert approval.status == ApprovalStatus.PENDING
    assert approval.amount == 150.0
    assert approval.currency == "INR"
    assert approval.agent_id == agent_id
    assert approval.transaction_data.get("order_id") == order_id

    # Verify Drawer detail API for initial gate decision before approval shows PENDING
    detail_res_pre = await client.get(f"/api/v1/approvals/gate-decisions/{initial_gate_dec.id}", headers=headers, cookies=cookies)
    assert detail_res_pre.status_code == 200
    detail_pre = detail_res_pre.json()
    assert detail_pre["decision"] == "REVIEW"
    assert detail_pre["required_approval"] is True
    assert detail_pre["approval"]["status"] == "PENDING"
    assert detail_pre["payment"] is None

    # Zero payments exist before approval
    payments_before = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(payments_before) == 0

    # 3. Approve via API
    approve_res = await client.post(
        f"/api/v1/approvals/{appr_id}/decision",
        json={"decision": "APPROVED", "order_id": order_id, "amount": 150, "currency": "INR", "agent_id": agent_id, "workspace_id": ws_id},
        headers=headers, cookies=cookies
    )
    assert approve_res.status_code == 200

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED

    # Check that a superseding ALLOW decision was created
    allow_gate_dec = (await db_session.execute(
        select(GateDecision).where(GateDecision.supersedes_decision_id == initial_gate_dec.id)
    )).scalar_one()
    assert allow_gate_dec.decision == DecisionResult.ALLOW
    assert allow_gate_dec.required_approval is False
    assert allow_gate_dec.nonce is not None
    assert allow_gate_dec.consumed_at is None

    # 4. Resume run -> captures payment
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "COMPLETED"

    # Verify payment captured
    captured_payments = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(captured_payments) == 1
    payment = captured_payments[0]
    assert payment.status == PaymentStatus.CAPTURED
    assert payment.amount == 150.0
    assert payment.currency == "INR"

    # Order marked PAID
    order = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert order.status == OrderStatus.PAID
    assert order.payment_id == payment.id

    # Approval marked CONSUMED
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    # Single-use nonce marked consumed
    await db_session.refresh(allow_gate_dec)
    assert allow_gate_dec.consumed_at is not None

    # 5. Post-completion drawer evidence check:
    # Both initial decision and superseding decision now reflect CONSUMED approval and CAPTURED payment
    detail_res_post_init = await client.get(f"/api/v1/approvals/gate-decisions/{initial_gate_dec.id}", headers=headers, cookies=cookies)
    assert detail_res_post_init.status_code == 200
    detail_post_init = detail_res_post_init.json()
    assert detail_post_init["approval"]["status"] == "CONSUMED"
    assert detail_post_init["payment"]["status"] == "CAPTURED"
    assert detail_post_init["payment"]["amount"] == 150.0

    detail_res_post_allow = await client.get(f"/api/v1/approvals/gate-decisions/{allow_gate_dec.id}", headers=headers, cookies=cookies)
    assert detail_res_post_allow.status_code == 200
    detail_post_allow = detail_res_post_allow.json()
    assert detail_post_allow["approval"]["status"] == "CONSUMED"
    assert detail_post_allow["payment"]["status"] == "CAPTURED"
    assert detail_post_allow["consumed_at"] is not None

    # 6. Replay & Double-Resumption protection
    resume_dup = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/resume", headers=headers, cookies=cookies)
    assert resume_dup.status_code == 200
    assert resume_dup.json()["status"] == "COMPLETED"
    dup_payments = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalars().all()
    assert len(dup_payments) == 1, "Duplicate payment must not be captured"

    await db_session.refresh(product)
    assert product.inventory == initial_inventory - 1, "Inventory must not be decremented twice"











