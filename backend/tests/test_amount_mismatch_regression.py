import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.agent import Agent, AgentType, AgentStatus
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.models.commerce import Merchant, Order, OrderItem, OrderStatus, Product
from app.models.payment import Payment, PaymentStatus


@pytest.fixture
async def ws_context_a(client: AsyncClient):
    email = f"amount_test_{uuid.uuid4().hex[:8]}@finshield.com"
    res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Amount Auditor"
    })
    assert res.status_code in [200, 201], res.text
    data = res.json()
    ws_id = data["workspace"]["id"]
    return {
        "cookies": res.cookies,
        "headers": {"X-Workspace-ID": ws_id},
        "ws_id": ws_id,
        "user_id": data["user"]["id"]
    }


@pytest.mark.asyncio
async def test_consistent_150_transaction_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that a canonical ₹150 transaction retains exact amount (150) and currency (INR)
    No decimal corruption or division into ₹1.50 occurs.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    # 1. Create Agent, Merchant, Product (150 INR)
    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Procurement Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        name="Tech Merchant"
    )
    db_session.add(merchant)

    product = Product(
        id=f"prd_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        name="Budget Item",
        price=150,
        currency="INR"
    )
    db_session.add(product)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="Buy item")
    db_session.add(run)

    action = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"amount": 150, "currency": "INR"}
    )
    db_session.add(action)

    # 2. Create Order for 150 INR
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id=merchant.id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    order_item = OrderItem(
        id=f"ori_{uuid.uuid4().hex[:16]}",
        order_id=order.id,
        product_id=product.id,
        product_name_snapshot="Budget Item",
        merchant_name_snapshot="Tech Merchant",
        quantity=1,
        unit_price_at_order=150,
        total=150
    )
    db_session.add(order_item)

    # 3. Create GateDecision (REVIEW) and ApprovalRequest (150 INR)
    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        explanation="Threshold exceeded",
        required_approval=True,
        evaluation_snapshot={"order_id": order.id}
    )
    db_session.add(gd)

    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=gd.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    # 4. User approves with amount=150
    decide_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED", "amount": 150, "currency": "INR"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert decide_res.status_code == 200, decide_res.text

    # 5. Create Payment Intent for 150 INR
    pi_res = await client.post(
        "/api/v1/payments/intents",
        json={
            "order_id": order.id,
            "payment_intent_id": f"pi_{uuid.uuid4().hex[:12]}",
            "idempotency_key": f"ik_{uuid.uuid4().hex[:12]}",
            "amount": 150,
            "currency": "INR",
            "payment_method_type": "card"
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert pi_res.status_code == 201, pi_res.text
    payment_id = pi_res.json()["id"]

    # 6. Authorize and capture payment
    auth_res = await client.post(
        f"/api/v1/payments/{payment_id}/authorize",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert auth_res.status_code == 200, auth_res.text

    cap_res = await client.post(
        f"/api/v1/payments/{payment_id}/capture",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert cap_res.status_code == 200, cap_res.text
    assert cap_res.json()["status"] == "CAPTURED"
    assert cap_res.json()["amount"] == 150

    # 7. Query GateDecision detail endpoint and verify exact consistency
    detail_res = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()

    assert detail["amount"] == 150.0
    assert detail["currency"] == "INR"
    assert detail["approval"]["amount"] == 150.0
    assert detail["approval"]["status"] == "CONSUMED"
    assert detail["order"]["total"] == 150.0
    assert detail["order"]["subtotal"] == 150.0
    assert detail["payment"]["amount"] == 150.0
    assert detail["payment"]["status"] == "CAPTURED"


@pytest.mark.asyncio
async def test_approval_decision_amount_mismatch_fails_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that attempting to approve a ₹150 approval with ₹1.50 fails closed.
    Approval remains in PENDING status.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(id=f"agent_{uuid.uuid4().hex[:12]}", workspace_id=ws_id, name="Test Agent", type=AgentType.SHOPPING)
    db_session.add(agent)
    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="Buy")
    db_session.add(run)
    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="pay_order")
    db_session.add(action)

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id="mer_dummy",
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={"order_id": order.id}
    )
    db_session.add(gd)

    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=gd.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    # Attempt to approve with amount 1.50 (100x lower mismatch)
    res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED", "amount": 1.50, "currency": "INR"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 400
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message") or str(err_body)
    assert "mismatch" in err_msg.lower()

    # Re-fetch approval from DB to confirm status is still PENDING
    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_order_amount_mismatch_with_approval_fails_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that if an approval record has amount=1.50 while the bound order has total=150,
    approving fails closed with HTTP 400 and does NOT approve.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(id=f"agent_{uuid.uuid4().hex[:12]}", workspace_id=ws_id, name="Test Agent", type=AgentType.SHOPPING)
    db_session.add(agent)
    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="Buy")
    db_session.add(run)
    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="pay_order")
    db_session.add(action)

    # Order is 150
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id="mer_dummy",
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={"order_id": order.id}
    )
    db_session.add(gd)

    # Approval has 1.50 (inconsistent with order total 150)
    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=gd.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=1.50,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 1.50, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 400
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message") or str(err_body)
    assert "mismatch" in err_msg.lower()

    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_payment_intent_amount_mismatch_fails_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that requesting a payment intent with amount=1.50 on a ₹150 order fails closed with HTTP 400.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=None,
        merchant_id="mer_dummy",
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        "/api/v1/payments/intents",
        json={
            "order_id": order.id,
            "payment_intent_id": f"pi_{uuid.uuid4().hex[:12]}",
            "idempotency_key": f"ik_{uuid.uuid4().hex[:12]}",
            "amount": 1.50,  # Mismatch with order total 150
            "currency": "INR"
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 400
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message") or str(err_body)
    assert "mismatch" in err_msg.lower()


@pytest.mark.asyncio
async def test_agent_order_approval_amount_mismatch_does_not_consume_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that creating a payment intent for an agent order fails closed if the approved
    amount (1.50) mismatches order total (150). Approval must NOT transition to CONSUMED.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(id=f"agent_{uuid.uuid4().hex[:12]}", workspace_id=ws_id, name="Test Agent", type=AgentType.SHOPPING)
    db_session.add(agent)
    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="Buy")
    db_session.add(run)
    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="pay_order")
    db_session.add(action)

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id="mer_dummy",
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.ALLOW,
        required_approval=True,
        evaluation_snapshot={"order_id": order.id}
    )
    db_session.add(gd)

    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=gd.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.APPROVED,
        amount=1.50,  # Mismatch with order total 150
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 1.50, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    res = await client.post(
        "/api/v1/payments/intents",
        json={
            "order_id": order.id,
            "payment_intent_id": f"pi_{uuid.uuid4().hex[:12]}",
            "idempotency_key": f"ik_{uuid.uuid4().hex[:12]}",
            "amount": 150,
            "currency": "INR"
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 403
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message") or str(err_body)
    assert "approved amount (1.5) does not match order total (150)" in err_msg.lower()

    # Crucial assertion: approval must NOT be consumed
    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_capture_payment_amount_mismatch_fails_closed(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Proves that capture_payment refuses to capture a payment whose amount (1.50)
    differs from the linked order's total (150). Payment remains AUTHORIZED, not CAPTURED.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=None,
        merchant_id="mer_dummy",
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    payment = Payment(
        id=f"pay_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        order_id=order.id,
        payment_intent_id=f"pi_{uuid.uuid4().hex[:12]}",
        idempotency_key=f"ik_{uuid.uuid4().hex[:12]}",
        amount=1.50,  # Tampered or mismatched payment amount
        currency="INR",
        status=PaymentStatus.AUTHORIZED
    )
    db_session.add(payment)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/payments/{payment.id}/capture",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 400
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message") or str(err_body)
    assert "does not match" in err_msg.lower() or "mismatch" in err_msg.lower()

    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.AUTHORIZED
    await db_session.refresh(order)
    assert order.status != OrderStatus.PAID


@pytest.mark.asyncio
async def test_exact_e2e_amount_verification_across_db_evidence_api_and_ledger(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """
    Validates that:
    1. Persisted values in SQLite DB for Order (subtotal, total), OrderItem (unit_price, total),
       Payment (amount), ApprovalRequest (amount), GateDecision (evaluation snapshot amount)
       are all strictly 150.0.
    2. Evidence API (/api/v1/gate-decisions/{gd_id}) returns exact 150.0 without division.
    3. Sandbox Overview Ledger (/api/v1/overview) reflects payment_volume of exactly 150.0.
    """
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Verification Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        name="Sandbox Merchant"
    )
    db_session.add(merchant)

    product = Product(
        id=f"prd_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        name="Budget Laptop 15-inch",
        category="LAPTOP",
        price=150.0,
        currency="INR",
        inventory=10
    )
    db_session.add(product)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        input="Purchase Budget Laptop"
    )
    db_session.add(run)

    action = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"amount": 150.0, "currency": "INR"}
    )
    db_session.add(action)

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id=merchant.id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150.0,
        total=150.0
    )
    db_session.add(order)

    item = OrderItem(
        id=f"ori_{uuid.uuid4().hex[:16]}",
        order_id=order.id,
        product_id=product.id,
        product_name_snapshot=product.name,
        merchant_name_snapshot=merchant.name,
        quantity=1,
        unit_price_at_order=150.0,
        total=150.0
    )
    db_session.add(item)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        required_approval=True,
        evaluation_snapshot={"order_id": order.id, "amount": 150.0, "currency": "INR"}
    )
    db_session.add(gd)

    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=gd.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=150.0,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150.0, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    # 1. Verify Persisted SQLite values directly from DB
    await db_session.refresh(order)
    await db_session.refresh(item)
    await db_session.refresh(appr)
    assert order.subtotal == 150.0
    assert order.total == 150.0
    assert order.currency == "INR"
    assert item.unit_price_at_order == 150.0
    assert item.total == 150.0
    assert appr.amount == 150.0
    assert appr.currency == "INR"

    # 2. Human Approves
    dec_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED", "reason": "Approved ₹150 laptop"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert dec_res.status_code == 200

    # 3. Create, Authorize, and Capture Payment for ₹150
    pi_res = await client.post(
        "/api/v1/payments/intents",
        json={
            "order_id": order.id,
            "payment_intent_id": f"pi_{uuid.uuid4().hex[:12]}",
            "idempotency_key": f"ik_{uuid.uuid4().hex[:12]}",
            "amount": 150.0,
            "currency": "INR",
            "payment_method_type": "card"
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert pi_res.status_code == 201
    pay_id = pi_res.json()["id"]

    await client.post(f"/api/v1/payments/{pay_id}/authorize", cookies=ctx["cookies"], headers=ctx["headers"])
    cap_res = await client.post(f"/api/v1/payments/{pay_id}/capture", cookies=ctx["cookies"], headers=ctx["headers"])
    assert cap_res.status_code == 200
    assert cap_res.json()["amount"] == 150.0

    # 4. Check Evidence API (/api/v1/gate-decisions/{gd.id})
    evidence_res = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert evidence_res.status_code == 200
    ev = evidence_res.json()
    assert ev["amount"] == 150.0
    assert ev["currency"] == "INR"
    assert ev["order"]["subtotal"] == 150.0
    assert ev["order"]["total"] == 150.0
    assert ev["order"]["items"][0]["unit_price"] == 150.0
    assert ev["order"]["items"][0]["total"] == 150.0
    assert ev["payment"]["amount"] == 150.0
    assert ev["payment"]["status"] == "CAPTURED"
    assert ev["approval"]["amount"] == 150.0
    assert ev["approval"]["status"] == "CONSUMED"

    # 5. Check Sandbox Balance Ledger (/api/v1/overview)
    overview_res = await client.get("/api/v1/overview", cookies=ctx["cookies"], headers=ctx["headers"])
    assert overview_res.status_code == 200
    financial = overview_res.json()["financial"]
    assert financial["payment_volume"] == 150.0
    assert financial["balances_by_currency"].get("INR") == 150.0


