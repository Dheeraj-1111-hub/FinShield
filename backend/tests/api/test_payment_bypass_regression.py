import pytest
import pytest_asyncio
from httpx import AsyncClient
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from app.models.agent import Agent, AgentStatus, AgentType
from app.models.agent_runtime import AgentRun, AgentAction, RunStatus, ActionStatus
from app.models.commerce import Merchant, Product, ProductStatus, Cart, CartStatus, CartItem, Order, OrderStatus, OrderItem
from app.models.payment import Payment, PaymentStatus
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.intent import Intent, IntentStatus, IntentType
from app.services.approval_service import ApprovalService
from app.services.commerce_service import CommerceService
from app.services.agent_runtime_service import AgentRuntimeService
from app.schemas.execution_context import ExecutionContext


@pytest_asyncio.fixture
async def base_setup(db_session: AsyncSession):
    # User
    user = User(
        id=f"usr_{uuid.uuid4().hex[:16]}",
        email=f"tester_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("password123"),
        full_name="Regression Tester",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)

    # Workspace
    workspace = Workspace(
        id=f"ws_{uuid.uuid4().hex[:16]}",
        name="Security Lab WS",
        slug=f"sec-lab-{uuid.uuid4().hex[:8]}",
        owner_id=user.id
    )
    db_session.add(workspace)

    # Membership
    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        workspace_id=workspace.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)

    # Session token
    token = generate_session_token()
    session = Session(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)

    # Agent
    agent = Agent(
        id=f"agt_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace.id,
        name="Procurement Bot",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        currency="INR",
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"]
    )
    db_session.add(agent)

    # Merchant
    merchant = Merchant(
        id=f"merch_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace.id,
        name="Sandbox Electronics",
        status="ACTIVE"
    )
    db_session.add(merchant)

    # Product with inventory = 50
    product = Product(
        id=f"prd_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        name="Enterprise Laptop",
        description="High spec laptop",
        category="electronics",
        price=150,
        currency="INR",
        inventory=50,
        status=ProductStatus.ACTIVE
    )
    db_session.add(product)

    await db_session.commit()

    return {
        "user": user,
        "workspace": workspace,
        "agent": agent,
        "merchant": merchant,
        "product": product,
        "headers": {"Cookie": f"finshield_session={token}"}
    }


@pytest.mark.asyncio
async def test_rejected_approval_manual_payment_attempt_denied(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent_id = base_setup["agent"].id
    merchant_id = base_setup["merchant"].id
    headers = base_setup["headers"]

    # 1. Create an agent order
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant_id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    # Create associated rejected ApprovalRequest
    gate_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:16]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:16]}",
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={},
        valid_until=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db_session.add(gate_decision)

    approval = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=gate_decision.agent_run_id,
        agent_action_id=gate_decision.agent_action_id,
        gate_decision_id=gate_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.REJECTED,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(approval)
    await db_session.commit()

    # 2. Attempt manual payment-intent creation
    resp = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_{uuid.uuid4().hex}",
            "order_id": order.id
        }
    )

    assert resp.status_code == 403
    err_body = resp.json()
    err_msg = err_body.get("error", {}).get("message") or err_body.get("detail", str(err_body))
    assert "rejected" in err_msg.lower()

    # Confirm no payment record exists
    p_stmt = select(Payment).where(Payment.order_id == order.id)
    p_res = await db_session.execute(p_stmt)
    assert len(p_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_pending_approval_manual_payment_attempt_denied(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent_id = base_setup["agent"].id
    merchant_id = base_setup["merchant"].id
    headers = base_setup["headers"]

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant_id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    gate_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:16]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:16]}",
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={},
        valid_until=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db_session.add(gate_decision)

    approval = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=gate_decision.agent_run_id,
        agent_action_id=gate_decision.agent_action_id,
        gate_decision_id=gate_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(approval)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_{uuid.uuid4().hex}",
            "order_id": order.id
        }
    )

    assert resp.status_code == 403
    err_body = resp.json()
    err_msg = err_body.get("error", {}).get("message") or err_body.get("detail", str(err_body))
    assert "pending" in err_msg.lower()

    p_stmt = select(Payment).where(Payment.order_id == order.id)
    p_res = await db_session.execute(p_stmt)
    assert len(p_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_valid_approval_permitted_flow(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent_id = base_setup["agent"].id
    merchant_id = base_setup["merchant"].id
    headers = base_setup["headers"]

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant_id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    # Approved gate decision
    gate_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:16]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:16]}",
        decision=DecisionResult.ALLOW,
        required_approval=True,
        evaluation_snapshot={},
        valid_until=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db_session.add(gate_decision)

    approval = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=gate_decision.agent_run_id,
        agent_action_id=gate_decision.agent_action_id,
        gate_decision_id=gate_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.APPROVED,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(approval)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_{uuid.uuid4().hex}",
            "order_id": order.id
        }
    )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert data["status"] == "CREATED"
    assert data["amount"] == 150
    assert data["currency"] == "INR"

    # Confirm approval was marked CONSUMED
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED


