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
from app.models.commerce import Merchant, Product, Cart, CartItem, Order, OrderItem
from app.models.payment import Payment
from app.models.gate import GateDecision, DecisionResult
from app.services.agent_runtime_service import AgentRuntimeService


@pytest.fixture
async def search_only_test_context(client: AsyncClient, db_session: AsyncSession):
    email = f"search_tester_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Search Only Tester"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    headers = {"X-Workspace-ID": ws_id}
    
    # 1. Create a merchant & products
    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Reliable Tech"
    )
    db_session.add(merchant)
    await db_session.flush()

    laptop_cheap = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant.id,
        name="Budget Chromebook Laptop",
        category="LAPTOP",
        price=18990,
        currency="INR",
        inventory=10
    )
    laptop_expensive = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant.id,
        name="Pro Gaming Laptop",
        category="LAPTOP",
        price=75000,
        currency="INR",
        inventory=5
    )
    db_session.add_all([laptop_cheap, laptop_expensive])
    await db_session.flush()

    # 2. Create an agent with broad purchase-capable capabilities
    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Broad Purchase Agent",
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

    # 3. Create a broad purchase-capable delegated authority
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=100000.0,
        approval_threshold=50000.0,
        currency="INR",
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
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
        "product_cheap": laptop_cheap,
        "product_expensive": laptop_expensive,
    }


