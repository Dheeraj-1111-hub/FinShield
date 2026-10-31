"""
FINSHIELD POLICIES BACKEND ACCEPTANCE SUITE
===========================================
Tests A-H: Validates Policy behavior against the LIVE backend.
NO mocks.
"""
import pytest
import httpx
import uuid
from typing import Optional

pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

_AUTH_STATE_A = None
_AUTH_STATE_B = None

class HelperClient:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.workspace_id: Optional[str] = None
        self.user_id: Optional[str] = None

    async def setup(self, email: str = None, password: str = "Password123!", name: str = "QA User"):
        email = email or f"qa_{uuid.uuid4().hex[:8]}@finshield.dev"
        res = await self.client.post("/api/v1/auth/signup", json={
            "email": email, "password": password, "full_name": name
        })
        if res.status_code not in [200, 201]:
            res = await self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
            if res.status_code != 200:
                raise Exception(f"Auth failed: {res.status_code} {res.text}")
        self.client.cookies = res.cookies
        data = res.json()
        self.workspace_id = data["workspace"]["id"]
        self.user_id = data["user"]["id"]
        return data

    async def get(self, path: str, **kw):
        return await self.client.get(path, **kw)

    async def post(self, path: str, **kw):
        return await self.client.post(path, **kw)

    async def patch(self, path: str, **kw):
        return await self.client.patch(path, **kw)

    async def delete(self, path: str, **kw):
        return await self.client.delete(path, **kw)


@pytest.fixture
async def tc():
    global _AUTH_STATE_A
    client = HelperClient(BASE_URL)
    if _AUTH_STATE_A:
        client.client.cookies = _AUTH_STATE_A["cookies"]
        client.workspace_id = _AUTH_STATE_A["workspace_id"]
        client.user_id = _AUTH_STATE_A["user_id"]
    else:
        await client.setup()
        _AUTH_STATE_A = {"cookies": client.client.cookies, "workspace_id": client.workspace_id, "user_id": client.user_id}
    yield client
    await client.client.aclose()


@pytest.fixture
async def tc_b():
    global _AUTH_STATE_B
    client = HelperClient(BASE_URL)
    if _AUTH_STATE_B:
        client.client.cookies = _AUTH_STATE_B["cookies"]
        client.workspace_id = _AUTH_STATE_B["workspace_id"]
        client.user_id = _AUTH_STATE_B["user_id"]
    else:
        await client.setup()
        _AUTH_STATE_B = {"cookies": client.client.cookies, "workspace_id": client.workspace_id, "user_id": client.user_id}
    yield client
    await client.client.aclose()


async def test_A_create_and_fetch_policy(tc: HelperClient):
    payload = {
        "name": "Block High Transactions",
        "description": "Block any txn > 100k",
        "status": "ACTIVE",
        "priority": 100,
        "policy_type": "TRANSACTION_LIMIT",
        "conditions": {
            "transaction_amount": {"operator": "GT", "value": 100000}
        },
        "actions": {
            "decision": "BLOCK"
        }
    }
    
    r = await tc.post("/api/v1/policies", json=payload)
    assert r.status_code == 201
    policy = r.json()
    assert policy["name"] == payload["name"]
    assert policy["status"] == "ACTIVE"
    policy_id = policy["id"]
    
    # Fetch
    r = await tc.get(f"/api/v1/policies/{policy_id}")
    assert r.status_code == 200
    assert r.json()["id"] == policy_id


async def test_B_evaluate_policy_match(tc: HelperClient):
    # Ensure a matching policy blocks the evaluation
    req = {
        "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
        "amount": 150000, # Matches condition GT 100000
        "currency": "USD"
    }
    
    r = await tc.post("/api/v1/policies/evaluate", json=req)
    assert r.status_code == 200
    res = r.json()
    
    assert res["decision"] == "BLOCK"
    assert len(res["matched_policies"]) > 0


