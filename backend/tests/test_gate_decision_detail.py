import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.gate import GateDecision, ApprovalRequest, DecisionResult, ApprovalStatus
from app.models.agent import Agent, AgentStatus, AgentType
from app.models.agent_runtime import AgentRun, AgentAction, RunStatus, ActionStatus
from app.models.intent import Intent, IntentStatus, IntentType
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.risk import RiskAssessment, RiskAssessmentType, RiskLevel, RiskAssessmentStatus
from app.models.commerce import Order, OrderItem, OrderStatus, Merchant
from app.models.payment import Payment, PaymentStatus


@pytest.fixture
async def ws_context_a(client: AsyncClient):
    email = f"ws_a_{uuid.uuid4().hex[:8]}@finshield.com"
    res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Workspace A Admin"
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


@pytest.fixture
async def ws_context_b(client: AsyncClient):
    email = f"ws_b_{uuid.uuid4().hex[:8]}@finshield.com"
    res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Workspace B Admin"
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
async def test_get_gate_decision_valid_with_full_evidence(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    # 1. Setup entities
    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Procurement Bot",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["PAY_ORDER", "CHECKOUT"]
    )
    db_session.add(agent)

    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        status=IntentStatus.ACTIVE,
        intent_type=IntentType.PURCHASE,
        title="Procure Office Supplies",
        natural_language_request="Purchase printer paper under INR 5000",
        version=1
    )
    db_session.add(intent)

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=AuthorityStatus.ACTIVE,
        allowed_capabilities=["PAY_ORDER"],
        monetary_limit=10000,
        currency="INR",
        approval_threshold=3000,
        version=1
    )
    db_session.add(authority)

    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        status=RunStatus.WAITING_FOR_APPROVAL,
        input="Procure printer supplies"
    )
    db_session.add(run)

    action = AgentAction(
        id=f"act_{uuid.uuid4().hex[:16]}",
        run_id=run.id,
        sequence_number=1,
        tool_name="pay_order",
        input={"order_id": "ord_mock123", "amount": 4500, "currency": "INR"},
        status=ActionStatus.PENDING_APPROVAL
    )
    db_session.add(action)

    ra = RiskAssessment(
        id=f"ra_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        assessment_type=RiskAssessmentType.PAYMENT,
        risk_score=72.5,
        risk_level=RiskLevel.MEDIUM,
        model_version="v1.0",
        scoring_version="v1.0",
        status=RiskAssessmentStatus.COMPLETED
    )
    db_session.add(ra)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        intent_id=intent.id,
        intent_version=1,
        authority_id=authority.id,
        authority_version=1,
        risk_assessment_id=ra.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["APPROVAL_THRESHOLD_EXCEEDED"],
        explanation="Payment amount ₹4,500 exceeds auto-approval threshold ₹3,000",
        required_approval=True,
        evaluation_snapshot={"policy": {"decision": "REVIEW"}, "order_id": "ord_mock123"}
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
        reason="Exceeds authority threshold",
        amount=4500,
        currency="INR",
        transaction_data={"order_id": "ord_mock123"}
    )
    db_session.add(appr)

    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        name="Office Supplies Co"
    )
    db_session.add(merchant)

    order = Order(
        id="ord_mock123",
        workspace_id=ws_id,
        agent_id=agent.id,
        merchant_id=merchant.id,
        status=OrderStatus.PENDING_PAYMENT,
        currency="INR",
        subtotal=4500,
        total=4500
    )
    db_session.add(order)

    payment = Payment(
        id=f"pay_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        order_id="ord_mock123",
        payment_intent_id="pi_mock123",
        idempotency_key="ik_mock123",
        amount=4500,
        currency="INR",
        status=PaymentStatus.REQUIRES_AUTHORIZATION,
        metadata_={"finshield": {"gate_decision_id": gd.id, "run_id": run.id, "action_id": action.id}}
    )
    db_session.add(payment)

    await db_session.commit()

    # 2. Test GET /gate-decisions/{id}
    res = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["id"] == gd.id
    assert body["decision"] == "REVIEW"
    assert body["required_approval"] is True
    assert body["amount"] == 4500.0
    assert body["currency"] == "INR"
    assert "APPROVAL_THRESHOLD_EXCEEDED" in body["reason_codes"]

    # Check evidence models
    assert body["agent"]["name"] == "Procurement Bot"
    assert body["agent_run"]["id"] == run.id
    assert body["agent_action"]["tool_name"] == "pay_order"
    assert body["intent"]["id"] == intent.id
    assert body["authority"]["id"] == authority.id
    assert body["risk_assessment"]["id"] == ra.id
    assert body["approval"]["id"] == appr.id
    assert body["approval"]["status"] == "PENDING"
    assert body["order"]["id"] == "ord_mock123"
    assert body["payment"]["id"] == payment.id

    # Check evidence statuses
    assert body["evidence_status"]["agent"] == "AVAILABLE"
    assert body["evidence_status"]["agent_run"] == "AVAILABLE"
    assert body["evidence_status"]["agent_action"] == "AVAILABLE"
    assert body["evidence_status"]["intent"] == "AVAILABLE"
    assert body["evidence_status"]["authority"] == "AVAILABLE"
    assert body["evidence_status"]["risk_assessment"] == "AVAILABLE"
    assert body["evidence_status"]["approval"] == "AVAILABLE"
    assert body["evidence_status"]["order"] == "AVAILABLE"
    assert body["evidence_status"]["payment"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_get_gate_decision_by_approval_id(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Runner Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="test")
    db_session.add(run)

    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="pay_order")
    db_session.add(action)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["MANUAL_CONFIRMATION"],
        required_approval=True,
        evaluation_snapshot={}
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
        amount=1200,
        currency="INR"
    )
    db_session.add(appr)
    await db_session.commit()

    # Query using the approval ID directly
    res = await client.get(
        f"/api/v1/gate-decisions/{appr.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == gd.id
    assert body["approval"]["id"] == appr.id
    assert body["decision"] == "REVIEW"


@pytest.mark.asyncio
async def test_gate_decision_not_found_404(
    client: AsyncClient,
    ws_context_a
):
    ctx = ws_context_a
    fake_id = f"gdec_{uuid.uuid4().hex}"
    res = await client.get(
        f"/api/v1/gate-decisions/{fake_id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 404
    assert "not found" in res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_gate_decision_workspace_isolation_403(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a,
    ws_context_b
):
    ctx_a = ws_context_a
    ctx_b = ws_context_b

    # Create GateDecision in Workspace A
    agent_a = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ctx_a["ws_id"],
        name="Private Agent A",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent_a)

    run_a = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ctx_a["ws_id"], agent_id=agent_a.id, input="secret run")
    db_session.add(run_a)

    action_a = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run_a.id, sequence_number=1, tool_name="secret_tool")
    db_session.add(action_a)

    gd_a = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ctx_a["ws_id"],
        agent_id=agent_a.id,
        agent_run_id=run_a.id,
        agent_action_id=action_a.id,
        decision=DecisionResult.BLOCK,
        reason_codes=["CONFIDENTIAL"],
        evaluation_snapshot={}
    )
    db_session.add(gd_a)

    appr_a = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ctx_a["ws_id"],
        agent_id=agent_a.id,
        agent_run_id=run_a.id,
        agent_action_id=action_a.id,
        gate_decision_id=gd_a.id,
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.PENDING
    )
    db_session.add(appr_a)
    await db_session.commit()

    # User from Workspace B tries to access Workspace A's gate decision by GateDecision ID
    res1 = await client.get(
        f"/api/v1/gate-decisions/{gd_a.id}",
        cookies=ctx_b["cookies"],
        headers=ctx_b["headers"]
    )
    assert res1.status_code == 403, f"Expected 403 Forbidden, got {res1.status_code}: {res1.text}"
    assert "another workspace" in res1.json()["error"]["message"].lower()

    # User from Workspace B tries to access Workspace A's gate decision by Approval ID
    res2 = await client.get(
        f"/api/v1/gate-decisions/{appr_a.id}",
        cookies=ctx_b["cookies"],
        headers=ctx_b["headers"]
    )
    assert res2.status_code == 403, f"Expected 403 Forbidden, got {res2.status_code}: {res2.text}"
    assert "another workspace" in res2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_gate_decision_unconfigured_and_failed_evidence_distinction(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Unconfigured Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="search only")
    db_session.add(run)

    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="create_cart")
    db_session.add(action)

    # BLOCK decision because action was prohibited by intent, with no authority or payment linked
    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        intent_id=None,
        authority_id=None,
        risk_assessment_id=None,
        decision=DecisionResult.BLOCK,
        reason_codes=["INTENT_PROHIBITED_ACTION"],
        explanation="Action create_cart was prohibited by user request",
        required_approval=False,
        evaluation_snapshot={}
    )
    db_session.add(gd)
    await db_session.commit()

    res = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["decision"] == "BLOCK"
    assert body["required_approval"] is False
    assert body["approval"] is None
    assert body["order"] is None
    assert body["payment"] is None

    # Distinguish NOT_CONFIGURED from AVAILABLE or CHECK_FAILED
    assert body["evidence_status"]["intent"] == "NOT_CONFIGURED"
    assert body["evidence_status"]["authority"] == "NOT_CONFIGURED"
    assert body["evidence_status"]["risk_assessment"] == "NOT_CONFIGURED"
    assert body["evidence_status"]["approval"] == "NOT_REQUIRED"
    assert body["evidence_status"]["order"] == "NONE_LINKED"
    assert body["evidence_status"]["payment"] == "NONE_LINKED"