@pytest.mark.asyncio
async def test_search_only_intent_enforcement_prevents_all_purchase_side_effects(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Exact user request:
    "Find me a laptop under ₹20,000. Only search and show me matching products. Do not add anything to the cart, create an order, or make a payment."

    Assert:
    1. search_products executes successfully.
    2. create_cart, add_to_cart, checkout, and pay_order are categorically prohibited and denied before execution.
    3. Authoritative gate decisions emit BLOCK with INTENT_MISALIGNED_SEARCH_ONLY / INTENT_MISALIGNED.
    4. Zero carts, cart items, orders, or payments are persisted in the database.
    5. Product stock quantities remain completely unchanged.
    6. Agent Console runtime reports truthful denial without falsely labeling ALLOW or ALIGNED.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    prod_cheap_id = ctx["product_cheap"].id

    exact_user_request = (
        "Find me a laptop under ₹20,000. Only search and show me matching products. "
        "Do not add anything to the cart, create an order, or make a payment."
    )

    # 1. Create Run in Agent Console runtime with the exact prompt
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=exact_user_request,
        authority_id=auth_id
    )
    assert run.id is not None
    assert run.status == RunStatus.RUNNING

    # 2. Verify run intent was extracted dynamically from the prompt and marked SEARCH / search-only
    run_intent = await db_session.get(Intent, run.intent_id)
    assert run_intent is not None
    assert run_intent.intent_type == IntentType.SEARCH
    constraints = run_intent.structured_constraints or {}
    assert constraints.get("search_only") is True
    assert "search_products" in constraints.get("allowed_actions", [])
    assert "create_cart" in constraints.get("prohibited_actions", [])
    assert "add_to_cart" in constraints.get("prohibited_actions", [])
    assert "checkout" in constraints.get("prohibited_actions", [])
    assert "pay_order" in constraints.get("prohibited_actions", [])

    # 3. Assert search_products CAN SUCCEED
    search_action = await AgentRuntimeService.execute_action(
        db=db_session,
        workspace_id=ws_id,
        run_id=run.id,
        tool_name="search_products",
        tool_input={"query": "laptop", "max_price": 20000}
    )
    assert search_action.status == ActionStatus.SUCCESS
    assert search_action.output is not None
    found_products = search_action.output.get("results", [])
    assert len(found_products) >= 1
    assert any(p["product_id"] == prod_cheap_id for p in found_products)

    # 4. Assert create_cart is CATEGORICALLY DENIED before execution and stops the run
    with pytest.raises(HTTPException) as exc_create_cart:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="create_cart",
            tool_input={}
        )
    assert exc_create_cart.value.status_code == 403
    assert "prohibited" in exc_create_cart.value.detail.lower() or "blocked" in exc_create_cart.value.detail.lower()

    # Verify run is STOPPED in BLOCKED status
    await db_session.refresh(run)
    assert run.status == RunStatus.BLOCKED
    assert run.completed_at is not None

    # Verify that further actions on this stopped run are strictly rejected
    with pytest.raises(HTTPException) as exc_subsequent:
        await AgentRuntimeService.execute_action(
            db=db_session,
            workspace_id=ws_id,
            run_id=run.id,
            tool_name="checkout",
            tool_input={"cart_id": "dummy_cart"}
        )
    assert exc_subsequent.value.status_code == 400
    assert "BLOCKED" in exc_subsequent.value.detail

    # Verify persisted action record for create_cart
    stmt_cart_act = (
        select(AgentAction)
        .where(AgentAction.run_id == run.id, AgentAction.tool_name == "create_cart")
    )
    res_cart_act = await db_session.execute(stmt_cart_act)
    cart_act = res_cart_act.scalars().first()
    assert cart_act is not None
    assert cart_act.status == ActionStatus.DENIED
    assert cart_act.alignment_result == "MISALIGNED"
    assert cart_act.error_code in ["INTENT_MISALIGNED_SEARCH_ONLY", "INTENT_MISALIGNED"]

    # Verify authoritative GateDecision record for create_cart
    stmt_gd_cart = select(GateDecision).where(GateDecision.agent_action_id == cart_act.id)
    res_gd_cart = await db_session.execute(stmt_gd_cart)
    gd_cart = res_gd_cart.scalars().first()
    assert gd_cart is not None
    assert gd_cart.decision == DecisionResult.BLOCK
    assert "INTENT_MISALIGNED_SEARCH_ONLY" in gd_cart.reason_codes or "INTENT_MISALIGNED" in gd_cart.reason_codes

    # 5. Test each other prohibited tool (add_to_cart, checkout, pay_order) on fresh search-only runs:
    for prohibited_tool, test_input in [
        ("add_to_cart", {"cart_id": "dummy_cart", "product_id": prod_cheap_id, "quantity": 1}),
        ("checkout", {"cart_id": "dummy_cart"}),
        ("pay_order", {"order_id": "dummy_order"}),
    ]:
        test_run = await AgentRuntimeService.create_run(
            db=db_session,
            workspace_id=ws_id,
            agent_id=agent_id,
            input_text=exact_user_request,
            authority_id=auth_id
        )
        with pytest.raises(HTTPException) as exc_tool:
            await AgentRuntimeService.execute_action(
                db=db_session,
                workspace_id=ws_id,
                run_id=test_run.id,
                tool_name=prohibited_tool,
                tool_input=test_input
            )
        assert exc_tool.value.status_code == 403
        await db_session.refresh(test_run)
        assert test_run.status == RunStatus.BLOCKED

        stmt_act = select(AgentAction).where(AgentAction.run_id == test_run.id, AgentAction.tool_name == prohibited_tool)
        res_act = await db_session.execute(stmt_act)
        tool_act = res_act.scalars().first()
        assert tool_act is not None
        assert tool_act.status == ActionStatus.DENIED
        assert tool_act.alignment_result == "MISALIGNED"

    # 6. Assert DATABASE EVIDENCE: Zero side effects persisted across all attempts
    from app.models.gate import ApprovalRequest
    res_carts = await db_session.execute(select(func.count(Cart.id)).where(Cart.workspace_id == ws_id))
    assert res_carts.scalar() == 0, "No cart must ever be created for search-only intent"

    res_cart_items = await db_session.execute(select(func.count(CartItem.id)))
    assert res_cart_items.scalar() == 0, "No cart item must ever be created for search-only intent"

    res_orders = await db_session.execute(select(func.count(Order.id)).where(Order.workspace_id == ws_id))
    assert res_orders.scalar() == 0, "No order must ever be created for search-only intent"

    res_payments = await db_session.execute(select(func.count(Payment.id)).where(Payment.workspace_id == ws_id))
    assert res_payments.scalar() == 0, "No payment must ever be created for search-only intent"

    res_apprs = await db_session.execute(select(func.count(ApprovalRequest.id)).where(ApprovalRequest.workspace_id == ws_id))
    assert res_apprs.scalar() == 0, "No approval request must ever be created for search-only intent"

    # Assert stock unchanged
    prod_cheap_db = await db_session.get(Product, prod_cheap_id)
    assert prod_cheap_db.inventory == 10, "Product stock must remain unchanged"

    # 9. Assert API endpoint truthfully reports the authoritative decision (ALLOW / ALIGNED must not be falsely displayed)
    run_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert run_res.status_code == 200
    run_json = run_res.json()
    actions_json = run_json.get("actions", [])

    for a in actions_json:
        if a["tool_name"] == "search_products":
            assert a["status"] == "SUCCESS"
        elif a["tool_name"] in ["create_cart", "add_to_cart", "checkout", "pay_order"]:
            assert a["status"] == "DENIED"
            assert a["alignment_result"] == "MISALIGNED"
            assert a["gate_decision"] == "BLOCK"

    # 10. Assert Decision Trace endpoint reports final decision as BLOCK
    trace_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run.id}/decision-trace",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert trace_res.status_code == 200
    trace_json = trace_res.json()
    assert trace_json.get("final_decision") == "BLOCK"
    assert trace_json.get("final_gate_decision") == "BLOCK"


