import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.action_gate_service import ActionGateService
from app.models.gate import DecisionResult
from app.services.investigation_service import InvestigationService
from app.schemas.investigation import InvestigationResolution, InvestigationCreate
from app.models.investigation import ResolutionType, InvestigationPriority, InvestigationType
from app.services.payment_service import log_payment_activity
from app.services.commerce_service import CommerceService

@pytest.fixture
async def audit_test_context(client: AsyncClient, db_session: AsyncSession):
    email = f"audit_tester_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Audit Tester"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    headers = {"X-Workspace-ID": ws_id}
    
    return {
        "cookies": cookies,
        "headers": headers,
        "ws_id": ws_id,
        "user_id": user_id,
        "email": email
    }

@pytest.mark.asyncio
async def test_audit_log_end_to_end_real_transactions_and_actions(
    client: AsyncClient,
    db_session: AsyncSession,
    audit_test_context
):
    ctx = audit_test_context
    ws_id = ctx["ws_id"]
    user_id = ctx["user_id"]
    
    # 1. Create an agent
    agent_res = await client.post("/api/v1/agents", json={
        "name": "Audit Shopping Agent",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "CREATE_ORDER", "PAY_ORDER"]
    }, cookies=ctx["cookies"], headers=ctx["headers"])
    assert agent_res.status_code in [200, 201], agent_res.text
    agent_id = agent_res.json()["id"]

    # 2. Trigger real Action Gate decision with BLOCK
    from app.models.agent import Agent, AgentStatus
    agent = await db_session.get(Agent, agent_id)
    agent.status = AgentStatus.PAUSED
    await db_session.commit()

    gate_service = ActionGateService(db_session)
    block_decision = await gate_service.evaluate(
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_run_id=f"run_{uuid.uuid4().hex[:8]}",
        agent_action_id=f"act_{uuid.uuid4().hex[:8]}",
        action_type="PAY_ORDER",
        transaction={"amount": 99999, "currency": "INR"}
    )
    await db_session.commit()
    assert block_decision.decision == DecisionResult.BLOCK

    # 3. Simulate payment activity logging (CAPTURE and AUTHORIZE)
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    await log_payment_activity(
        db=db_session,
        payment_id=payment_id,
        workspace_id=ws_id,
        action="CAPTURED",
        actor_id=agent_id,
        agent_id=agent_id,
        actor_type=ActorType.AGENT,
        details={"amount": 150.0, "currency": "INR"}
    )
    await db_session.commit()

    # 4. Simulate order activity logging
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    await CommerceService._log_activity(
        db=db_session,
        workspace_id=ws_id,
        action="ORDER_CREATED",
        order_id=order_id,
        actor_id=agent_id,
        agent_id=agent_id,
        actor_type=ActorType.AGENT,
        details={"total": 150.0, "currency": "INR"}
    )
    await db_session.commit()

    # 5. Create and resolve an investigation
    inv_service = InvestigationService(db_session)
    inv = await inv_service.create_investigation(
        inv_in=InvestigationCreate(
            title="Suspicious High Value Activity",
            description="Agent attempted transaction of 99999 INR",
            type=InvestigationType.POLICY_VIOLATION,
            priority=InvestigationPriority.HIGH,
            source_type="AGENT",
            source_id=agent_id
        ),
        workspace_id=ws_id,
        created_by=user_id
    )
    
    await inv_service.resolve_investigation(
        investigation_id=inv.id,
        workspace_id=ws_id,
        resolution_in=InvestigationResolution(
            resolution=ResolutionType.CONFIRMED_THREAT,
            resolution_reason="Confirmed abnormal transaction attempt"
        ),
        actor_id=user_id
    )

    # 6. Retrieve events via standard endpoint /api/v1/audit/
    res_direct = await client.get("/api/v1/audit/", cookies=ctx["cookies"], headers=ctx["headers"])
    assert res_direct.status_code == 200, res_direct.text
    events_direct = res_direct.json()
    assert isinstance(events_direct, list)
    assert len(events_direct) >= 5

    # 7. Retrieve events via workspace-scoped endpoint /api/v1/workspaces/{workspace_id}/audit/
    res_scoped = await client.get(f"/api/v1/workspaces/{ws_id}/audit/", cookies=ctx["cookies"], headers=ctx["headers"])
    assert res_scoped.status_code == 200, res_scoped.text
    events_scoped = res_scoped.json()
    assert isinstance(events_scoped, list)
    assert len(events_scoped) == len(events_direct)

    # 8. Verify specific critical actions emitted durable, workspace-scoped audit events
    event_types = [e["event_type"] for e in events_direct]
    assert "CAPTURED" in event_types
    assert "ORDER_CREATED" in event_types
    assert "INVESTIGATION_RESOLVED" in event_types
    assert any("GATE_DECISION" in et for et in event_types)

    # Verify agent context is preserved on agent actions
    captured_evt = next(e for e in events_direct if e["event_type"] == "CAPTURED")
    assert captured_evt["entity_type"] == "PAYMENT"
    assert captured_evt["entity_id"] == payment_id
    assert captured_evt["agent_id"] == agent_id
    assert captured_evt["actor_type"] == "AGENT"
    assert captured_evt["workspace_id"] == ws_id

    # 9. Verify Cryptographic Integrity Chain is INTACT
    verify_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res.status_code == 200
    integrity_data = verify_res.json()
    assert integrity_data["valid"] is True
    assert integrity_data["checked_events"] >= 5
    assert len(integrity_data["broken_links"]) == 0

    # GET alias for integrity check also works
    verify_get = await client.get("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_get.status_code == 200
    assert verify_get.json()["valid"] is True

@pytest.mark.asyncio
async def test_audit_integrity_tampering_detection(
    client: AsyncClient,
    db_session: AsyncSession,
    audit_test_context
):
    ctx = audit_test_context
    ws_id = ctx["ws_id"]

    # Log 3 events
    for i in range(3):
        await log_payment_activity(
            db=db_session,
            payment_id=f"pay_seq_{i}",
            workspace_id=ws_id,
            action="CAPTURED",
            actor_id=ctx["user_id"],
            details={"step": i}
        )
    await db_session.commit()

    # Verify chain is intact first
    verify_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True

    # Mutate a payload in the database to simulate tampering
    res_audit = await client.get("/api/v1/audit/", cookies=ctx["cookies"], headers=ctx["headers"])
    target_event = res_audit.json()[1]
    
    await db_session.execute(text(
        f"UPDATE audit_events SET payload = '{{\"tampered\": true}}' WHERE id = '{target_event['id']}'"
    ))
    await db_session.commit()

    # Verify that integrity check detects the tampering
    tampered_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert tampered_res.status_code == 200
    data = tampered_res.json()
    assert data["valid"] is False
    assert any(b["event_id"] == target_event["id"] for b in data["broken_links"])

@pytest.mark.asyncio
async def test_audit_workspace_isolation_and_empty_filters(
    client: AsyncClient,
    db_session: AsyncSession
):
    # Create Workspace A
    email_a = f"tenant_a_{uuid.uuid4().hex[:8]}@finshield.com"
    res_a = await client.post("/api/v1/auth/signup", json={
        "email": email_a, "password": "Password123!", "full_name": "Tenant A"
    })
    assert res_a.status_code in [200, 201]
    cookies_a = res_a.cookies
    ws_a = res_a.json()["workspace"]["id"]
    headers_a = {"X-Workspace-ID": ws_a}

    # Create Workspace B
    email_b = f"tenant_b_{uuid.uuid4().hex[:8]}@finshield.com"
    res_b = await client.post("/api/v1/auth/signup", json={
        "email": email_b, "password": "Password123!", "full_name": "Tenant B"
    })
    assert res_b.status_code in [200, 201]
    cookies_b = res_b.cookies
    ws_b = res_b.json()["workspace"]["id"]
    headers_b = {"X-Workspace-ID": ws_b}

    # Initially, workspace A has only signup/auth events
    res_a_init = await client.get("/api/v1/audit/", cookies=cookies_a, headers=headers_a)
    init_events_a = res_a_init.json()
    
    # Emit an event in Workspace A
    await log_payment_activity(
        db=db_session,
        payment_id=f"pay_ws_a_{uuid.uuid4().hex[:6]}",
        workspace_id=ws_a,
        action="CAPTURED",
        actor_id=res_a.json()["user"]["id"],
        details={"tenant": "A"}
    )
    await db_session.commit()

    # Emit an event in Workspace B
    await log_payment_activity(
        db=db_session,
        payment_id=f"pay_ws_b_{uuid.uuid4().hex[:6]}",
        workspace_id=ws_b,
        action="AUTHORIZED",
        actor_id=res_b.json()["user"]["id"],
        details={"tenant": "B"}
    )
    await db_session.commit()

    # Verify Workspace A only sees Workspace A events
    events_a = (await client.get("/api/v1/audit/", cookies=cookies_a, headers=headers_a)).json()
    assert all(e["workspace_id"] == ws_a for e in events_a)
    assert any((e.get("payload") or {}).get("tenant") == "A" for e in events_a)
    assert not any((e.get("payload") or {}).get("tenant") == "B" for e in events_a)

    # Verify Workspace B only sees Workspace B events
    events_b = (await client.get("/api/v1/audit/", cookies=cookies_b, headers=headers_b)).json()
    assert all(e["workspace_id"] == ws_b for e in events_b)
    assert any((e.get("payload") or {}).get("tenant") == "B" for e in events_b)
    assert not any((e.get("payload") or {}).get("tenant") == "A" for e in events_b)


    # Verify empty results when filter genuinely does not match
    no_match_res = await client.get("/api/v1/audit/?category=INVESTIGATION", cookies=cookies_a, headers=headers_a)
    assert no_match_res.status_code == 200
    assert no_match_res.json() == []

    entity_no_match = await client.get("/api/v1/audit/?entity_type=NONEXISTENT_ENTITY", cookies=cookies_a, headers=headers_a)
    assert entity_no_match.status_code == 200
    assert entity_no_match.json() == []


@pytest.mark.asyncio
async def test_integrity_distinguishes_chain_validity_from_completeness(
    client: AsyncClient,
    db_session: AsyncSession
):
    from app.services.audit_service import AuditService
    from app.models.payment import Payment, PaymentStatus
    audit_svc = AuditService(db_session)

    # 1. Test empty workspace with no records: chain is EMPTY, completeness is NO_EVENTS
    empty_ws_id = f"wksp_empty_{uuid.uuid4().hex[:8]}"
    empty_res = await audit_svc.verify_integrity(empty_ws_id)
    assert empty_res["checked_events"] == 0
    assert empty_res["chain_status"] == "EMPTY"
    assert empty_res["completeness_status"] == "NO_EVENTS"

    # 2. Test broken ingestion: workspace has a payment record in database, but 0 audit events
    broken_ws_id = f"wksp_broken_{uuid.uuid4().hex[:8]}"
    dummy_payment = Payment(
        id=f"pay_{uuid.uuid4().hex[:8]}",
        workspace_id=broken_ws_id,
        payment_intent_id=f"pi_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        amount=500,
        currency="INR",
        status=PaymentStatus.CAPTURED
    )
    db_session.add(dummy_payment)
    await db_session.commit()

    broken_res = await audit_svc.verify_integrity(broken_ws_id)
    assert broken_res["checked_events"] == 0
    assert broken_res["valid"] is False  # Cannot certify as valid when ingestion is broken
    assert broken_res["chain_status"] == "EMPTY"
    assert broken_res["completeness_status"] == "INCOMPLETE_INGESTION"
    assert "active records" in broken_res["completeness_note"]

    # 3. Test workspace with real events: available chain is valid, but completeness is CHAIN_VALID_ONLY
    valid_ws_id = f"wksp_valid_{uuid.uuid4().hex[:8]}"
    await log_payment_activity(
        db=db_session,
        payment_id=f"pay_{uuid.uuid4().hex[:8]}",
        workspace_id=valid_ws_id,
        action="CAPTURED",
        actor_id="test_actor",
        details={"amount": 100}
    )
    await db_session.commit()

    valid_res = await audit_svc.verify_integrity(valid_ws_id)
    assert valid_res["checked_events"] == 1
    assert valid_res["valid"] is True
    assert valid_res["chain_status"] == "VALID"
    assert valid_res["completeness_status"] == "CHAIN_VALID_ONLY"
    assert "not guarantee completeness" in valid_res["completeness_note"]


@pytest.mark.asyncio
async def test_audit_integrity_detects_missing_sequence_numbers(
    client: AsyncClient,
    db_session: AsyncSession,
    audit_test_context
):
    """
    Direct regression test for sequence gaps:
    When an event sequence is omitted or deleted (such as the deleted #205 event),
    the integrity verifier must flag both the sequence gap and the previous-hash mismatch.
    """
    from app.services.audit_service import AuditService
    audit_svc = AuditService(db_session)
    ws_id = f"wksp_seq_gap_{uuid.uuid4().hex[:8]}"

    # Emit 3 events in sequence
    e1 = await audit_svc.record_event(
        workspace_id=ws_id,
        event_type="PAYMENT_CAPTURED",
        event_category=EventCategory.PAYMENT,
        severity=EventSeverity.INFO,
        actor_id="actor_1",
        actor_type=ActorType.USER,
        payload={"amount": 100}
    )
    e2 = await audit_svc.record_event(
        workspace_id=ws_id,
        event_type="APPROVAL_APPROVED",
        event_category=EventCategory.APPROVAL,
        severity=EventSeverity.INFO,
        actor_id="actor_1",
        actor_type=ActorType.USER,
        payload={"approved": True}
    )
    e3 = await audit_svc.record_event(
        workspace_id=ws_id,
        event_type="GATE_DECISION_ALLOW",
        event_category=EventCategory.GATE,
        severity=EventSeverity.INFO,
        actor_id="gate_engine",
        actor_type=ActorType.SYSTEM,
        payload={"decision": "ALLOW"}
    )
    await db_session.commit()

    # Pre-check: chain is valid with 3 events
    res_before = await audit_svc.verify_integrity(ws_id)
    assert res_before["valid"] is True
    assert res_before["checked_events"] == 3

    # Delete event 2 (sequence #2), leaving sequence #1 and #3
    await db_session.execute(text(f"DELETE FROM audit_events WHERE id = '{e2.id}'"))
    await db_session.commit()

    # Verification must fail and report SEQUENCE_GAP and PREVIOUS_HASH_MISMATCH
    res_after = await audit_svc.verify_integrity(ws_id)
    assert res_after["valid"] is False
    assert res_after["chain_status"] == "TAMPERED"
    assert len(res_after["broken_links"]) == 2
    
    gap_issue = next(b for b in res_after["broken_links"] if b["reason"] == "SEQUENCE_GAP")
    assert gap_issue["expected"] == 2
    assert gap_issue["actual"] == 3
    assert gap_issue["event_id"] == e3.id

    hash_issue = next(b for b in res_after["broken_links"] if b["reason"] == "PREVIOUS_HASH_MISMATCH")
    assert hash_issue["event_id"] == e3.id


@pytest.mark.asyncio
async def test_audit_integrity_detects_reordered_events(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Regression test for reordered/out-of-order events:
    If sequence numbers are swapped or out of order, verification must fail.
    """
    from app.services.audit_service import AuditService
    audit_svc = AuditService(db_session)
    ws_id = f"wksp_reorder_{uuid.uuid4().hex[:8]}"

    # Emit 2 events
    e1 = await audit_svc.record_event(
        workspace_id=ws_id,
        event_type="PAYMENT_CAPTURED",
        event_category=EventCategory.PAYMENT,
        severity=EventSeverity.INFO,
        actor_id="actor_1",
        actor_type=ActorType.USER,
        payload={"step": 1}
    )
    e2 = await audit_svc.record_event(
        workspace_id=ws_id,
        event_type="ORDER_CREATED",
        event_category=EventCategory.ORDER,
        severity=EventSeverity.INFO,
        actor_id="actor_1",
        actor_type=ActorType.USER,
        payload={"step": 2}
    )
    await db_session.commit()

    # Move sequence of e1 to 99 so that e2 (which expects e1 as antecedent) is evaluated first
    await db_session.execute(text(f"UPDATE audit_events SET workspace_sequence = 99 WHERE id = '{e1.id}'"))
    await db_session.commit()

    # Verification must detect broken integrity
    res = await audit_svc.verify_integrity(ws_id)
    assert res["valid"] is False
    assert res["chain_status"] == "TAMPERED"
    assert len(res["broken_links"]) > 0


@pytest.mark.asyncio
async def test_audit_pagination_and_full_chain_integrity(
    client: AsyncClient,
    db_session: AsyncSession,
    audit_test_context
):
    """
    Regression test for Requirement 4:
    Verifies that pagination (e.g. limit=5) returns partial windows for UI presentation,
    while audit integrity verification always inspects the complete chain of all events.
    """
    ctx = audit_test_context
    ws_id = ctx["ws_id"]

    # Emit 12 audit events
    for i in range(12):
        await log_payment_activity(
            db=db_session,
            payment_id=f"pay_page_{i}",
            workspace_id=ws_id,
            action="CAPTURED",
            actor_id=ctx["user_id"],
            details={"index": i}
        )
    await db_session.commit()

    # 1. Test pagination on /api/v1/audit/
    page1 = await client.get("/api/v1/audit/?limit=5&offset=0", cookies=ctx["cookies"], headers=ctx["headers"])
    assert page1.status_code == 200
    items_p1 = page1.json()
    assert len(items_p1) == 5

    page2 = await client.get("/api/v1/audit/?limit=5&offset=5", cookies=ctx["cookies"], headers=ctx["headers"])
    assert page2.status_code == 200
    items_p2 = page2.json()
    assert len(items_p2) == 5
    # Verify disjoint pages
    assert set(e["id"] for e in items_p1).isdisjoint(set(e["id"] for e in items_p2))

    # 2. Test that integrity verification checks ALL events in the workspace (12 + signup/auth events >= 12)
    verify_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is True
    assert data["checked_events"] >= 12
    assert len(data["broken_links"]) == 0
    assert data["chain_status"] == "VALID"


@pytest.mark.asyncio
async def test_audit_investigation_and_payment_lifecycle_recording(
    client: AsyncClient,
    db_session: AsyncSession,
    audit_test_context
):
    """
    Regression test for Task 3 & 5:
    Verifies that resolving investigations, status transitions, and recording payment
    lifecycle events (AUTHORIZATION_REQUESTED, AUTHORIZED, CAPTURED, ORDER_PAID)
    use the same audit-chain service, increment sequence numbers consistently,
    and produce a valid cryptographic chain.
    """
    ctx = audit_test_context
    ws_id = ctx["ws_id"]
    user_id = ctx["user_id"]
    
    # 1. Create an investigation
    inv_svc = InvestigationService(db_session)
    inv = await inv_svc.create_investigation(
        inv_in=InvestigationCreate(
            title="Suspicious Activity Investigation",
            description="Agent triggered high risk threshold",
            type=InvestigationType.POLICY_VIOLATION,
            priority=InvestigationPriority.HIGH,
            source_type="USER",
            source_id=user_id
        ),
        workspace_id=ws_id,
        created_by=user_id
    )
    await db_session.commit()

    # 2. Update investigation status to IN_REVIEW
    from app.models.investigation import InvestigationStatus
    await inv_svc.update_status(
        investigation_id=inv.id,
        workspace_id=ws_id,
        status=InvestigationStatus.IN_REVIEW,
        actor_id=user_id
    )

    # 3. Resolve the investigation
    await inv_svc.resolve_investigation(
        investigation_id=inv.id,
        workspace_id=ws_id,
        resolution_in=InvestigationResolution(
            resolution=ResolutionType.FALSE_POSITIVE,
            resolution_reason="Reviewed agent behavior and confirmed benign"
        ),
        actor_id=user_id
    )

    # 4. Record payment lifecycle events on the same workspace session
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    for lifecycle_action in ["AUTHORIZATION_REQUESTED", "AUTHORIZED", "CAPTURED", "ORDER_PAID"]:
        await log_payment_activity(
            db=db_session,
            payment_id=payment_id,
            workspace_id=ws_id,
            action=lifecycle_action,
            actor_id=user_id,
            details={"lifecycle_step": lifecycle_action}
        )
    await db_session.commit()

    # 5. Verify the complete workspace chain via API
    verify_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res.status_code == 200
    integrity = verify_res.json()
    assert integrity["valid"] is True
    assert integrity["chain_status"] == "VALID"
    assert len(integrity["broken_links"]) == 0
    assert integrity["checked_events"] >= 7


@pytest.mark.asyncio
async def test_audit_concurrent_writes_chain_integrity(
    db_session: AsyncSession
):
    """
    Regression test for Task 5:
    Verifies that concurrent record_event calls on the same workspace
    execute with serialized sequence allocation and produce a gapless,
    cryptographically unbroken hash chain.
    """
    import asyncio
    from app.services.audit_service import AuditService
    audit_svc = AuditService(db_session)
    ws_id = f"wksp_concurrent_{uuid.uuid4().hex[:8]}"

    # Concurrently emit 10 events
    async def emit_worker(index: int):
        return await audit_svc.record_event(
            workspace_id=ws_id,
            event_type=f"CONCURRENT_EVENT_{index}",
            event_category=EventCategory.SYSTEM,
            severity=EventSeverity.INFO,
            actor_id=f"worker_{index}",
            actor_type=ActorType.SYSTEM,
            payload={"worker_index": index}
        )

    tasks = [emit_worker(i) for i in range(10)]
    events = await asyncio.gather(*tasks)
    await db_session.commit()

    # Verify that all 10 events were recorded with distinct sequences 1 through 10
    sequences = sorted([e.workspace_sequence for e in events])
    assert sequences == list(range(1, 11))

    # Verify chain integrity
    res = await audit_svc.verify_integrity(ws_id)
    assert res["valid"] is True
    assert res["checked_events"] == 10
    assert res["chain_status"] == "VALID"
    assert len(res["broken_links"]) == 0



