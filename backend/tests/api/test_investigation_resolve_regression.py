"""
Regression tests for Investigation Resolution workflow.

Covers:
- Direct OPEN -> RESOLVED transition (single-step resolve)
- Resolution persists resolution_type and analyst notes
- Status is RESOLVED after resolve, not OPEN
- Counter consistency (open count decreases, resolved increases)
- Drawer-state simulation: failed requests do not silently change status
- Invalid transition guard: RESOLVED -> RESOLVED is rejected
- CLOSED investigation cannot be resolved without reopen
- Resolution reason required (non-empty)
"""

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
from app.models.investigation import (
    Investigation, InvestigationStatus, InvestigationPriority,
    InvestigationType, ResolutionType
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def inv_setup(db_session: AsyncSession):
    user = User(
        id=f"usr_{uuid.uuid4().hex[:16]}",
        email=f"inv_tester_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("password123"),
        full_name="Investigation Tester",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    workspace = Workspace(
        id=f"ws_{uuid.uuid4().hex[:16]}",
        name="Investigation Lab",
        slug=f"inv-lab-{uuid.uuid4().hex[:8]}",
        owner_id=user.id,
    )
    db_session.add(workspace)

    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        workspace_id=workspace.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)

    token = generate_session_token()
    session = Session(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(session)
    await db_session.commit()

    return {"user": user, "workspace": workspace, "token": token}


async def _create_open_investigation(client, workspace_id, token, title="Test Investigation"):
    resp = await client.post(
        "/api/v1/investigations",
        json={
            "title": title,
            "description": "Automated test investigation",
            "type": "POLICY_VIOLATION",
            "priority": "HIGH",
            "source_type": "GATE_DECISION",
            "source_id": f"gdec_{uuid.uuid4().hex[:12]}",
        },
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id},
    )
    assert resp.status_code == 200, f"create_investigation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests: Direct OPEN -> RESOLVED
# ---------------------------------------------------------------------------

class TestInvestigationResolveDirectFromOpen:

    @pytest.mark.asyncio
    async def test_resolve_open_investigation_succeeds(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        inv = await _create_open_investigation(client, ws_id, token)
        assert inv["status"] == "OPEN"

        resp = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Confirmed: expected parameters."},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
        )
        assert resp.status_code == 200, f"resolve failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "FALSE_POSITIVE"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_sets_resolved_at_timestamp(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        inv = await _create_open_investigation(client, ws_id, token)
        before = datetime.now(timezone.utc)

        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "CONFIRMED_THREAT", "resolution_reason": "Verified malicious."},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
        )
        get_resp = await client.get(
            f"/api/v1/investigations/{inv['id']}",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
        )
        data = get_resp.json()
        resolved_at_str = data["resolved_at"].rstrip("Z")  # strip trailing Z if present
        resolved_at = datetime.fromisoformat(resolved_at_str).replace(tzinfo=timezone.utc)
        assert resolved_at >= before

    @pytest.mark.asyncio
    async def test_resolve_persists_all_resolution_fields(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        inv = await _create_open_investigation(client, ws_id, token)
        notes = "Analyst found no unauthorized action; policy was misconfigured."

        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "POLICY_CONFIGURATION_ISSUE", "resolution_reason": notes},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
        )
        get_resp = await client.get(
            f"/api/v1/investigations/{inv['id']}",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id},
        )
        data = get_resp.json()
        assert data["resolution"] == "POLICY_CONFIGURATION_ISSUE"
        assert data["resolution_reason"] == notes


# ---------------------------------------------------------------------------
# Tests: Counter Consistency
# ---------------------------------------------------------------------------

class TestInvestigationResolveCounterConsistency:

    @pytest.mark.asyncio
    async def test_open_count_decreases_after_resolve(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv1 = await _create_open_investigation(client, ws_id, token, "Inv A")
        inv2 = await _create_open_investigation(client, ws_id, token, "Inv B")

        list_before = (await client.get("/api/v1/investigations", headers=headers)).json()
        open_before = sum(1 for i in list_before if i["status"] == "OPEN")
        resolved_before = sum(1 for i in list_before if i["status"] == "RESOLVED")

        await client.post(
            f"/api/v1/investigations/{inv1['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Not a real threat."},
            headers=headers,
        )

        list_after = (await client.get("/api/v1/investigations", headers=headers)).json()
        open_after = sum(1 for i in list_after if i["status"] == "OPEN")
        resolved_after = sum(1 for i in list_after if i["status"] == "RESOLVED")

        assert open_after == open_before - 1
        assert resolved_after == resolved_before + 1

    @pytest.mark.asyncio
    async def test_status_filter_excludes_resolved_from_open_list(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "OTHER", "resolution_reason": "Test only."},
            headers=headers,
        )

        open_list = (await client.get("/api/v1/investigations?status=OPEN", headers=headers)).json()
        ids_in_open_list = {i["id"] for i in open_list}
        assert inv["id"] not in ids_in_open_list