@pytest.mark.asyncio
async def test_search_only_request_completes_successfully_without_side_effects_or_approvals(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Assert that a search-only request finishes successfully after returning matching products,
    without creating a cart, order, approval request, or payment.
    Forbidden tools are denied before side effects if attempted.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    prod_cheap_id = ctx["product_cheap"].id

    exact_user_request = (
        "Find me a laptop under ₹20,000. Only search and show me matching products. "
        "Do not add anything to the cart, create an order, or make a payment."
    )

    # 1. Create run via API
    create_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": exact_user_request,
            "authority_id": auth_id,
            "auto_start": False
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert create_res.status_code == 200
    run_id = create_res.json()["id"]

    # 2. Execute search_products via action API
    search_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={
            "tool_name": "search_products",
            "input": {"query": "laptop", "max_price": 20000}
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["status"] == "SUCCESS"
    results = search_data.get("output", {}).get("results", [])
    assert len(results) >= 1
    matching_product = next(p for p in results if p["product_id"] == prod_cheap_id)
    assert matching_product["price"] <= 20000

    # 3. Finish run successfully with the matching products directly after search (clean path)
    output_text = (
        f"Found 1 matching laptop: {matching_product['name']} for ₹{matching_product['price']}. "
        "No cart was created, no order placed, and no payment captured as requested."
    )
    finish_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/finish",
        json={
            "output": output_text,
            "status": "COMPLETED"
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert finish_res.status_code == 200
    run_finished = finish_res.json()
    assert run_finished["status"] == "COMPLETED"
    assert matching_product["name"] in run_finished["output"]

    # Assert clean search-only run reports NOT EVALUATED (not ALLOW)
    get_run_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run_id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert get_run_res.status_code == 200
    run_detail = get_run_res.json()
    assert run_detail["status"] == "COMPLETED"
    assert run_detail["gate_decision"] == "NOT EVALUATED"
    assert run_detail["authoritative_decision"] == "NOT EVALUATED"

    # 4. Now test that if a search-only run attempts create_cart, it is rejected with 403 and stopped as BLOCKED
    run_blocked = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=exact_user_request,
        authority_id=auth_id
    )
    cart_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_blocked.id}/actions",
        json={
            "tool_name": "create_cart",
            "input": {}
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert cart_res.status_code == 403
    await db_session.refresh(run_blocked)
    assert run_blocked.status == RunStatus.BLOCKED

    # 5. Assert DB evidence across workspace: zero carts, zero orders, zero payments, zero approval requests
    from app.models.gate import ApprovalRequest
    carts_cnt = (await db_session.execute(select(func.count(Cart.id)).where(Cart.workspace_id == ws_id))).scalar()
    assert carts_cnt == 0, "No cart should be created"

    orders_cnt = (await db_session.execute(select(func.count(Order.id)).where(Order.workspace_id == ws_id))).scalar()
    assert orders_cnt == 0, "No order should be created"

    payments_cnt = (await db_session.execute(select(func.count(Payment.id)).where(Payment.workspace_id == ws_id))).scalar()
    assert payments_cnt == 0, "No payment should be created"

    approvals_cnt = (await db_session.execute(select(func.count(ApprovalRequest.id)).where(ApprovalRequest.workspace_id == ws_id))).scalar()
    assert approvals_cnt == 0, "No approval request should be created for search-only run"


@pytest.mark.asyncio
async def test_review_required_run_never_reports_allow_in_api(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Assert that the runtime's headline decision reflects the latest authoritative gate decision
    and execution status. The API and UI must NEVER display ALLOW when the run is WAITING_FOR_APPROVAL
    or the latest authoritative decision is REVIEW_REQUIRED.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    prod_cheap_id = ctx["product_cheap"].id

    # 1. Create an authority with low approval threshold to trigger REVIEW_REQUIRED
    low_threshold_auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=100000.0,
        approval_threshold=100.0, # product price is 18990 > 100, requires approval
        currency="INR",
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        ],
        version=1
    )
    db_session.add(low_threshold_auth)
    await db_session.commit()

    # 2. Create Run with purchase objective
    purchase_request = "Purchase Budget Chromebook Laptop for my team."
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": purchase_request,
            "authority_id": low_threshold_auth.id,
            "auto_start": False
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # 3. Execute search -> create_cart -> add_to_cart -> checkout (these succeed with ALLOW)
    await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "search_products", "input": {"query": "Chromebook"}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    c_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "create_cart", "input": {}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    cart_id = c_res.json()["output"]["cart_id"]

    await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_cheap_id, "quantity": 1}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    co_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert co_res.status_code == 200
    order_id = co_res.json()["output"]["order_id"]

    # 4. Propose pay_order (exceeds 100 INR threshold -> requires review)
    pay_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert pay_res.status_code in [200, 402]
    stmt_pay = select(AgentAction).where(AgentAction.run_id == run_id, AgentAction.tool_name == "pay_order")
    res_pay = await db_session.execute(stmt_pay)
    pay_action = res_pay.scalars().first()
    assert pay_action is not None
    assert pay_action.status == ActionStatus.PENDING_APPROVAL

    # Set run status to WAITING_FOR_APPROVAL
    run_obj = await db_session.get(AgentRun, run_id)
    run_obj.status = RunStatus.WAITING_FOR_APPROVAL
    await db_session.commit()

    # 5. Assert GET /runs/{run_id} reports REVIEW_REQUIRED, NEVER ALLOW
    get_run = await client.get(
        f"/api/v1/agent-runtime/runs/{run_id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert get_run.status_code == 200
    run_json = get_run.json()
    assert run_json["status"] == "WAITING_FOR_APPROVAL"
    assert run_json["gate_decision"] == "REVIEW_REQUIRED"
    assert run_json["authoritative_decision"] == "REVIEW_REQUIRED"
    assert run_json["gate_decision"] != "ALLOW"
    assert run_json["authoritative_decision"] != "ALLOW"

    # 6. Assert Decision Trace reports REVIEW_REQUIRED, NEVER ALLOW
    trace_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run_id}/decision-trace",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert trace_res.status_code == 200
    trace_json = trace_res.json()
    assert trace_json["run_status"] == "WAITING_FOR_APPROVAL"
    assert trace_json["final_gate_decision"] == "REVIEW_REQUIRED"
    assert trace_json["final_decision"] == "REVIEW_REQUIRED"
    assert trace_json["final_gate_decision"] != "ALLOW"