@pytest.mark.asyncio
async def test_approval_rejection_lifecycle_and_inventory_restoration(base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent_id = base_setup["agent"].id
    merchant_id = base_setup["merchant"].id
    product = base_setup["product"]
    user_id = base_setup["user"].id

    # Initial inventory is 50
    assert product.inventory == 50

    # Create order reserving 2 units
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant_id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=300,
        total=300
    )
    db_session.add(order)

    item = OrderItem(
        id=f"ori_{uuid.uuid4().hex[:16]}",
        order_id=order.id,
        product_id=product.id,
        product_name_snapshot=product.name,
        merchant_name_snapshot="Sandbox Electronics",
        quantity=2,
        unit_price_at_order=150,
        total=300
    )
    db_session.add(item)
    # Deduct inventory at checkout time
    product.inventory -= 2
    assert product.inventory == 48

    # Create pending approval
    gate_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:16]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:16]}",
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={}
    )
    db_session.add(gate_decision)

    approval = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=gate_decision.agent_run_id,
        agent_action_id=gate_decision.agent_action_id,
        gate_decision_id=gate_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=300,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 300, "currency": "INR"}
    )
    db_session.add(approval)
    await db_session.commit()

    # Reject via ApprovalService
    approval_svc = ApprovalService(db_session)
    rejected_appr = await approval_svc.reject(approval.id, ws_id, user_id)

    assert rejected_appr.status == ApprovalStatus.REJECTED

    # Verify order is CANCELLED
    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED

    # Verify inventory restored back to 50
    await db_session.refresh(product)
    assert product.inventory == 50

    # Idempotency check: Cancel order again via CommerceService must fail gracefully without re-incrementing
    with pytest.raises(Exception):
        await CommerceService.cancel_order(db_session, ws_id, order.id, ExecutionContext(is_human=True, is_agent=False, user_id=user_id))

    await db_session.refresh(product)
    assert product.inventory == 50 # NOT 52!


@pytest.mark.asyncio
async def test_paid_orders_never_cancelled_on_approval_rejection(base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent_id = base_setup["agent"].id
    merchant_id = base_setup["merchant"].id
    product = base_setup["product"]
    user_id = base_setup["user"].id

    # Create an order that is already PAID
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant_id,
        status=OrderStatus.PAID,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    item = OrderItem(
        id=f"ori_{uuid.uuid4().hex[:16]}",
        order_id=order.id,
        product_id=product.id,
        product_name_snapshot=product.name,
        merchant_name_snapshot="Sandbox Electronics",
        quantity=1,
        unit_price_at_order=150,
        total=150
    )
    db_session.add(item)
    product.inventory = 49

    gate_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:16]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:16]}",
        decision=DecisionResult.REVIEW,
        required_approval=True,
        evaluation_snapshot={}
    )
    db_session.add(gate_decision)

    approval = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=gate_decision.agent_run_id,
        agent_action_id=gate_decision.agent_action_id,
        gate_decision_id=gate_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=150,
        currency="INR",
        transaction_data={"order_id": order.id, "amount": 150, "currency": "INR"}
    )
    db_session.add(approval)
    await db_session.commit()

    # Reject the approval
    approval_svc = ApprovalService(db_session)
    await approval_svc.reject(approval.id, ws_id, user_id)

    # Order must remain PAID
    await db_session.refresh(order)
    assert order.status == OrderStatus.PAID

    # Inventory must remain 49
    await db_session.refresh(product)
    assert product.inventory == 49