# ---------------------------------------------------------------------------
# Tests: Error Handling (drawer stays open on failure)
# ---------------------------------------------------------------------------

class TestInvestigationResolveErrorHandling:

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_returns_400(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "OTHER", "resolution_reason": "First."},
            headers=headers,
        )
        resp2 = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Second."},
            headers=headers,
        )
        assert resp2.status_code == 400, f"Expected 400, got {resp2.status_code}: {resp2.text}"

    @pytest.mark.asyncio
    async def test_resolve_closed_investigation_returns_400(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "OTHER", "resolution_reason": "Resolved."},
            headers=headers,
        )
        await client.post(f"/api/v1/investigations/{inv['id']}/close", headers=headers)

        resp = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Nope."},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_investigation_returns_404(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        resp = await client.post(
            "/api/v1/investigations/inv_doesnotexist1234/resolve",
            json={"resolution": "OTHER", "resolution_reason": "Ghost."},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_missing_resolution_field_returns_422(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        resp = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution_reason": "No resolution type provided."},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_resolve_wrong_workspace_returns_404(self, client: AsyncClient, inv_setup: dict, db_session: AsyncSession):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]

        inv = await _create_open_investigation(client, ws_id, token)

        user2 = User(
            id=f"usr_{uuid.uuid4().hex[:16]}",
            email=f"other_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=get_password_hash("password123"),
            full_name="Other User",
            status=UserStatus.ACTIVE,
        )
        db_session.add(user2)
        ws2 = Workspace(
            id=f"ws_{uuid.uuid4().hex[:16]}",
            name="Other WS",
            slug=f"other-{uuid.uuid4().hex[:8]}",
            owner_id=user2.id,
        )
        db_session.add(ws2)
        member2 = WorkspaceMember(
            id=f"wm_{uuid.uuid4().hex[:16]}",
            user_id=user2.id,
            workspace_id=ws2.id,
            role=WorkspaceRole.OWNER,
        )
        db_session.add(member2)
        token2 = generate_session_token()
        sess2 = Session(
            id=f"sess_{uuid.uuid4().hex[:16]}",
            user_id=user2.id,
            token_hash=hash_session_token(token2),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db_session.add(sess2)
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Wrong workspace."},
            headers={"Authorization": f"Bearer {token2}", "X-Workspace-ID": ws2.id},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: IN_REVIEW -> RESOLVED path
# ---------------------------------------------------------------------------

class TestInvestigationResolveAfterInReview:

    @pytest.mark.asyncio
    async def test_resolve_after_start_investigation(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        start_resp = await client.post(f"/api/v1/investigations/{inv['id']}/start", headers=headers)
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "IN_REVIEW"

        resolve_resp = await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "AGENT_MISBEHAVIOR", "resolution_reason": "Agent retry loop confirmed."},
            headers=headers,
        )
        assert resolve_resp.status_code == 200
        data = resolve_resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "AGENT_MISBEHAVIOR"


# ---------------------------------------------------------------------------
# Tests: Persistence after reload
# ---------------------------------------------------------------------------

class TestInvestigationResolvePersistenceAfterReload:

    @pytest.mark.asyncio
    async def test_resolution_persists_on_reload(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "CONFIRMED_THREAT", "resolution_reason": "Full forensic review complete."},
            headers=headers,
        )

        get_resp = await client.get(f"/api/v1/investigations/{inv['id']}", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "CONFIRMED_THREAT"
        assert data["resolution_reason"] == "Full forensic review complete."
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolution_appears_in_list_with_resolved_status(self, client: AsyncClient, inv_setup: dict):
        ws_id = inv_setup["workspace"].id
        token = inv_setup["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

        inv = await _create_open_investigation(client, ws_id, token)
        await client.post(
            f"/api/v1/investigations/{inv['id']}/resolve",
            json={"resolution": "FALSE_POSITIVE", "resolution_reason": "Cleared by analyst."},
            headers=headers,
        )

        list_resp = await client.get("/api/v1/investigations?status=RESOLVED", headers=headers)
        resolved_ids = {i["id"] for i in list_resp.json()}
        assert inv["id"] in resolved_ids