@pytest.mark.asyncio
async def test_approval_request_cannot_authorize_action_contradicting_user_intent(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Assert that an approval request cannot authorize an action that contradicts the original user intent.
    Even if an approval request is somehow created or presented for a search-only run,
    approving it must fail closed with HTTP 403, preventing any unauthorized purchase.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    user_id = ctx["user_id"]

    exact_user_request = (
        "Find me a laptop under ₹20,000. Only search and show me matching products. "
        "Do not add anything to the cart, create an order, or make a payment."
    )

    # 1. Create run with search-only user request
    run = await AgentRuntimeService.create_run(
        db=db_session,
        workspace_id=ws_id,
        agent_id=agent_id,
        input_text=exact_user_request,
        authority_id=auth_id
    )

    from app.models.gate import GateDecision, ApprovalRequest, ApprovalStatus
    from app.services.approval_service import ApprovalService

    # 2. Simulate an agent action and approval request linked to this search-only run
    act = AgentAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        run_id=run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"order_id": "dummy_order"},
        status=ActionStatus.PENDING_APPROVAL
    )
    db_session.add(act)
    await db_session.flush()

    dummy_decision = GateDecision(
        id=f"gdec_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=run.id,
        agent_action_id=act.id,
        intent_id=run.intent_id,
        authority_id=auth_id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        explanation="Simulated threshold review",
        required_approval=True,
        evaluation_snapshot={"simulated": True}
    )
    db_session.add(dummy_decision)
    await db_session.flush()

    appr = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=run.id,
        agent_action_id=act.id,
        gate_decision_id=dummy_decision.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING,
        amount=18990.0,
        currency="INR",
        transaction_data={"amount": 18990.0, "currency": "INR"}
    )
    db_session.add(appr)
    await db_session.commit()

    # 3. Assert that attempting to approve this request fails closed with HTTP 403
    approval_service = ApprovalService(db_session)
    with pytest.raises(HTTPException) as exc_appr:
        await approval_service.approve(
            approval_id=appr.id,
            workspace_id=ws_id,
            user_id=user_id
        )
    assert exc_appr.value.status_code == 403
    assert "search-only" in exc_appr.value.detail.lower()

    # Verify that the approval request remains PENDING
    await db_session.refresh(appr)
    assert appr.status == ApprovalStatus.PENDING
    assert appr.approved_by is None


