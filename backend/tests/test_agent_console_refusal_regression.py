import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.agent import Agent, AgentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.intent import Intent, IntentType, IntentStatus
from app.models.agent_runtime import AgentRun, AgentAction, ActionStatus, RunStatus
from app.models.commerce import Merchant, Product, Cart, CartItem, Order, OrderItem
from app.models.payment import Payment, PaymentStatus
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.services.agent_runtime_service import AgentRuntimeService
from app.services.intent_extractor import extract_intent, _is_search_only_or_prohibits_purchase
from app.api.routes.agent_runtime import _populate_run_authoritative_decision


@pytest.fixture
async def regression_test_context(client: AsyncClient, db_session: AsyncSession):
    email = f"refusal_tester_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Refusal Regression Tester"
    })
    assert signup_res.status_code in [200, 201], signup_res.text

    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    headers = {"X-Workspace-ID": ws_id}

    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Reliable Tech"
    )
    db_session.add(merchant)
    await db_session.flush()

    laptop = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant.id,
        name="Budget Laptop 15-inch",
        category="ELECTRONICS",
        price=150.0,
        currency="INR",
        inventory=10
    )
    db_session.add(laptop)
    await db_session.flush()

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

    purchase_intent = Intent(
        id=f"int_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_type=IntentType.PURCHASE,
        status=IntentStatus.ACTIVE,
        title="Purchase Budget Laptop 15-inch up to 40,000 INR",
        natural_language_request="Purchase Budget Laptop 15-inch up to 40,000 INR",
        structured_constraints={
            "max_budget": 40000.0,
            "currency": "INR",
            "approval_threshold": 100.0,
            "category": "electronics",
            "keywords": ["laptop"]
        },
        version=1
    )
    db_session.add(purchase_intent)
    await db_session.flush()

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        intent_id=purchase_intent.id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=40000.0,
        approval_threshold=100.0,
        currency="INR",
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM", "ADD_TO_CART",
            "MANAGE_CART", "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        ],
        version=1
    )
    db_session.add(authority)
    await db_session.commit()

    return {
        "cookies": cookies,
        "headers": headers,
        "ws_id": ws_id,
        "user_id": user_id,
        "agent": agent,
        "authority": authority,
        "purchase_intent": purchase_intent,
        "laptop": laptop
    }


@pytest.mark.asyncio
async def test_search_only_prompt_restricts_to_search_and_blocks_side_effects(
    db_session: AsyncSession,
    regression_test_context
):
    """
    Search-only requests can only search and never create carts, orders, or payments.
    Asserts database side effects: zero carts/orders/payments created.
    """
    ctx = regression_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id

    search_prompt = "Search for Budget Laptop 15-inch under ₹200. Do not create carts, orders, or payments."

    # 1. Verify pattern detection correctly classifies search-only
    assert _is_search_only_or_prohibits_purchase(search_prompt) is True

    # 2. Create Run
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=search_prompt,
        authority_id=auth_id
    )
    assert run.id is not None
    assert run.status == RunStatus.RUNNING

    # 3. Intent should have search_only constraint and prohibited side-effect actions
    run_intent = await db_session.get(Intent, run.intent_id)
    assert run_intent is not None
    assert run_intent.intent_type == IntentType.SEARCH
    constraints = run_intent.structured_constraints or {}
    assert constraints.get("search_only") is True
    assert "create_cart" in constraints.get("prohibited_actions", [])
    assert "pay_order" in constraints.get("prohibited_actions", [])

    # 4. Search action succeeds
    search_act = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="search_products",
        tool_input={"query": "Budget Laptop"}
    )
    assert search_act.status == ActionStatus.SUCCESS

    # 5. create_cart fails closed and stops the run
    with pytest.raises(HTTPException) as exc_cart:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="create_cart",
            tool_input={}
        )
    assert exc_cart.value.status_code == 403

    await db_session.refresh(run)
    assert run.status == RunStatus.BLOCKED

    # Assert zero persisted commerce side-effects
    carts = (await db_session.execute(select(Cart).where(Cart.workspace_id == ws_id))).scalars().all()
    assert len(carts) == 0

    orders = (await db_session.execute(select(Order).where(Order.workspace_id == ws_id))).scalars().all()
    assert len(orders) == 0

    payments = (await db_session.execute(select(Payment).where(Payment.workspace_id == ws_id))).scalars().all()
    assert len(payments) == 0


@pytest.mark.asyncio
async def test_purchase_prompt_with_negative_substitution_not_flagged_as_search_only(
    db_session: AsyncSession,
    regression_test_context
):
    """
    User prompt with negative constraints ('Do not substitute another product...')
    must NOT be flagged as search-only, and must link active purchase intent & delegated authority.
    """
    ctx = regression_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    purchase_intent_id = ctx["purchase_intent"].id

    exact_user_prompt = (
        "Purchase exactly one Budget Laptop 15-inch for ₹150 using my linked purchase intent "
        "and delegated authority. Do not substitute another product or change the amount. "
        "If approval is required, stop and wait for my approval. Otherwise, complete the sandbox purchase."
    )

    # 1. Assert regex does NOT misclassify negative substitution as negative purchase
    assert _is_search_only_or_prohibits_purchase(exact_user_prompt) is False

    # 2. Create Run
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=exact_user_prompt,
        authority_id=auth_id
    )
    assert run.id is not None
    assert run.status == RunStatus.RUNNING

    # 3. Assert attached active purchase intent and authority are used, NOT a throwaway search intent
    assert run.intent_id == purchase_intent_id
    assert run.authority_id == auth_id

    run_intent = await db_session.get(Intent, run.intent_id)
    assert run_intent is not None
    assert run_intent.intent_type == IntentType.PURCHASE
    assert (run_intent.structured_constraints or {}).get("search_only") is not True