@pytest.mark.asyncio
async def test_list_gate_decisions(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Listing Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="list test")
    db_session.add(run)

    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="search_products")
    db_session.add(action)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.ALLOW,
        reason_codes=["POLICY_PASS"],
        explanation="Search allowed",
        required_approval=False,
        evaluation_snapshot={}
    )
    db_session.add(gd)
    await db_session.commit()

    res = await client.get(
        "/api/v1/gate-decisions",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 200, res.text
    items = res.json()
    assert isinstance(items, list)
    matching = [it for it in items if it["id"] == gd.id]
    assert len(matching) == 1
    assert matching[0]["decision"] == "ALLOW"
    assert matching[0]["agent_name"] == "Listing Agent"
    assert matching[0]["tool_name"] == "search_products"


@pytest.mark.asyncio
async def test_pending_approval_can_be_rejected_and_subsequent_decision_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """Proves that a pending approval can be rejected, and once rejected, terminal decision cannot be acted on."""
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Action Test Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="pending test")
    db_session.add(run)

    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="place_order")
    db_session.add(action)

    gd = GateDecision(
        id=f"gdec_{uuid.uuid4().hex}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        decision=DecisionResult.REVIEW,
        reason_codes=["MANUAL_REVIEW_REQUIRED"],
        explanation="High-value transaction requires approval",
        required_approval=True,
        evaluation_snapshot={}
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
        reason="Manual review required",
        amount=1500,
        currency="USD"
    )
    db_session.add(appr)
    await db_session.commit()

    # 1. Fetch gate decision detail -> shows status PENDING
    res = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res.status_code == 200
    assert res.json()["approval"]["status"] == "PENDING"

    # 2. Reject the pending approval
    reject_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "REJECTED", "reason": "Disallowed by manager"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert reject_res.status_code == 200, reject_res.text
    reject_data = reject_res.json()
    assert reject_data["status"] == "REJECTED"
    assert reject_data["decision"] == "REJECTED"

    # 3. Fetch gate decision again -> reflects REJECTED terminal state
    res_after = await client.get(
        f"/api/v1/gate-decisions/{gd.id}",
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res_after.status_code == 200
    assert res_after.json()["approval"]["status"] == "REJECTED"

    # 4. Attempt to act on the rejected approval again -> must fail with HTTP 400
    duplicate_res = await client.post(
        f"/api/v1/approvals/{appr.id}/decision",
        json={"decision": "APPROVED"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert duplicate_res.status_code == 400
    err_msg = duplicate_res.json()["error"]["message"]
    assert "already REJECTED" in err_msg


@pytest.mark.asyncio
async def test_terminal_consumed_and_expired_approvals_cannot_be_acted_on(
    client: AsyncClient,
    db_session: AsyncSession,
    ws_context_a
):
    """Proves that decisions in terminal states (CONSUMED, EXPIRED, CANCELLED) cannot be acted on."""
    ctx = ws_context_a
    ws_id = ctx["ws_id"]

    agent = Agent(
        id=f"agent_{uuid.uuid4().hex[:12]}",
        workspace_id=ws_id,
        name="Terminal States Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)

    run = AgentRun(id=f"run_{uuid.uuid4().hex[:16]}", workspace_id=ws_id, agent_id=agent.id, input="terminal test")
    db_session.add(run)

    action = AgentAction(id=f"act_{uuid.uuid4().hex[:16]}", run_id=run.id, sequence_number=1, tool_name="finalize_checkout")
    db_session.add(action)

    # 1. Consumed Approval
    appr_consumed = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=f"gdec_{uuid.uuid4().hex}",
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.CONSUMED,
        reason="Already processed",
        amount=200,
        currency="USD"
    )
    db_session.add(appr_consumed)

    # 2. Expired Approval
    appr_expired = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=f"gdec_{uuid.uuid4().hex}",
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.EXPIRED,
        reason="Timed out",
        amount=300,
        currency="USD"
    )
    db_session.add(appr_expired)

    # 3. Cancelled Approval
    appr_cancelled = ApprovalRequest(
        id=f"appr_{uuid.uuid4().hex[:16]}",
        workspace_id=ws_id,
        agent_id=agent.id,
        agent_run_id=run.id,
        agent_action_id=action.id,
        gate_decision_id=f"gdec_{uuid.uuid4().hex}",
        requested_by="SYSTEM_GATE",
        status=ApprovalStatus.CANCELLED,
        reason="Run cancelled",
        amount=400,
        currency="USD"
    )
    db_session.add(appr_cancelled)

    await db_session.commit()

    # Attempt to decide on CONSUMED
    res1 = await client.post(
        f"/api/v1/approvals/{appr_consumed.id}/decision",
        json={"decision": "APPROVED"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res1.status_code == 400
    assert "already CONSUMED" in res1.json()["error"]["message"]

    # Attempt to decide on EXPIRED
    res2 = await client.post(
        f"/api/v1/approvals/{appr_expired.id}/decision",
        json={"decision": "REJECTED"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res2.status_code == 400
    assert "already EXPIRED" in res2.json()["error"]["message"]

    # Attempt to decide on CANCELLED
    res3 = await client.post(
        f"/api/v1/approvals/{appr_cancelled.id}/decision",
        json={"decision": "APPROVED"},
        cookies=ctx["cookies"],
        headers=ctx["headers"]
    )
    assert res3.status_code == 400
    assert "already CANCELLED" in res3.json()["error"]["message"]