@pytest.mark.asyncio
async def test_explicitly_authorized_purchase_completes_normally_through_gate(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Assert that a legitimate, explicitly authorized purchase request:
    1. Executes search_products, create_cart, add_to_cart, checkout, and pay_order through the normal gate.
    2. Passes the Action Gate with ALLOW when within authority monetary and approval thresholds.
    3. Successfully captures payment and transitions order to PAID.
    4. Accurately decrements product inventory by 1.
    5. Leaves run status as COMPLETED with authoritative_decision = 'ALLOW'.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    auth_id = ctx["authority"].id
    prod_cheap_id = ctx["product_cheap"].id

    # Check starting inventory
    prod_before = await db_session.get(Product, prod_cheap_id)
    initial_inventory = prod_before.inventory

    # 1. Create run for explicit purchase within threshold (auth limit 100k, threshold 50k, item price 18990)
    purchase_request = "Purchase 1 Budget Chromebook Laptop for our office."
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": purchase_request,
            "authority_id": auth_id,
            "auto_start": False
        },
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # 2. Execute search -> create_cart -> add_to_cart -> checkout -> pay_order
    s_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "search_products", "input": {"query": "Chromebook"}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert s_res.status_code == 200

    c_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "create_cart", "input": {}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert c_res.status_code == 200
    cart_id = c_res.json()["output"]["cart_id"]

    a_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_cheap_id, "quantity": 1}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert a_res.status_code == 200

    co_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert co_res.status_code == 200
    order_id = co_res.json()["output"]["order_id"]

    # Verify order is initially PENDING_PAYMENT
    order_obj = await db_session.get(Order, order_id)
    assert order_obj.status.value == "PENDING_PAYMENT"

    # 3. Pay order: should be directly ALLOWED (18,990 <= 50,000 threshold)
    pay_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert pay_res.status_code == 200
    pay_action_data = pay_res.json()
    assert pay_action_data["status"] == "SUCCESS"
    assert pay_action_data["output"]["status"] == "PAID"

    # Finish run
    finish_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/finish",
        json={"output": "Order placed and paid successfully.", "status": "COMPLETED"},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert finish_res.status_code == 200

    # 4. Assert order transitioned to PAID
    await db_session.refresh(order_obj)
    assert order_obj.status.value == "PAID"

    # 5. Assert product inventory decremented by exactly 1
    await db_session.refresh(prod_before)
    assert prod_before.inventory == initial_inventory - 1

    # 6. Assert API returns authoritative ALLOW
    get_run_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run_id}",
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert get_run_res.status_code == 200
    run_detail = get_run_res.json()
    assert run_detail["status"] == "COMPLETED"
    assert run_detail["authoritative_decision"] == "ALLOW"