@pytest.mark.asyncio
async def test_approval_required_purchase_stops_at_review_and_waits_for_approval(
    db_session: AsyncSession,
    regression_test_context
):
    """
    When purchase amount (₹150) exceeds approval threshold (₹100),
    Action Gate MUST evaluate to REVIEW (APPROVAL_THRESHOLD_EXCEEDED),
    stop execution, pause run at WAITING_FOR_APPROVAL, and persist PENDING ApprovalRequest.
    """
    ctx = regression_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    prod_id = ctx["laptop"].id

    prompt = (
        "Purchase exactly one Budget Laptop 15-inch for ₹150 using my linked purchase intent and delegated authority."
    )

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=prompt,
        authority_id=auth_id
    )

    # 1. Create cart
    cart_act = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="create_cart",
        tool_input={}
    )
    assert cart_act.status == ActionStatus.SUCCESS
    cart_id = cart_act.output["cart_id"]

    # 2. Add item (1 x ₹150)
    add_act = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="add_to_cart",
        tool_input={"cart_id": cart_id, "product_id": prod_id, "quantity": 1}
    )
    assert add_act.status == ActionStatus.SUCCESS

    # 3. Checkout
    checkout_act = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="checkout",
        tool_input={"cart_id": cart_id}
    )
    assert checkout_act.status == ActionStatus.SUCCESS
    order_id = checkout_act.output["order_id"]

    # 4. Attempt to pay order (₹150 > threshold ₹100)
    with pytest.raises(HTTPException) as exc_review:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="pay_order",
            tool_input={"order_id": order_id}
        )
    assert exc_review.value.status_code == 402
    assert "approval" in exc_review.value.detail.lower()

    # Assert Run status paused at WAITING_FOR_APPROVAL
    await db_session.refresh(run)
    assert run.status == RunStatus.WAITING_FOR_APPROVAL

    # Assert database side effects:
    # 1. ApprovalRequest exists with status PENDING and bound_amount == 150.0
    approvals = (await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
    )).scalars().all()
    assert len(approvals) == 1
    approval = approvals[0]
    assert approval.status == ApprovalStatus.PENDING
    assert float(approval.amount) == 150.0
    assert approval.currency == "INR"
    assert (approval.transaction_data or {}).get("order_id") == order_id

    # 2. Payment is NOT captured
    payments = (await db_session.execute(
        select(Payment).where(Payment.order_id == order_id)
    )).scalars().all()
    assert all(p.status != PaymentStatus.CAPTURED for p in payments)


@pytest.mark.asyncio
async def test_purchase_without_authority_fails_closed(
    db_session: AsyncSession,
    regression_test_context
):
    """
    Missing or invalid authority must fail closed.
    Execution of protected commerce action without authority is denied and stops run.
    """
    ctx = regression_test_context
    ws_id = ctx["ws_id"]

    # Create an agent WITHOUT delegated authority
    unauthorized_agent = Agent(
        id=f"agent_unauth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_id,
        name="Unauthorized Agent",
        type="SHOPPING",
        status=AgentStatus.ACTIVE,
        currency="INR",
        capabilities=["SEARCH_PRODUCTS"]  # No commerce capabilities
    )
    db_session.add(unauthorized_agent)
    await db_session.commit()

    prompt = "Purchase one Budget Laptop for ₹150."

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=unauthorized_agent.id,
        input_text=prompt,
        authority_id=None
    )
    assert run.authority_id is None

    # Attempting to execute create_cart without authority fails closed
    with pytest.raises(HTTPException) as exc:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="create_cart",
            tool_input={}
        )
    assert exc.value.status_code == 403
    assert "authority" in exc.value.detail.lower() or "denied" in exc.value.detail.lower()

    await db_session.refresh(run)
    assert run.status == RunStatus.BLOCKED

    # Assert no carts or orders were created
    carts = (await db_session.execute(select(Cart).where(Cart.workspace_id == ws_id))).scalars().all()
    assert len(carts) == 0


@pytest.mark.asyncio
async def test_unexecuted_financial_request_not_classified_as_read_only(
    db_session: AsyncSession,
    regression_test_context
):
    """
    A financial request where the model refuses or fails without executing tools
    must NOT be classified as READ-ONLY / NOT EVALUATED.
    It must be classified as FAILED with error_code LLM_REFUSAL.
    """
    ctx = regression_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id

    prompt = "Purchase exactly one Budget Laptop 15-inch for ₹150."

    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=prompt,
        authority_id=auth_id
    )

    # Simulate model returning refusal without executing any tools
    refusal_text = "I'm sorry, but I can't help with that."
    await AgentRuntimeService.finish_run(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        output=refusal_text,
        status=RunStatus.FAILED,
        error_code="LLM_REFUSAL",
        error_message=f"Model refused request: {refusal_text}"
    )

    await db_session.refresh(run)
    assert run.status == RunStatus.FAILED
    assert run.error_code == "LLM_REFUSAL"

    # Verify authoritative decision population
    authoritative_dec = _populate_run_authoritative_decision(run)
    assert authoritative_dec != "NOT EVALUATED", "Financial refusal must not be labeled NOT EVALUATED"
    assert authoritative_dec == "FAILED", f"Expected FAILED, got {authoritative_dec}"