@pytest.mark.asyncio
async def test_duplicate_checkout_and_retry_protection(base_setup: dict, db_session: AsyncSession):
    ws_id = base_setup["workspace"].id
    agent = base_setup["agent"]
    merchant = base_setup["merchant"]
    product = base_setup["product"]

    # Authority with limit
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        currency="INR",
        monetary_limit=10000,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        prohibited_actions=[],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db_session.add(authority)

    # Intent
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        title="Purchase Laptop",
        natural_language_request="Purchase laptop within authority",
        intent_type=IntentType.PURCHASE,
        structured_constraints={
            "amount": 10000,
            "currency": "INR",
            "product": {"category": "electronics"},
            "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"]
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    # Agent Run
    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=authority.id,
        status=RunStatus.RUNNING,
        trigger_type="API",
        input="Purchase the laptop"
    )
    db_session.add(run)

    # Create Cart with 1 item
    cart = Cart(
        id=f"crt_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=CartStatus.ACTIVE,
        currency="INR"
    )
    db_session.add(cart)

    citem = CartItem(
        id=f"cti_{uuid.uuid4().hex[:16]}",
        cart_id=cart.id,
        product_id=product.id,
        quantity=1
    )
    db_session.add(citem)
    await db_session.commit()

    initial_inv = product.inventory

    # 1. First checkout
    act1 = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="checkout",
        tool_input={"cart_id": cart.id}
    )
    assert act1.status == ActionStatus.SUCCESS
    order_id_1 = act1.output["order_id"]
    assert order_id_1.startswith("ord_")

    await db_session.refresh(product)
    assert product.inventory == initial_inv - 1

    # 2. Second checkout (retry / duplicate) in the same run
    act2 = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="checkout",
        tool_input={"cart_id": cart.id}
    )
    assert act2.status == ActionStatus.SUCCESS
    assert act2.output.get("reused") is True
    assert act2.output["order_id"] == order_id_1

    # Crucial: Inventory was NOT decremented again!
    await db_session.refresh(product)
    assert product.inventory == initial_inv - 1

    # Only 1 order exists for this cart
    orders_res = await db_session.execute(select(Order).where(Order.cart_id == cart.id))
    orders = orders_res.scalars().all()
    assert len(orders) == 1