@pytest.mark.asyncio
async def test_review_required_purchase_and_resume_prevents_duplicate_side_effects(
    client: AsyncClient,
    db_session: AsyncSession,
    search_only_test_context
):
    """
    REGRESSION TEST:
    Assert that a purchase exceeding approval threshold:
    1. Pauses with REVIEW_REQUIRED and action PENDING_APPROVAL.
    2. Leaves order in PENDING_PAYMENT (cannot be mistaken for paid).
    3. Does not decrement inventory multiple times.
    4. Upon approval and resume, executes payment, transitions order to PAID, and consumes approval.
    5. A second resume call is idempotent and does not create duplicate payments or decrement inventory.
    """
    ctx = search_only_test_context
    ws_id = ctx["ws_id"]
    agent_id = ctx["agent"].id
    prod_expensive_id = ctx["product_expensive"].id
    user_id = ctx["user_id"]

    # Starting inventory for expensive product
    prod_exp = await db_session.get(Product, prod_expensive_id)
    initial_exp_inventory = prod_exp.inventory

    # 1. Authority with low approval threshold to trigger REVIEW_REQUIRED
    low_thresh_auth = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        agent_id=agent_id,
        status=AuthorityStatus.ACTIVE,
        monetary_limit=100000.0,
        approval_threshold=1000.0, # 75,000 INR price > 1,000 threshold
        currency="INR",
        allowed_capabilities=[
            "SEARCH_PRODUCTS", "CREATE_CART", "ADD_CART_ITEM",
            "MANAGE_CART", "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        ],
        version=1
    )
    db_session.add(low_thresh_auth)
    await db_session.commit()

    # 2. Create purchase run
    run_res = await client.post(
        "/api/v1/agent-runtime/runs",
        json={
            "agent_id": agent_id,
            "input": "Purchase the Pro Gaming Laptop for 75000 INR.",
            "authority_id": low_thresh_auth.id,
            "auto_start": False
        },
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert run_res.status_code == 200
    run_id = run_res.json()["id"]

    # 3. Search -> Cart -> Add -> Checkout
    await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "search_products", "input": {"query": "Gaming"}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    c_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "create_cart", "input": {}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    cart_id = c_res.json()["output"]["cart_id"]

    await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_expensive_id, "quantity": 1}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    co_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "checkout", "input": {"cart_id": cart_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert co_res.status_code == 200
    order_id = co_res.json()["output"]["order_id"]

    # Check order is PENDING_PAYMENT
    order_obj = await db_session.get(Order, order_id)
    assert order_obj.status.value == "PENDING_PAYMENT"

    # Inventory was decremented once at checkout
    await db_session.refresh(prod_exp)
    assert prod_exp.inventory == initial_exp_inventory - 1
    inventory_after_checkout = prod_exp.inventory

    # 4. Propose pay_order (must require review)
    pay_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": "pay_order", "input": {"order_id": order_id}},
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert pay_res.status_code in [200, 402]

    # Find the pending approval request
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.services.approval_service import ApprovalService
    stmt_appr = select(ApprovalRequest).where(
        ApprovalRequest.agent_run_id == run_id,
        ApprovalRequest.status == ApprovalStatus.PENDING
    )
    res_appr = await db_session.execute(stmt_appr)
    approval_req = res_appr.scalars().first()
    assert approval_req is not None
    assert approval_req.amount == 75000.0

    # Assert run displays REVIEW_REQUIRED (NEVER ALLOW)
    get_run_res = await client.get(
        f"/api/v1/agent-runtime/runs/{run_id}",
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    run_detail = get_run_res.json()
    assert run_detail["status"] == "WAITING_FOR_APPROVAL"
    assert run_detail["authoritative_decision"] == "REVIEW_REQUIRED"
    assert run_detail["authoritative_decision"] != "ALLOW"

    # Assert order is still NOT paid
    await db_session.refresh(order_obj)
    assert order_obj.status.value == "PENDING_PAYMENT"

    # 5. Approve the approval request legitimately
    appr_service = ApprovalService(db_session)
    dec = await appr_service.approve(
        approval_id=approval_req.id,
        workspace_id=ws_id,
        user_id=user_id
    )
    assert dec.decision.value == "ALLOW"
    await db_session.refresh(approval_req)
    assert approval_req.status == ApprovalStatus.APPROVED

    # 6. Resume the run via POST /runs/{run_id}/resume
    resume_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/resume",
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert resume_res.status_code == 200
    resumed_run = resume_res.json()
    assert resumed_run["status"] == "COMPLETED"

    # Verify order is now PAID
    await db_session.refresh(order_obj)
    assert order_obj.status.value == "PAID"

    # Verify approval is CONSUMED
    await db_session.refresh(approval_req)
    assert approval_req.status == ApprovalStatus.CONSUMED

    # Verify inventory was NOT decremented a second time
    await db_session.refresh(prod_exp)
    assert prod_exp.inventory == inventory_after_checkout

    # 7. Test Idempotency: call resume a second time
    resume_second_res = await client.post(
        f"/api/v1/agent-runtime/runs/{run_id}/resume",
        cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert resume_second_res.status_code == 200
    second_res_run = resume_second_res.json()
    assert second_res_run["status"] == "COMPLETED"

    # Verify inventory is STILL unchanged
    await db_session.refresh(prod_exp)
    assert prod_exp.inventory == inventory_after_checkout