async def test_C_evaluate_policy_no_match(tc: HelperClient):
    # Ensure non-matching request allows by default or evaluates other policies
    req = {
        "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
        "amount": 50000, # Does NOT match GT 100000
        "currency": "USD"
    }
    
    r = await tc.post("/api/v1/policies/evaluate", json=req)
    assert r.status_code == 200
    res = r.json()
    
    assert res["decision"] == "ALLOW"
    assert len(res["matched_policies"]) == 0 # assuming no other policy matches


async def test_D_policy_precedence(tc: HelperClient):
    # Create an ALLOW policy with matching conditions
    allow_payload = {
        "name": "Allow Low Transactions",
        "status": "ACTIVE",
        "priority": 10,
        "policy_type": "TRANSACTION_LIMIT",
        "conditions": {
            "transaction_amount": {"operator": "LT", "value": 200000}
        },
        "actions": {
            "decision": "ALLOW"
        }
    }
    await tc.post("/api/v1/policies", json=allow_payload)
    
    # Send a request that matches both the BLOCK (> 100k) and ALLOW (< 200k) policies
    req = {
        "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
        "amount": 150000,
        "currency": "USD"
    }
    
    r = await tc.post("/api/v1/policies/evaluate", json=req)
    assert r.status_code == 200
    res = r.json()
    
    # BLOCK should take precedence over ALLOW
    assert res["decision"] == "BLOCK"
    # matched_policies only returns the WINNING policies, which are just the BLOCK ones
    assert len(res["matched_policies"]) == 1


async def test_E_audit_trail_generation(tc: HelperClient):
    # Check if creating a policy generated an audit trail
    
    # 1. Create a policy
    payload = {
        "name": "Audit Test Policy",
        "description": "Testing audit",
        "policy_type": "CUSTOM",
        "status": "ACTIVE",
        "priority": 5,
        "conditions": {"workspace": "all"},
        "actions": {"decision": "ALLOW"}
    }
    r = await tc.post("/api/v1/policies", json=payload)
    assert r.status_code == 201
    
    # 2. Check audit trail
    
    r = await tc.get("/api/v1/audit/")
    assert r.status_code == 200
    events = r.json()
    
    # Filter for POLICY events
    policy_events = [e for e in events if e.get("entity_type") == "POLICY"]
    if not policy_events:
        assert False, f"EVENTS: {events}"
    assert len(policy_events) > 0
    
    # Filter for POLICY_CREATED events
    created_events = [e for e in events if e["event_type"] == "POLICY_CREATED"]
    assert len(created_events) > 0
    
    event = created_events[-1] 
    assert event["event_category"] == "POLICY"
    assert "payload" in event


async def test_F_workspace_isolation(tc: HelperClient, tc_b: HelperClient):
    r = await tc.get("/api/v1/policies")
    policies_a = r.json()
    assert len(policies_a) > 0
    policy_id = policies_a[0]["id"]
    
    # tc_b shouldn't see it
    r_b = await tc_b.get(f"/api/v1/policies/{policy_id}")
    assert r_b.status_code == 404
    
    # tc_b list should be empty
    r_list = await tc_b.get("/api/v1/policies")
    assert len(r_list.json()) == 0


async def test_G_update_policy(tc: HelperClient):
    r = await tc.get("/api/v1/policies")
    policy_id = r.json()[0]["id"]
    
    r2 = await tc.patch(f"/api/v1/policies/{policy_id}", json={"status": "DISABLED"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "DISABLED"


async def test_H_disabled_policy_ignored(tc: HelperClient):
    # We just disabled the BLOCK policy. Let's test the 150k amount again.
    # It should only match the ALLOW policy now.
    req = {
        "agent_id": f"agent_{uuid.uuid4().hex[:8]}",
        "amount": 150000,
        "currency": "USD"
    }
    
    r = await tc.post("/api/v1/policies/evaluate", json=req)
    assert r.status_code == 200
    res = r.json()
    
    assert res["decision"] == "ALLOW"
    assert len(res["matched_policies"]) == 1
    assert res["matched_policies"][0]["name"] == "Allow Low Transactions"