@pytest.mark.asyncio
async def test_approval_threshold_enforced_and_resumed_after_approval(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Exact FINSHIELD P0 scenario:
    - Order amount: ₹150
    - Approval threshold: ₹100
    - Explicit approval required
    - Assert that initial run cannot capture payment, pending approval exists in DB,
      unapproved resume is rejected, and payment succeeds only after valid approval.
    - Assert idempotency: retry does not double charge or create duplicate payments.
    """
    from fastapi import HTTPException

    ws_id = base_setup["workspace"].id
    agent = base_setup["agent"]
    merchant = base_setup["merchant"]
    product = base_setup["product"]
    user = base_setup["user"]
    headers = base_setup["headers"]

    # Authority with limit 40,000 INR
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        currency="INR",
        monetary_limit=40000,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"],
        prohibited_actions=[],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db_session.add(authority)

    # Intent with threshold ₹100
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        title="Laptop Purchase with Approval Threshold",
        natural_language_request="Purchase Budget Laptop under INR 40,000 with approval above INR 100",
        intent_type=IntentType.PURCHASE,
        structured_constraints={
            "amount": {"maximum": 40000, "currency": "INR"},
            "product": {"category": "electronics", "keywords": ["laptop"]},
            "approval": {"approval_required_above": 100, "approval_required": True},
            "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"]
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    # Agent Run
    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=authority.id,
        status=RunStatus.RUNNING,
        trigger_type="API",
        input="Purchase the Budget Laptop 15-inch for ₹150. My intent permits this purchase, but require my approval before payment because the amount exceeds ₹100. Do not make any other purchase or exceed my delegated authority. Stop and wait for my approval before capturing payment."
    )
    db_session.add(run)

    # Cart with Budget Laptop (150 INR)
    cart = Cart(
        id=f"crt_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=CartStatus.ACTIVE,
        currency="INR"
    )
    db_session.add(cart)

    citem = CartItem(
        id=f"cti_{uuid.uuid4().hex[:16]}",
        cart_id=cart.id,
        product_id=product.id,
        quantity=1
    )
    db_session.add(citem)
    await db_session.commit()

    # 1. Checkout action succeeds and creates an order of ₹150
    act_co = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="checkout",
        tool_input={"cart_id": cart.id}
    )
    assert act_co.status == ActionStatus.SUCCESS
    order_id = act_co.output["order_id"]
    assert order_id.startswith("ord_")

    # 2. Agent attempts pay_order for ₹150 -> Must hit Action Gate REVIEW because 150 > 100
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="pay_order",
            tool_input={"order_id": order_id}
        )
    assert exc_info.value.status_code == 402
    assert "requires human approval" in str(exc_info.value.detail)

    # 3. Assert database state: Run is WAITING_FOR_APPROVAL, Action is PENDING_APPROVAL
    await db_session.refresh(run)
    assert run.status == RunStatus.WAITING_FOR_APPROVAL

    stmt_pay_act = (
        select(AgentAction)
        .where(AgentAction.run_id == run.id, AgentAction.tool_name == "pay_order")
        .order_by(AgentAction.sequence_number.desc())
    )
    pay_act_res = await db_session.execute(stmt_pay_act)
    pay_act = pay_act_res.scalars().first()
    assert pay_act is not None
    assert pay_act.status == ActionStatus.PENDING_APPROVAL
    assert pay_act.error_code == "APPROVAL_REQUIRED"

    # Assert GateDecision in DB
    gate_dec_stmt = select(GateDecision).where(GateDecision.agent_action_id == pay_act.id)
    gate_dec_res = await db_session.execute(gate_dec_stmt)
    gate_decision = gate_dec_res.scalars().first()
    assert gate_decision is not None
    assert gate_decision.decision == DecisionResult.REVIEW
    assert gate_decision.required_approval is True
    assert "APPROVAL_THRESHOLD_EXCEEDED" in gate_decision.reason_codes

    # Assert pending ApprovalRequest in DB
    appr_stmt = select(ApprovalRequest).where(ApprovalRequest.agent_action_id == pay_act.id)
    appr_res = await db_session.execute(appr_stmt)
    approval = appr_res.scalars().first()
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING
    assert approval.amount == 150
    assert approval.currency == "INR"
    assert approval.transaction_data.get("order_id") == order_id

    # Assert Order remains PENDING_PAYMENT
    order_stmt = select(Order).where(Order.id == order_id)
    order_res = await db_session.execute(order_stmt)
    order = order_res.scalar_one()
    assert order.status == OrderStatus.PENDING_PAYMENT

    # CRUCIAL: Assert 0 Payment records exist for this order in the database!
    payments_stmt = select(Payment).where(Payment.order_id == order_id)
    payments_res = await db_session.execute(payments_stmt)
    assert len(payments_res.scalars().all()) == 0

    # 4. Attempt to resume the run while approval is still PENDING -> Must be denied
    resume_fail_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_fail_resp.status_code == 400
    err_body = resume_fail_resp.json()
    err_msg = err_body.get("error", {}).get("message") or err_body.get("detail", str(err_body))
    assert "PENDING" in err_msg

    # Confirm still no payment
    payments_res = await db_session.execute(payments_stmt)
    assert len(payments_res.scalars().all()) == 0

    # 5. Approver grants valid approval in Approval Center
    appr_svc = ApprovalService(db_session)
    revalidated_gate_dec = await appr_svc.approve(approval.id, ws_id, user.id)
    assert revalidated_gate_dec.decision == DecisionResult.ALLOW
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED

    # 6. Resume the run -> Validates context, issues fresh token, captures payment, consumes approval
    resume_success_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_success_resp.status_code == 200, f"Resume failed: {resume_success_resp.json()}"
    resumed_data = resume_success_resp.json()
    assert resumed_data["status"] == "COMPLETED"

    # 7. Assert persisted database state after valid resume:
    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED

    await db_session.refresh(pay_act)
    assert pay_act.status == ActionStatus.SUCCESS
    assert pay_act.output.get("status") == "PAID"

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    await db_session.refresh(order)
    assert order.status == OrderStatus.PAID
    assert order.payment_id is not None

    # Assert exactly 1 captured Payment record in DB
    payments_after = (await db_session.execute(payments_stmt)).scalars().all()
    assert len(payments_after) == 1
    captured_payment = payments_after[0]
    assert captured_payment.status == PaymentStatus.CAPTURED
    assert captured_payment.amount == 150
    assert captured_payment.currency == "INR"
    assert captured_payment.order_id == order_id

    # 8. Idempotency test: resume again must not charge again or duplicate payment
    resume_again_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_again_resp.status_code == 200
    payments_after_again = (await db_session.execute(payments_stmt)).scalars().all()
    assert len(payments_after_again) == 1

    # In a completed run, execute_action must refuse further action execution
    with pytest.raises(HTTPException) as exc_retry:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="pay_order",
            tool_input={"order_id": order_id}
        )
    assert exc_retry.value.status_code == 400
    assert "completed" in str(exc_retry.value.detail).lower()
    payments_after_tool_retry = (await db_session.execute(payments_stmt)).scalars().all()
    assert len(payments_after_tool_retry) == 1


@pytest.mark.asyncio
async def test_cannot_pay_already_paid_order_from_another_run(base_setup: dict, db_session: AsyncSession):
    """
    Assert that an agent cannot pay or reuse an order paid by a different run.
    Must fail closed with HTTP 400 ORDER_ALREADY_PAID.
    """
    from fastapi import HTTPException

    ws_id = base_setup["workspace"].id
    agent = base_setup["agent"]
    merchant = base_setup["merchant"]

    # Authority with PAY_ORDER capability
    auth_b = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        currency="INR",
        monetary_limit=10000,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        prohibited_actions=[],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db_session.add(auth_b)

    # Order paid by Run A
    order_a = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        status=OrderStatus.PAID,
        payment_id=f"pay_{uuid.uuid4().hex[:16]}",
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order_a)

    # Run B starts fresh with authority
    run_b = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        authority_id=auth_b.id,
        status=RunStatus.RUNNING,
        trigger_type="API",
        input="Purchase laptop"
    )
    db_session.add(run_b)
    await db_session.commit()

    # Run B attempts to pay Order A
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run_b.id,
            tool_name="pay_order",
            tool_input={"order_id": order_a.id}
        )

    assert exc_info.value.status_code == 400
    assert "already paid" in str(exc_info.value.detail).lower()

    # Confirm action is recorded as FAILED with ORDER_ALREADY_PAID
    stmt_act = select(AgentAction).where(AgentAction.run_id == run_b.id)
    res_act = await db_session.execute(stmt_act)
    action = res_act.scalar_one()
    assert action.status == ActionStatus.FAILED
    assert action.error_code == "ORDER_ALREADY_PAID"


@pytest.mark.asyncio
async def test_missing_intent_alignment_fails_closed(base_setup: dict, db_session: AsyncSession):
    """
    Assert that protected actions with an attached intent fail closed (BLOCK)
    if intent alignment is missing or unknown. Never converts to ALLOW.
    """
    from fastapi import HTTPException

    ws_id = base_setup["workspace"].id
    agent = base_setup["agent"]
    merchant = base_setup["merchant"]

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        currency="INR",
        monetary_limit=10000,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db_session.add(authority)

    # Intent with specific disallowed category
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        title="Books Only",
        natural_language_request="Buy books only",
        intent_type=IntentType.PURCHASE,
        structured_constraints={
            "product": {"category": "books"},
            "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"]
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=authority.id,
        status=RunStatus.RUNNING,
        trigger_type="API",
        input="Buy laptop"
    )
    db_session.add(run)

    # Order with category electronics (mismatched)
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=150,
        total=150
    )
    db_session.add(order)

    # Add item with electronics category
    product_elec = Product(
        id=f"prd_{uuid.uuid4().hex[:16]}",
        merchant_id=merchant.id,
        name="Laptop",
        category="electronics",
        price=150,
        currency="INR",
        inventory=10,
        status=ProductStatus.ACTIVE
    )
    db_session.add(product_elec)

    item = OrderItem(
        id=f"ori_{uuid.uuid4().hex[:16]}",
        order_id=order.id,
        product_id=product_elec.id,
        product_name_snapshot="Laptop",
        merchant_name_snapshot="Merchant",
        quantity=1,
        unit_price_at_order=150,
        total=150
    )
    db_session.add(item)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="pay_order",
            tool_input={"order_id": order.id}
        )

    assert exc_info.value.status_code == 403
    assert "blocked" in str(exc_info.value.detail).lower()

    # Verify GateDecision is BLOCK
    gdec_stmt = select(GateDecision).where(GateDecision.agent_run_id == run.id)
    gdec = (await db_session.execute(gdec_stmt)).scalars().first()
    assert gdec is not None
    assert gdec.decision == DecisionResult.BLOCK
    assert "INTENT_MISALIGNED" in gdec.reason_codes


async def _create_pending_approval_run(base_setup: dict, db_session: AsyncSession, amount: int = 150):
    """
    Helper that sets up an agent run requiring approval for pay_order of `amount`.
    Returns run, order, approval, agent, workspace_id, product.
    """
    from fastapi import HTTPException
    ws_id = base_setup["workspace"].id
    agent = base_setup["agent"]
    product = base_setup["product"]

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        currency="INR",
        monetary_limit=10000,
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "ADD_CART_ITEM", "CREATE_ORDER", "PAY_ORDER"],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db_session.add(authority)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        title="Approved Laptop Purchase",
        natural_language_request="Purchase laptop with approval",
        intent_type=IntentType.PURCHASE,
        structured_constraints={
            "amount": {"maximum": 40000, "currency": "INR"},
            "product": {"category": "electronics", "keywords": ["laptop"]},
            "approval": {"approval_required_above": 100, "approval_required": True},
            "allowed_actions": ["SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"]
        },
        status=IntentStatus.ACTIVE,
        version=1
    )
    db_session.add(intent)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=intent.id,
        authority_id=authority.id,
        status=RunStatus.RUNNING,
        trigger_type="API",
        input=f"Purchase the Budget Laptop 15-inch for ₹{amount}. My intent permits this purchase, but require my approval before payment because the amount exceeds ₹100. Do not make any other purchase or exceed my delegated authority. Stop and wait for my approval before capturing payment."
    )
    db_session.add(run)

    cart = Cart(
        id=f"crt_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=CartStatus.ACTIVE,
        currency="INR"
    )
    db_session.add(cart)

    citem = CartItem(
        id=f"cti_{uuid.uuid4().hex[:16]}",
        cart_id=cart.id,
        product_id=product.id,
        quantity=1
    )
    db_session.add(citem)
    await db_session.commit()

    # Checkout
    act_co = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="checkout",
        tool_input={"cart_id": cart.id}
    )
    order_id = act_co.output["order_id"]

    # pay_order -> triggers 402 REVIEW
    with pytest.raises(HTTPException) as exc_info:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="pay_order",
            tool_input={"order_id": order_id}
        )
    assert exc_info.value.status_code == 402

    # Fetch approval
    appr_stmt = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    approval = (await db_session.execute(appr_stmt)).scalars().first()

    order_stmt = select(Order).where(Order.id == order_id)
    order = (await db_session.execute(order_stmt)).scalar_one()

    return {
        "run": run,
        "order": order,
        "approval": approval,
        "agent": agent,
        "workspace_id": ws_id,
        "product": product
    }


@pytest.mark.asyncio
async def test_approval_decision_approve_flow(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Test valid APPROVE decision:
    1. Validates exact order, amount, currency, agent, workspace.
    2. Marks approval APPROVED without capturing payment.
    3. Run remains WAITING_FOR_APPROVAL and Order remains PENDING_PAYMENT.
    4. Resuming the run authoritatively captures payment, marks order PAID, consumes approval, and finishes run.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]
    order = ctx["order"]
    run = ctx["run"]
    agent = ctx["agent"]
    ws_id = ctx["workspace_id"]

    # Assert pre-decision state
    assert approval.status == ApprovalStatus.PENDING
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert run.status == RunStatus.WAITING_FOR_APPROVAL

    # Call approval decision API
    resp = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={
            "decision": "APPROVED",
            "reason": "Approved by supervisor",
            "order_id": order.id,
            "amount": 150,
            "currency": "INR",
            "agent_id": agent.id,
            "workspace_id": ws_id
        }
    )
    assert resp.status_code == 200, f"Approval decision failed: {resp.text}"
    resp_data = resp.json()
    assert resp_data["decision"] == "ALLOW"
    assert resp_data["status"] == "APPROVED"
    assert resp_data["approval_id"] == approval.id

    # Verify DB state: Approval is APPROVED, but order is NOT paid yet and run is NOT finished yet
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED

    await db_session.refresh(order)
    assert order.status == OrderStatus.PENDING_PAYMENT

    await db_session.refresh(run)
    assert run.status == RunStatus.WAITING_FOR_APPROVAL

    # Ensure zero payment records exist yet
    p_stmt = select(Payment).where(Payment.order_id == order.id)
    payments = (await db_session.execute(p_stmt)).scalars().all()
    assert len(payments) == 0, "Approval alone must NOT capture payment before authoritative resume"

    # Now resume the run
    resume_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_resp.status_code == 200, f"Resume failed: {resume_resp.text}"
    assert resume_resp.json()["status"] == "COMPLETED"

    # Post-resume state: Order is PAID, Payment CAPTURED, Approval CONSUMED
    await db_session.refresh(order)
    assert order.status == OrderStatus.PAID

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    payments_post = (await db_session.execute(p_stmt)).scalars().all()
    assert len(payments_post) == 1
    assert payments_post[0].status == PaymentStatus.CAPTURED
    assert payments_post[0].amount == 150


@pytest.mark.asyncio
async def test_approval_decision_reject_lifecycle(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Test REJECT decision:
    1. Rejection cancels the unpaid order and restores inventory.
    2. Marks run BLOCKED and action DENIED.
    3. Cannot resume a rejected/blocked run.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]
    order = ctx["order"]
    run = ctx["run"]
    product = ctx["product"]

    await db_session.refresh(product)
    inv_after_checkout = product.inventory

    # Reject via API
    resp = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={
            "decision": "REJECTED",
            "reason": "Exceeds authorized limit",
            "order_id": order.id
        }
    )
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["decision"] == "REJECTED"
    assert resp_data["status"] == "REJECTED"

    # Verify DB state
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.REJECTED

    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED

    await db_session.refresh(product)
    assert product.inventory == inv_after_checkout + 1, "Inventory must be restored upon rejection"

    await db_session.refresh(run)
    assert run.status == RunStatus.BLOCKED

    # Check pay_order action status
    act_stmt = select(AgentAction).where(AgentAction.run_id == run.id, AgentAction.tool_name == "pay_order")
    act = (await db_session.execute(act_stmt)).scalars().first()
    assert act is not None
    assert act.status == ActionStatus.DENIED

    # Resume must be rejected
    resume_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_resp.status_code == 400


@pytest.mark.asyncio
async def test_approval_decision_invalid_requests(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Assert invalid decision values and non-existent approvals return HTTP 400/404.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]

    # Invalid decision string
    resp_invalid = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "MAYBE"}
    )
    assert resp_invalid.status_code == 400
    assert "APPROVED" in resp_invalid.text and "REJECTED" in resp_invalid.text

    # Non-existent approval ID
    resp_404 = await client.post(
        "/api/v1/approvals/appr_nonexistent12345/decision",
        headers=headers,
        json={"decision": "APPROVED"}
    )
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_approval_decision_expired(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Assert expired approval cannot be decided; returns HTTP 400 and marks status EXPIRED.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]

    # Set expired timestamp in DB
    approval.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED"}
    )
    assert resp.status_code == 400
    assert "expired" in resp.text.lower()

    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.EXPIRED


@pytest.mark.asyncio
async def test_approval_decision_mismatched_context(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Assert decision fails if order_id, amount, currency, agent_id, or workspace_id do not match.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]
    order = ctx["order"]
    agent = ctx["agent"]
    ws_id = ctx["workspace_id"]

    # Mismatched order_id
    resp_ord = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "order_id": "ord_wrong_order_123"}
    )
    assert resp_ord.status_code == 400
    assert "order" in resp_ord.text.lower()

    # Mismatched amount
    resp_amt = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "amount": 999.0}
    )
    assert resp_amt.status_code == 400
    assert "amount" in resp_amt.text.lower()

    # Mismatched currency
    resp_curr = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "currency": "USD"}
    )
    assert resp_curr.status_code == 400
    assert "currency" in resp_curr.text.lower()

    # Mismatched agent_id
    resp_agt = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "agent_id": "agt_other_agent_999"}
    )
    assert resp_agt.status_code == 400
    assert "agent" in resp_agt.text.lower()

    # Mismatched workspace_id
    resp_ws = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "workspace_id": "ws_other_ws_888"}
    )
    assert resp_ws.status_code == 400
    assert "workspace" in resp_ws.text.lower()

    # Verify approval remains untouched in PENDING
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_approval_decision_duplicate_and_replay_prevention(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Assert duplicate decision or replay on non-pending approval returns HTTP 400.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    approval = ctx["approval"]
    order = ctx["order"]
    run = ctx["run"]

    # First approve succeeds
    resp1 = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "order_id": order.id}
    )
    assert resp1.status_code == 200

    # Second approve fails
    resp2 = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "order_id": order.id}
    )
    assert resp2.status_code == 400
    assert "already" in resp2.text.lower()

    # Reject on already approved fails
    resp3 = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "REJECTED", "order_id": order.id}
    )
    assert resp3.status_code == 400
    assert "already" in resp3.text.lower()

    # Resume to consume approval
    resume_resp = await client.post(
        f"/api/v1/agent-runtime/runs/{run.id}/resume",
        headers=headers
    )
    assert resume_resp.status_code == 200
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.CONSUMED

    # Decision on consumed approval fails
    resp4 = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "order_id": order.id}
    )
    assert resp4.status_code == 400
    assert "already consumed" in resp4.text.lower()


@pytest.mark.asyncio
async def test_decision_trace_authoritative_distinction(client: AsyncClient, base_setup: dict, db_session: AsyncSession):
    """
    Assert that the Decision Trace API reports REVIEW_REQUIRED (not earlier step ALLOW)
    when a run is waiting for approval, and BLOCK when rejected.
    """
    headers = base_setup["headers"]
    ctx = await _create_pending_approval_run(base_setup, db_session, amount=150)
    run = ctx["run"]
    approval = ctx["approval"]
    order = ctx["order"]

    # 1. Fetch trace while run is WAITING_FOR_APPROVAL
    trace_resp = await client.get(
        f"/api/v1/agent-runtime/runs/{run.id}/decision-trace",
        headers=headers
    )
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()

    # Authoritative final decision must be REVIEW_REQUIRED, NOT the earlier checkout's ALLOW!
    assert trace_data["final_decision"] == "REVIEW_REQUIRED"
    assert trace_data["final_gate_decision"] == "REVIEW_REQUIRED"
    assert trace_data["run_status"] == "WAITING_FOR_APPROVAL"

    # 2. Reject the approval
    reject_resp = await client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers=headers,
        json={"decision": "REJECTED", "order_id": order.id}
    )
    assert reject_resp.status_code == 200

    # 3. Fetch trace after rejection -> final_decision must be BLOCK
    trace_after = await client.get(
        f"/api/v1/agent-runtime/runs/{run.id}/decision-trace",
        headers=headers
    )
    assert trace_after.status_code == 200
    trace_after_data = trace_after.json()
    assert trace_after_data["final_decision"] == "BLOCK"
    assert trace_after_data["final_gate_decision"] == "BLOCK"
    assert trace_after_data["run_status"] == "BLOCKED"


