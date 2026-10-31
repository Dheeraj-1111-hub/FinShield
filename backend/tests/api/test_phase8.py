"""
Integration tests for Intent and Authority APIs + Phase 8 runtime gate.
"""
import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.models.agent import Agent, AgentStatus, AgentType
from app.core.security import get_password_hash, generate_session_token, hash_session_token

pytestmark = pytest.mark.asyncio


# ─── Shared fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def owner_ctx(db_session: AsyncSession):
    """Returns (headers, workspace_id, user_id) for an owner."""
    user = User(
        id=f"usr_{uuid.uuid4().hex[:16]}",
        email=f"owner_{uuid.uuid4().hex[:8]}@test.com",
        full_name="Owner",
        password_hash=get_password_hash("pass"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    ws = Workspace(
        id=f"ws_{uuid.uuid4().hex[:16]}",
        name="Test WS",
        slug=f"test-ws-{uuid.uuid4().hex[:8]}",
        owner_id=user.id,
    )
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex[:16]}",
        workspace_id=ws.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)

    token = generate_session_token()
    session = Session(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(session)
    await db_session.commit()

    return {
        "headers": {"X-Workspace-ID": ws.id},
        "cookies": {"finshield_session": token},
        "workspace_id": ws.id,
        "user_id": user.id,
    }


@pytest_asyncio.fixture
async def active_agent(db_session: AsyncSession, owner_ctx):
    """Creates an ACTIVE agent with SEARCH_PRODUCTS + PAY_ORDER capabilities."""
    agent = Agent(
        id=f"agt_{uuid.uuid4().hex[:16]}",
        workspace_id=owner_ctx["workspace_id"],
        name="Test Agent",
        type=AgentType.SHOPPING,
        status=AgentStatus.ACTIVE,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER"],
        max_transaction_amount=100000,
        created_by=owner_ctx["user_id"],
    )
    db_session.add(agent)
    await db_session.commit()
    return agent


# ─── Intent CRUD tests ────────────────────────────────────────────────────────

async def test_create_intent(client: AsyncClient, owner_ctx):
    resp = await client.post("/api/v1/intents", json={
        "title": "Buy laptop",
        "intent_type": "PURCHASE",
        "natural_language_request": "Find me a Lenovo laptop under ₹80,000",
        "structured_constraints": {
            "amount": {"maximum": 80000, "currency": "INR"},
            "product": {"category": "LAPTOP", "preferred_brands": ["Lenovo"]},
        },
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["version"] == 1
    assert data["intent_type"] == "PURCHASE"
    assert data["structured_constraints"]["amount"]["maximum"] == 80000


async def test_create_intent_invalid_constraints_extra_field(client: AsyncClient, owner_ctx):
    """Extra fields in IntentConstraints should be rejected (extra=forbid)."""
    resp = await client.post("/api/v1/intents", json={
        "title": "Bad intent",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy something",
        "structured_constraints": {
            "evil_field": "injected",  # Should be rejected
        },
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 422


async def test_create_purchase_intent_regression_and_retrieval(client: AsyncClient, owner_ctx):
    """Regression test: Create a Purchase intent using the exact payload constructed in new.tsx, verify persistence, and retrieve it."""
    # Matches the exact payload constructed in frontend new.tsx
    frontend_payload = {
        "title": "College Laptop Purchase",
        "natural_language_request": "College Laptop Purchase",
        "structured_constraints": {
            "amount": {"maximum": 80000, "currency": "INR"},
            "product": {"category": "LAPTOP", "preferred_brands": ["Lenovo", "Dell"]},
            "approval": {"approval_required": True}
        },
        "intent_type": "PURCHASE"
    }

    create_resp = await client.post(
        "/api/v1/intents",
        json=frontend_payload,
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert create_resp.status_code == 201, f"Expected 201 Created but got {create_resp.status_code}: {create_resp.text}"
    created_data = create_resp.json()
    intent_id = created_data["id"]

    assert created_data["title"] == "College Laptop Purchase"
    assert created_data["intent_type"] == "PURCHASE"
    assert created_data["status"] == "DRAFT"
    assert created_data["structured_constraints"]["amount"]["maximum"] == 80000
    assert created_data["structured_constraints"]["product"]["category"] == "LAPTOP"

    # Retrieve and verify database persistence
    get_resp = await client.get(
        f"/api/v1/intents/{intent_id}",
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert get_resp.status_code == 200, f"Expected 200 OK but got {get_resp.status_code}: {get_resp.text}"
    retrieved_data = get_resp.json()
    assert retrieved_data["id"] == intent_id
    assert retrieved_data["title"] == "College Laptop Purchase"
    assert retrieved_data["intent_type"] == "PURCHASE"
    assert retrieved_data["structured_constraints"]["amount"]["maximum"] == 80000
    assert retrieved_data["structured_constraints"]["product"]["preferred_brands"] == ["Lenovo", "Dell"]


async def test_create_intent_empty_nl_request_failure_regression(client: AsyncClient, owner_ctx):
    """Regression test: Reproduce exact 422 failure when natural_language_request is empty."""
    failing_payload = {
        "title": "College Laptop Purchase",
        "natural_language_request": "",
        "structured_constraints": {},
        "intent_type": "PURCHASE"
    }
    resp = await client.post(
        "/api/v1/intents",
        json=failing_payload,
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    details = data["error"]["details"]
    assert any(d["loc"][-1] == "natural_language_request" for d in details)


async def test_create_intent_extracted_proposal_payload(client: AsyncClient, owner_ctx):
    """Regression test: Flow from /extract to /intents using extracted proposed_constraints."""
    extract_resp = await client.post(
        "/api/v1/intents/extract",
        json={"text": "I want to buy a laptop for college under ₹80,000. It must be Lenovo or Dell, and from Amazon or Flipkart."},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert extract_resp.status_code == 200
    proposal = extract_resp.json()

    create_payload = {
        "title": proposal["proposed_title"],
        "natural_language_request": "I want to buy a laptop for college under ₹80,000. It must be Lenovo or Dell, and from Amazon or Flipkart.",
        "structured_constraints": proposal["proposed_constraints"],
        "intent_type": proposal["proposed_type"]
    }
    create_resp = await client.post(
        "/api/v1/intents",
        json=create_payload,
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["intent_type"] == "PURCHASE"
    assert created["structured_constraints"]["amount"]["maximum"] == 80000
    assert "Lenovo" in created["structured_constraints"]["product"]["preferred_brands"]




async def test_get_intent(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "T1", "intent_type": "SEARCH",
        "natural_language_request": "Find laptops",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    resp = await client.get(f"/api/v1/intents/{intent_id}", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["id"] == intent_id


async def test_list_intents(client: AsyncClient, owner_ctx):
    for i in range(3):
        await client.post("/api/v1/intents", json={
            "title": f"Intent {i}", "intent_type": "SEARCH",
            "natural_language_request": f"Find thing {i}",
        }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    resp = await client.get("/api/v1/intents", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_update_intent_increments_version(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "V1 Intent", "intent_type": "SEARCH",
        "natural_language_request": "find laptops",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    update = await client.patch(f"/api/v1/intents/{intent_id}", json={
        "title": "V2 Intent",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert update.status_code == 200
    assert update.json()["version"] == 2
    assert update.json()["title"] == "V2 Intent"


async def test_confirm_intent_transitions_to_active(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "Confirmable", "intent_type": "PURCHASE",
        "natural_language_request": "Buy laptop",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    confirm = await client.post(f"/api/v1/intents/{intent_id}/confirm",
                                 headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "ACTIVE"


async def test_confirm_only_works_on_draft(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "T", "intent_type": "SEARCH", "natural_language_request": "find",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]
    await client.post(f"/api/v1/intents/{intent_id}/confirm", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    # Confirm again should fail
    resp = await client.post(f"/api/v1/intents/{intent_id}/confirm", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 400


async def test_pause_intent(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "T", "intent_type": "SEARCH", "natural_language_request": "find",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]
    await client.post(f"/api/v1/intents/{intent_id}/confirm", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    resp = await client.post(f"/api/v1/intents/{intent_id}/pause", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"


async def test_revoke_intent(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "T", "intent_type": "SEARCH", "natural_language_request": "find",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]
    resp = await client.post(f"/api/v1/intents/{intent_id}/revoke", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOKED"


async def test_versions_created_on_update(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "V1", "intent_type": "SEARCH", "natural_language_request": "find",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]
    await client.patch(f"/api/v1/intents/{intent_id}", json={"title": "V2"},
                       headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    versions = await client.get(f"/api/v1/intents/{intent_id}/versions",
                                headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert versions.status_code == 200
    assert len(versions.json()) == 2
    assert versions.json()[0]["version_number"] == 1
    assert versions.json()[1]["version_number"] == 2


async def test_workspace_isolation_idor(client: AsyncClient, owner_ctx, db_session: AsyncSession):
    """Workspace A cannot access Workspace B's intent."""
    # Create second workspace
    user2 = User(
        id=f"usr_{uuid.uuid4().hex[:16]}",
        email=f"b_{uuid.uuid4().hex[:8]}@test.com",
        full_name="User B",
        password_hash=get_password_hash("pass"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user2)
    ws2 = Workspace(
        id=f"ws_{uuid.uuid4().hex[:16]}",
        name="WS B",
        slug=f"ws-b-{uuid.uuid4().hex[:8]}",
        owner_id=user2.id,
    )
    db_session.add(ws2)
    await db_session.flush()
    member2 = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex[:16]}",
        workspace_id=ws2.id,
        user_id=user2.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member2)
    token2 = generate_session_token()
    sess2 = Session(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user2.id,
        token_hash=hash_session_token(token2),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(sess2)
    await db_session.commit()
    headers2 = {"X-Workspace-ID": ws2.id}
    cookies2 = {"finshield_session": token2}

    # Create intent in WS1
    create = await client.post("/api/v1/intents", json={
        "title": "Secret", "intent_type": "PURCHASE", "natural_language_request": "secret purchase",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    # WS2 tries to access WS1 intent
    resp = await client.get(f"/api/v1/intents/{intent_id}", headers=headers2, cookies=cookies2)
    assert resp.status_code == 404  # Must not leak


# ─── Extract endpoint tests ───────────────────────────────────────────────────

async def test_extract_endpoint(client: AsyncClient, owner_ctx):
    resp = await client.post("/api/v1/intents/extract", json={
        "text": "Buy me a Lenovo laptop for college, under ₹80,000"
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    data = resp.json()
    assert "proposed_type" in data
    assert "proposed_constraints" in data
    assert "refused_inferences" in data
    # Purchase intent must refuse payment authority
    assert any("payment_authority" in r for r in data["refused_inferences"])


async def test_extract_does_not_create_intent(client: AsyncClient, owner_ctx):
    await client.post("/api/v1/intents/extract", json={
        "text": "Buy me a Lenovo laptop"
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    # List should still be empty
    list_resp = await client.get("/api/v1/intents", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert list_resp.json() == []


# ─── Evaluate alignment endpoint ──────────────────────────────────────────────

async def test_evaluate_alignment_endpoint_laptop_aligned(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "Laptop intent",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy a laptop under 80k",
        "structured_constraints": {
            "amount": {"maximum": 80000, "currency": "INR"},
            "product": {"category": "LAPTOP"},
        },
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    resp = await client.post("/api/v1/intents/evaluate", json={
        "intent_id": intent_id,
        "action": "search_products",
        "amount": 70000,
        "product_category": "LAPTOP",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["alignment"] == "ALIGNED"


async def test_evaluate_alignment_endpoint_laptop_misaligned(client: AsyncClient, owner_ctx):
    create = await client.post("/api/v1/intents", json={
        "title": "Laptop intent",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy a laptop under 80k",
        "structured_constraints": {
            "product": {"category": "LAPTOP"},
        },
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = create.json()["id"]

    resp = await client.post("/api/v1/intents/evaluate", json={
        "intent_id": intent_id,
        "action": "search_products",
        "product_category": "HEADPHONES",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["alignment"] == "MISALIGNED"


# ─── Authority CRUD tests ─────────────────────────────────────────────────────

async def test_create_authority(client: AsyncClient, owner_ctx, active_agent):
    resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART"],
        "monetary_limit": 80000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["version"] == 1
    assert "SEARCH_PRODUCTS" in data["allowed_capabilities"]


async def test_activate_authority(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
        "monetary_limit": 80000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]

    resp = await client.post(f"/api/v1/authorities/{auth_id}/activate",
                              headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


async def test_revoke_authority(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    resp = await client.post(f"/api/v1/authorities/{auth_id}/revoke",
                              headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOKED"


async def test_authority_version_created_on_update(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
        "monetary_limit": 80000,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]

    await client.patch(f"/api/v1/authorities/{auth_id}", json={
        "monetary_limit": 70000,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    versions = await client.get(f"/api/v1/authorities/{auth_id}/versions",
                                headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert len(versions.json()) == 2


# ─── Authority Simulator tests ────────────────────────────────────────────────

async def test_authority_simulator_authorized(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
        "monetary_limit": 100000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    resp = await client.post("/api/v1/authorities/evaluate", json={
        "authority_id": auth_id,
        "agent_id": active_agent.id,
        "action": "SEARCH_PRODUCTS",
        "amount": 70000,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["authorized"] is True


async def test_authority_simulator_denied_revoked(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    await client.post(f"/api/v1/authorities/{auth_id}/revoke", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    resp = await client.post("/api/v1/authorities/evaluate", json={
        "authority_id": auth_id,
        "agent_id": active_agent.id,
        "action": "SEARCH_PRODUCTS",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["authorized"] is False


async def test_authority_simulator_denied_amount_exceeded(client: AsyncClient, owner_ctx, active_agent):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["PAY_ORDER"],
        "monetary_limit": 50000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    resp = await client.post("/api/v1/authorities/evaluate", json={
        "authority_id": auth_id,
        "agent_id": active_agent.id,
        "action": "PAY_ORDER",
        "amount": 90000,  # Exceeds 50k limit
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["authorized"] is False


async def test_authority_simulator_denied_capability_not_in_list(
    client: AsyncClient, owner_ctx, active_agent
):
    create = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],  # Only search allowed
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = create.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    resp = await client.post("/api/v1/authorities/evaluate", json={
        "authority_id": auth_id,
        "agent_id": active_agent.id,
        "action": "PAY_ORDER",  # Not in allowlist
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert resp.status_code == 200
    assert resp.json()["authorized"] is False


async def test_authority_simulator_endpoint_allowed_and_denied_no_side_effects(
    client: AsyncClient, owner_ctx, active_agent, db_session: AsyncSession
):
    """
    Test POST /api/v1/authorities/{authority_id}/simulate:
    1. Exact browser payload: EXECUTE_PAYMENT, amount=150, currency=INR
    2. Test allowed capability when authority is active and capability is present
    3. Test denied capability when capability is not permitted
    4. Confirm simulation does NOT create carts, orders, or payments
    """
    from sqlalchemy import select, func
    from app.models.commerce import Cart, Order
    from app.models.payment import Payment

    # Create an Intent
    intent_resp = await client.post("/api/v1/intents", json={
        "title": "College Laptop Purchase",
        "natural_language_request": "Buy laptop for college under 40000",
        "structured_constraints": {
            "amount": {"minimum": 100, "maximum": 40000, "currency": "INR"},
            "product": {"category": "LAPTOP"},
        },
        "intent_type": "PURCHASE"
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert intent_resp.status_code == 201
    intent_id = intent_resp.json()["id"]

    # Ensure agent has EXECUTE_PAYMENT in its capabilities
    active_agent.capabilities = ["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER", "EXECUTE_PAYMENT"]
    await db_session.commit()

    # Create an Authority bound to active_agent and intent
    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "EXECUTE_PAYMENT"],
        "monetary_limit": 40000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert auth_resp.status_code == 201
    auth_id = auth_resp.json()["id"]

    # Activate authority
    activate_resp = await client.post(
        f"/api/v1/authorities/{auth_id}/activate",
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"]
    )
    assert activate_resp.status_code == 200

    # Snapshot existing carts, orders, payments counts
    carts_before = (await db_session.execute(select(func.count(Cart.id)))).scalar()
    orders_before = (await db_session.execute(select(func.count(Order.id)))).scalar()
    payments_before = (await db_session.execute(select(func.count(Payment.id)))).scalar()

    # 1. Exact browser request: EXECUTE_PAYMENT, amount=150, currency=INR
    # Note: Intent has no approval constraint configured here, so authorized=True and requires_approval=False
    sim_resp_allowed = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "EXECUTE_PAYMENT", "amount": 150, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert sim_resp_allowed.status_code == 200, f"Expected 200 but got {sim_resp_allowed.status_code}: {sim_resp_allowed.text}"
    result_allowed = sim_resp_allowed.json()
    assert result_allowed["authorized"] is True
    assert result_allowed["reasons"] == []
    assert result_allowed["effective_monetary_limit"] == 40000
    assert result_allowed["alignment_result"] == "ALIGNED"

    # 2. Test denied capability: UNKNOWN_ACTION or unauthorized capability
    sim_resp_denied = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "TRANSFER_FUNDS", "amount": 150, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert sim_resp_denied.status_code == 200
    result_denied = sim_resp_denied.json()
    assert result_denied["authorized"] is False
    assert any("not in the authority's allowed capabilities" in r or "lacks capability" in r for r in result_denied["reasons"])

    # 3. Test denied due to amount exceeding limit
    sim_resp_exceeded = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "EXECUTE_PAYMENT", "amount": 50000, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert sim_resp_exceeded.status_code == 200
    result_exceeded = sim_resp_exceeded.json()
    assert result_exceeded["authorized"] is False
    assert any("exceeds effective authority limit" in r for r in result_exceeded["reasons"])

    # 4. Verify no financial side-effects were created
    carts_after = (await db_session.execute(select(func.count(Cart.id)))).scalar()
    orders_after = (await db_session.execute(select(func.count(Order.id)))).scalar()
    payments_after = (await db_session.execute(select(func.count(Payment.id)))).scalar()

    assert carts_after == carts_before, "Simulator must not create carts"
    assert orders_after == orders_before, "Simulator must not create orders"
    assert payments_after == payments_before, "Simulator must not create payments"


async def test_authority_simulator_approval_threshold_enforcement(
    client: AsyncClient, owner_ctx, active_agent, db_session: AsyncSession
):
    """
    Test approval enforcement across amounts 99, 100, and 150 derived from persisted intent:
    - Intent max: 40000, approval_required_above: 100
    - Amount 99 (below threshold) -> authorized=True, requires_approval=False
    - Amount 100 (at threshold) -> authorized=True, requires_approval=False
    - Amount 150 (above threshold) -> authorized=True, requires_approval=True
    - Simulator remains side-effect-free (no carts, orders, or payments)
    """
    from sqlalchemy import select, func
    from app.models.commerce import Cart, Order
    from app.models.payment import Payment

    # 1. Create Intent with natural language request containing approval threshold
    intent_resp = await client.post("/api/v1/intents", json={
        "title": "Purchase laptop under INR 40,000",
        "natural_language_request": "I want to purchase a laptop under ₹40,000. Purchases above ₹100 require approval.",
        "structured_constraints": {
            "amount": {"maximum": 40000, "currency": "INR"},
            "product": {"category": "LAPTOP"},
            "approval": {"approval_required": True, "approval_required_above": 100},
        },
        "intent_type": "PURCHASE"
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert intent_resp.status_code == 201
    intent_id = intent_resp.json()["id"]

    active_agent.capabilities = ["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER", "EXECUTE_PAYMENT"]
    await db_session.commit()

    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER", "EXECUTE_PAYMENT"],
        "monetary_limit": 40000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert auth_resp.status_code == 201
    auth_id = auth_resp.json()["id"]

    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    carts_before = (await db_session.execute(select(func.count(Cart.id)))).scalar()
    orders_before = (await db_session.execute(select(func.count(Order.id)))).scalar()
    payments_before = (await db_session.execute(select(func.count(Payment.id)))).scalar()

    # Amount 99: below threshold -> requires_approval=False
    resp_99 = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "EXECUTE_PAYMENT", "amount": 99, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert resp_99.status_code == 200
    res_99 = resp_99.json()
    assert res_99["authorized"] is True
    assert res_99["requires_approval"] is False
    assert res_99["alignment_result"] == "ALIGNED"

    # Amount 100: at threshold -> requires_approval=False
    resp_100 = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "EXECUTE_PAYMENT", "amount": 100, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert resp_100.status_code == 200
    res_100 = resp_100.json()
    assert res_100["authorized"] is True
    assert res_100["requires_approval"] is False
    assert res_100["alignment_result"] == "ALIGNED"

    # Amount 150: above threshold -> requires_approval=True
    resp_150 = await client.post(
        f"/api/v1/authorities/{auth_id}/simulate",
        json={"action": "EXECUTE_PAYMENT", "amount": 150, "currency": "INR"},
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert resp_150.status_code == 200
    res_150 = resp_150.json()
    assert res_150["authorized"] is True
    assert res_150["requires_approval"] is True
    assert res_150["alignment_result"] == "ALIGNED"

    # Simulator must remain side-effect-free
    carts_after = (await db_session.execute(select(func.count(Cart.id)))).scalar()
    orders_after = (await db_session.execute(select(func.count(Order.id)))).scalar()
    payments_after = (await db_session.execute(select(func.count(Payment.id)))).scalar()

    assert carts_after == carts_before
    assert orders_after == orders_before
    assert payments_after == payments_before


async def test_action_gate_review_blocks_execution_until_approved(
    client: AsyncClient, owner_ctx, active_agent, db_session: AsyncSession
):
    """
    Test Action Gate REVIEW decision prevents execution and creates NO payment until approved:
    1. Intent with approval_required_above: 100.
    2. Order with total ₹150 exceeds approval threshold.
    3. pay_order triggers Action Gate REVIEW -> returns 402 PENDING_APPROVAL.
    4. Verify NO payment record exists in DB.
    5. Approve the approval request.
    6. Re-executing pay_order now succeeds (ALLOW) and captures payment.
    """
    from app.models.commerce import Merchant, Product, Order, OrderItem, OrderStatus
    from app.models.payment import Payment
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from sqlalchemy import select

    # Create Merchant & Product
    merchant = Merchant(
        id=f"mer_{uuid.uuid4().hex[:12]}",
        workspace_id=owner_ctx["workspace_id"],
        name="TechStore",
    )
    db_session.add(merchant)
    await db_session.flush()

    product = Product(
        id=f"prd_{uuid.uuid4().hex[:12]}",
        merchant_id=merchant.id,
        name="Laptop Accessory",
        category="LAPTOP",
        price=150,
        currency="INR",
        inventory=10,
    )
    db_session.add(product)
    await db_session.flush()

    # Create Order for ₹150
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        workspace_id=owner_ctx["workspace_id"],
        merchant_id=merchant.id,
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=150,
        total=150,
        currency="INR",
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        id=f"item_{uuid.uuid4().hex[:12]}",
        order_id=order.id,
        product_id=product.id,
        product_name_snapshot=product.name,
        merchant_name_snapshot=merchant.name,
        quantity=1,
        unit_price_at_order=150,
        total=150,
    )
    db_session.add(item)
    await db_session.commit()

    # Create Intent with approval threshold ₹100
    intent_resp = await client.post("/api/v1/intents", json={
        "title": "Laptop purchases",
        "natural_language_request": "Buy laptop under 40000. Above 100 requires approval.",
        "structured_constraints": {
            "amount": {"maximum": 40000, "currency": "INR"},
            "product": {"category": "LAPTOP"},
            "approval": {"approval_required": True, "approval_required_above": 100},
        },
        "intent_type": "PURCHASE"
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert intent_resp.status_code == 201
    intent_id = intent_resp.json()["id"]

    # Delegated authority with PAY_ORDER capability
    active_agent.capabilities = ["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER"]
    await db_session.commit()

    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "PAY_ORDER"],
        "monetary_limit": 40000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert auth_resp.status_code == 201
    auth_id = auth_resp.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    # Start an agent run (manual execution test, auto_start=False)
    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "Pay for order",
        "authority_id": auth_id,
        "auto_start": False,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    # Attempt pay_order with amount 150 (> threshold 100)
    pay_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"order_id": order.id, "amount": 150, "currency": "INR"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    # Action Gate must intercept and return HTTP 402 (REVIEW / PENDING_APPROVAL)
    assert pay_resp.status_code == 402, f"Expected 402 but got {pay_resp.status_code}: {pay_resp.text}"
    assert "requires human approval" in pay_resp.text

    # PROVE that NO payment was created for this order
    stmt_pmt = select(Payment).where(Payment.order_id == order.id)
    payments_found = (await db_session.execute(stmt_pmt)).scalars().all()
    assert len(payments_found) == 0, "No payment should exist before approval"

    # Find the created ApprovalRequest
    stmt_appr = select(ApprovalRequest).where(
        ApprovalRequest.agent_run_id == run_id,
        ApprovalRequest.workspace_id == owner_ctx["workspace_id"]
    )
    appr_res = await db_session.execute(stmt_appr)
    approval = appr_res.scalars().first()
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING

    # Authenticated human approves the transaction context
    approve_resp = await client.post(
        f"/api/v1/approvals/{owner_ctx['workspace_id']}/approvals/{approval.id}/approve",
        headers=owner_ctx["headers"],
        cookies=owner_ctx["cookies"],
    )
    assert approve_resp.status_code == 200

    # Retry pay_order: should now succeed (revalidation ALLOW)
    pay_retry_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"order_id": order.id, "amount": 150, "currency": "INR"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert pay_retry_resp.status_code == 200
    action_data = pay_retry_resp.json()
    assert action_data["status"] == "SUCCESS"

    # Now verify payment was created
    stmt_pmt_after = select(Payment).where(Payment.order_id == order.id)
    payments_after = (await db_session.execute(stmt_pmt_after)).scalars().all()
    assert len(payments_after) == 1, "Payment must be captured after human approval"
    assert payments_after[0].amount == 150




# ─── Runtime Phase 8 integration tests ───────────────────────────────────────

async def test_runtime_with_active_authority_allows_authorized_action(
    client: AsyncClient, owner_ctx, active_agent
):
    """Full pipeline: create authority → activate → create run → execute authorized action."""
    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
        "monetary_limit": 100000,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = auth_resp.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "Find me a laptop",
        "authority_id": auth_id,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    action_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "search_products",
        "input": {"query": "laptop"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert action_resp.status_code == 200
    data = action_resp.json()
    assert data["status"] == "SUCCESS"
    # Verify authority is stamped on action
    assert data["authority_id"] == auth_id
    assert data["authority_version"] == 1


async def test_runtime_authority_denied_action_blocked(
    client: AsyncClient, owner_ctx, active_agent
):
    """Authority with only SEARCH does not allow PAY_ORDER — tool must NOT execute."""
    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],  # PAY_ORDER NOT included
        "monetary_limit": 100000,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = auth_resp.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "Pay for order",
        "authority_id": auth_id,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    run_id = run_resp.json()["id"]

    action_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "pay_order",
        "input": {"order_id": "ord_test"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    print("ACTION RESP TEXT:", action_resp.text)
    assert action_resp.status_code == 403
    assert "Authority denied" in action_resp.text


async def test_runtime_revoked_authority_blocks_action(
    client: AsyncClient, owner_ctx, active_agent
):
    """After revocation, actions on that run are denied."""
    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = auth_resp.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "Find laptops",
        "authority_id": auth_id,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    run_id = run_resp.json()["id"]

    # Revoke authority now
    await client.post(f"/api/v1/authorities/{auth_id}/revoke", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    # Try to execute action after revocation
    action_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "search_products",
        "input": {"query": "laptop"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert action_resp.status_code == 403


async def test_runtime_without_authority_still_works(
    client: AsyncClient, owner_ctx, active_agent
):
    """Running without an authority should fall through to capability check (backward compat)."""
    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "Find a laptop",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    action_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "search_products",
        "input": {"query": "laptop"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "SUCCESS"


async def test_runtime_action_stamped_with_intent_and_alignment(
    client: AsyncClient, owner_ctx, active_agent
):
    """Actions should be stamped with intent_id and alignment_result when intent is linked."""
    intent_resp = await client.post("/api/v1/intents", json={
        "title": "Find laptop",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy a laptop under 80k",
        "structured_constraints": {
            "product": {"category": "LAPTOP"},
        },
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    intent_id = intent_resp.json()["id"]
    await client.post(f"/api/v1/intents/{intent_id}/confirm", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    auth_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS"],
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    auth_id = auth_resp.json()["id"]
    await client.post(f"/api/v1/authorities/{auth_id}/activate", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])

    run_resp = await client.post("/api/v1/agent-runtime/runs", json={
        "agent_id": active_agent.id,
        "input": "search for laptop",
        "authority_id": auth_id,
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    run_id = run_resp.json()["id"]

    action_resp = await client.post(f"/api/v1/agent-runtime/runs/{run_id}/actions", json={
        "tool_name": "search_products",
        "input": {"query": "laptop", "category": "LAPTOP"},
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert action_resp.status_code == 200
    data = action_resp.json()
    assert data["intent_id"] == intent_id
    assert data["authority_id"] == auth_id
    assert data["alignment_result"] is not None


async def test_authority_detail_and_version_history_response_contract(
    client: AsyncClient, owner_ctx, active_agent
):
    """
    Regression test for Authority detail page crash:
    Verify that GET /api/v1/authorities/{id} and GET /api/v1/authorities/{id}/versions
    return the expected contract so frontend components can safely render version histories,
    snapshots, and simulation details without throwing runtime ReferenceError/TypeErrors.
    """
    # 1. Create authority
    create_resp = await client.post("/api/v1/authorities", json={
        "agent_id": active_agent.id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "EXECUTE_PAYMENT"],
        "monetary_limit": 40000,
        "currency": "INR",
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert create_resp.status_code == 201
    auth_data = create_resp.json()
    auth_id = auth_data["id"]
    assert auth_data["version"] == 1

    # 2. Update authority (creates version 2)
    patch_resp = await client.patch(f"/api/v1/authorities/{auth_id}", json={
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "EXECUTE_PAYMENT"],
    }, headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["version"] == 2

    # 3. Fetch authority detail
    get_resp = await client.get(f"/api/v1/authorities/{auth_id}", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == auth_id
    assert detail["version"] == 2
    assert "MANAGE_CART" in detail["allowed_capabilities"]

    # 4. Fetch authority version history
    versions_resp = await client.get(f"/api/v1/authorities/{auth_id}/versions", headers=owner_ctx["headers"], cookies=owner_ctx["cookies"])
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert len(versions) == 2
    for v in versions:
        assert "version_number" in v
        assert "snapshot" in v
        assert "allowed_capabilities" in v["snapshot"]
        assert "monetary_limit" in v["snapshot"]

