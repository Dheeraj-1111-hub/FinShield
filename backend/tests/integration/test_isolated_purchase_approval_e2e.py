import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.agent import Agent, AgentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.intent import Intent, IntentType, IntentStatus
from app.models.agent_runtime import AgentRun, AgentAction, ActionStatus, RunStatus
from app.models.commerce import Merchant, Product, Cart, Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.models.audit import AuditEvent
from app.services.agent_runtime_service import AgentRuntimeService
from app.services.overview_service import get_workspace_overview


@pytest.fixture
async def isolated_e2e_fixture(client: AsyncClient, db_session: AsyncSession):
    """
    Deterministic isolated fixtures creating a fresh workspace, user, agent,
    authority with 100 INR threshold, intent, merchant, and Budget Laptop at 150 INR.
    """
    email = f"e2e_tester_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "E2E Acceptance Tester"
    })
    assert signup_res.status_code in [200, 201], signup_res.text

    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    headers = {"X-Workspace-ID": ws_id}

    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Sandbox Merchant Corp"
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
        name="Procurement Agent",
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
        natural_language_request="Purchase laptop with review required above 100 INR",
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
async def test_isolated_purchase_approval_and_payment_e2e_acceptance(
    client: AsyncClient,
    db_session: AsyncSession,
    isolated_e2e_fixture: dict
):
    """
    End-to-end acceptance certification test:
    1. Search-only request: products returned, zero cart/order/payment side effects.
    2. Purchase request for exactly one Budget Laptop 15-inch at INR 150.
    3. Action Gate returns REVIEW_REQUIRED before payment capture.
    4. Approval is bound to the exact order, amount, and currency.
    5. After approval, exactly one payment is captured and stock decreases by exactly one.
    6. Orders, Payments, Agent Console, Action Gate evidence, and audit records agree.
    7. Replaying the approval or resuming completed run cannot duplicate payment or inventory changes.
    """
    ctx = isolated_e2e_fixture
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    product_id = ctx["product"].id
    headers = ctx["headers"]
    cookies = ctx["cookies"]

    # Refresh baseline product inventory
    product = (await db_session.execute(select(Product).where(Product.id == product_id))).scalar_one()
    initial_inventory = product.inventory
    assert initial_inventory == 50

    # =========================================================================
    # STEP 1: Search-only request — products returned, zero financial side-effects
    # =========================================================================
    search_run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Search for available laptops", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert search_run_res.status_code == 200, search_run_res.text
    search_run_id = search_run_res.json()["id"]

    search_act = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=search_run_id,
        tool_name="search_products", tool_input={"query": "laptop"}
    )
    assert search_act.status == ActionStatus.SUCCESS
    assert "results" in search_act.output
    found_products = search_act.output["results"]
    assert any(p.get("product_id") == product_id or p.get("id") == product_id for p in found_products)

    await AgentRuntimeService.finish_run(
        db=db_session, workspace_id=ws_id, run_id=search_run_id,
        output="Found laptops in the catalog.", status=RunStatus.COMPLETED
    )

    # Invariant check: ZERO cart, order, or payment side-effects from search
    carts_count = (await db_session.execute(select(func.count(Cart.id)).where(Cart.workspace_id == ws_id))).scalar()
    orders_count = (await db_session.execute(select(func.count(Order.id)).where(Order.workspace_id == ws_id))).scalar()
    payments_count = (await db_session.execute(select(func.count(Payment.id)).where(Payment.workspace_id == ws_id))).scalar()
    await db_session.refresh(product)

    assert carts_count == 0, "Search-only run must not create carts"
    assert orders_count == 0, "Search-only run must not create orders"
    assert payments_count == 0, "Search-only run must not create payments"
    assert product.inventory == initial_inventory, "Search-only run must not modify inventory"

    # =========================================================================
    # STEP 2: Purchase request for exactly one Budget Laptop 15-inch at INR 150
    # =========================================================================
    purchase_run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Purchase exactly one Budget Laptop 15-inch for 150 INR. If approval is required, pause and wait.",
            "authority_id": auth_id,
            "auto_start": False
        },
        headers=headers, cookies=cookies
    )
    assert purchase_run_res.status_code == 200
    purchase_run_id = purchase_run_res.json()["id"]

    # 2a. create_cart
    act_cart = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=purchase_run_id,
        tool_name="create_cart", tool_input={}
    )
    cart_id = act_cart.output["cart_id"]

    # 2b. add_to_cart (1 x laptop @ 150 INR)
    act_add = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=purchase_run_id,
        tool_name="add_to_cart", tool_input={"cart_id": cart_id, "product_id": product_id, "quantity": 1}
    )
    assert act_add.status == ActionStatus.SUCCESS

    # 2c. checkout
    act_checkout = await AgentRuntimeService.execute_action(
        db=db_session, workspace_id=ws_id, run_id=purchase_run_id,
        tool_name="checkout", tool_input={"cart_id": cart_id}
    )
    order_id = act_checkout.output["order_id"]

    # Verify inventory decremented exactly once upon checkout
    await db_session.refresh(product)
    assert product.inventory == initial_inventory - 1, "Stock must decrement by exactly 1 upon checkout"

    # =========================================================================
    # STEP 3: Action Gate returns REVIEW_REQUIRED before payment capture
    # =========================================================================
    # Attempting to execute pay_order triggers the Action Gate REVIEW
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws_id, run_id=purchase_run_id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert exc_info.value.status_code == 402, f"Expected 402 Payment Required / Approval Required, got {exc_info.value.status_code}"

    # Verify action status is PENDING_APPROVAL and Gate Decision is REVIEW
    pay_act = (await db_session.execute(
        select(AgentAction).where(AgentAction.run_id == purchase_run_id, AgentAction.tool_name == "pay_order")
    )).scalar_one()
    assert pay_act.status == ActionStatus.PENDING_APPROVAL

    gate_dec = (await db_session.execute(
        select(GateDecision).where(GateDecision.agent_action_id == pay_act.id)
    )).scalar_one()
    assert gate_dec.decision == DecisionResult.REVIEW
    assert gate_dec.required_approval is True
    assert gate_dec.approval_id is not None

    # Verify Run is paused in WAITING_FOR_APPROVAL with authoritative decision REVIEW_REQUIRED
    run_check_res = await client.get(f"/api/v1/agent-runtime/runs/{purchase_run_id}", headers=headers, cookies=cookies)
    assert run_check_res.status_code == 200
    run_check_data = run_check_res.json()
    assert run_check_data["status"] == "WAITING_FOR_APPROVAL"
    assert run_check_data["authoritative_decision"] == "REVIEW_REQUIRED"

    # Verify ZERO payments captured before approval
    payments_before_appr = (await db_session.execute(
        select(Payment).where(Payment.order_id == order_id)
    )).scalars().all()
    assert len(payments_before_appr) == 0, "No payment may be captured before approval"

    # Verify order is in PENDING_PAYMENT
    order_before_appr = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert order_before_appr.status == OrderStatus.PENDING_PAYMENT
    assert order_before_appr.payment_id is None

    # =========================================================================
    # STEP 4: Approval is bound to the exact order, amount, and currency
    # =========================================================================
    approval = (await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == gate_dec.approval_id)
    )).scalar_one()

    assert approval.status == ApprovalStatus.PENDING
    assert approval.amount == 150
    assert approval.currency == "INR"
    assert approval.workspace_id == ws_id
    assert approval.agent_id == agent_id
    assert approval.agent_run_id == purchase_run_id
    assert approval.agent_action_id == pay_act.id
    assert approval.transaction_data.get("order_id") == order_id

    # Verify API view of approval request
    appr_api_res = await client.get(f"/api/v1/approvals/{ws_id}/approvals", headers=headers, cookies=cookies)
    assert appr_api_res.status_code == 200
    pending_apprs = [a for a in appr_api_res.json() if a["id"] == approval.id]
    assert len(pending_apprs) == 1
    assert pending_apprs[0]["amount"] == 150
    assert pending_apprs[0]["currency"] == "INR"

    # =========================================================================
    # STEP 5: After approval, exactly one payment is captured and stock decreases by 1
    # =========================================================================
    # 5a. Approve the request via API
    dec_res = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        json={"decision": "APPROVED", "order_id": order_id, "amount": 150, "currency": "INR", "agent_id": agent_id, "workspace_id": ws_id},
        headers=headers, cookies=cookies
    )
    assert dec_res.status_code == 200

    # 5b. Resume run -> executes payment capture
    resume_res = await client.post(f"/api/v1/agent-runtime/runs/{purchase_run_id}/resume", headers=headers, cookies=cookies)
    assert resume_res.status_code == 200
    resumed_data = resume_res.json()
    assert resumed_data["status"] == "COMPLETED"
    assert resumed_data["authoritative_decision"] == "ALLOW"

    # Verify exactly one captured payment exists
    captured_payments = (await db_session.execute(
        select(Payment).where(Payment.order_id == order_id)
    )).scalars().all()
    assert len(captured_payments) == 1, "Exactly one payment must be captured"
    payment = captured_payments[0]
    assert payment.status == PaymentStatus.CAPTURED
    assert payment.amount == 150
    assert payment.currency == "INR"

    # Verify order is PAID with payment_id linked
    order_after_pay = (await db_session.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert order_after_pay.status == OrderStatus.PAID
    assert order_after_pay.payment_id == payment.id
    assert order_after_pay.total == 150
    assert order_after_pay.currency == "INR"

    # Verify stock remains exactly initial_inventory - 1 (50 -> 49)
    await db_session.refresh(product)
    assert product.inventory == initial_inventory - 1, "Stock decrement must remain exactly 1"

    # =========================================================================
    # STEP 6: Agreement across Orders, Payments, Agent Console, Action Gate & Audit
    # =========================================================================
    # 6a. Orders API
    ord_api_res = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=headers, cookies=cookies)
    assert ord_api_res.status_code == 200
    ord_api_data = ord_api_res.json()
    assert ord_api_data["id"] == order_id
    assert ord_api_data["status"] == "PAID"
    assert ord_api_data["total"] == 150
    assert ord_api_data["currency"] == "INR"
    assert ord_api_data["payment_id"] == payment.id

    # 6b. Payments API
    pay_api_res = await client.get(f"/api/v1/payments/{payment.id}", headers=headers, cookies=cookies)
    assert pay_api_res.status_code == 200
    pay_api_data = pay_api_res.json()
    assert pay_api_data["id"] == payment.id
    assert pay_api_data["order_id"] == order_id
    assert pay_api_data["status"] == "CAPTURED"
    assert pay_api_data["amount"] == 150
    assert pay_api_data["currency"] == "INR"

    # 6c. Agent Run & Trajectory API
    run_api_res = await client.get(f"/api/v1/agent-runtime/runs/{purchase_run_id}", headers=headers, cookies=cookies)
    assert run_api_res.status_code == 200
    run_api_data = run_api_res.json()
    assert run_api_data["status"] == "COMPLETED"
    assert run_api_data["authoritative_decision"] == "ALLOW"
    pay_action_api = next(a for a in run_api_data["actions"] if a["tool_name"] == "pay_order")
    assert pay_action_api["status"] == "SUCCESS"
    assert pay_action_api["output"]["transaction_id"] == payment.id

    # 6d. Decision Trace API
    trace_res = await client.get(f"/api/v1/agent-runtime/runs/{purchase_run_id}/decision-trace", headers=headers, cookies=cookies)
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert trace_data["run_status"] == "COMPLETED"
    assert (trace_data.get("final_gate_decision") or trace_data.get("final_decision")) == "ALLOW"
    trace_gdec_ids = [d["id"] for d in trace_data["gate_decisions"]]
    assert gate_dec.id in trace_gdec_ids

    # 6e. Audit Records agreement
    audit_events = (await db_session.execute(
        select(AuditEvent).where(AuditEvent.workspace_id == ws_id).order_by(AuditEvent.created_at.asc())
    )).scalars().all()
    event_types = [e.event_type for e in audit_events]
    assert "AGENT_RUN_CREATED" in event_types
    assert "ORDER_CREATED" in event_types
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_APPROVED" in event_types
    assert "CAPTURED" in event_types
    assert "ORDER_PAID" in event_types

    # Ensure no false security alarms was logged
    assert "SECURITY_INCIDENT" not in event_types
    assert "POLICY_VIOLATION" not in event_types

    # =========================================================================
    # STEP 7: Replay protection & Repeated Resumption Idempotency
    # =========================================================================
    # 7a. Approval is single-use: status must be CONSUMED
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    # 7b. Resuming the completed run a 2nd time is a safe, zero-payment no-op
    resume_dup_res = await client.post(f"/api/v1/agent-runtime/runs/{purchase_run_id}/resume", headers=headers, cookies=cookies)
    assert resume_dup_res.status_code == 200
    assert resume_dup_res.json()["status"] == "COMPLETED"

    # Verify payments count remains exactly 1
    payments_after_dup = (await db_session.execute(
        select(Payment).where(Payment.order_id == order_id)
    )).scalars().all()
    assert len(payments_after_dup) == 1, "Must not capture duplicate payment on repeat resume"

    # Verify inventory is untouched (remains 49)
    await db_session.refresh(product)
    assert product.inventory == initial_inventory - 1, "Inventory must not change on repeated resume"

    # 7c. Retrying payment on the order from a new run fails closed
    new_run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={"agent_id": agent_id, "input": "Retry pay_order", "authority_id": auth_id, "auto_start": False},
        headers=headers, cookies=cookies
    )
    assert new_run_res.status_code == 200
    new_run_id = new_run_res.json()["id"]

    with pytest.raises(HTTPException) as pay_retry_exc:
        await AgentRuntimeService.execute_action(
            db=db_session, workspace_id=ws_id, run_id=new_run_id,
            tool_name="pay_order", tool_input={"order_id": order_id}
        )
    assert pay_retry_exc.value.status_code == 400
    assert "already paid" in str(pay_retry_exc.value.detail).lower()

    # Final overview check on isolated database: exactly ₹150 INR payment volume
    overview = await get_workspace_overview(db_session, ws_id, time_range="30d")
    assert overview.financial.payment_volume == 150.0
    assert overview.financial.payment_count == 1
    assert overview.financial.orders_count == 1
