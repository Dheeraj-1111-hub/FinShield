"""
FINSHIELD RISK CENTER BACKEND ACCEPTANCE SUITE
============================================
Tests A-H: Validates Risk Center behavior against the LIVE backend.
NO mocks.
"""
import pytest
import httpx
import uuid
from typing import Dict, Any, Optional
import time

pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

_AUTH_STATE_A = None
_AUTH_STATE_B = None
_COMMERCE_ENV = None

class HelperClient:
    """Wraps httpx.AsyncClient with workspace-aware auth."""
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.workspace_id: Optional[str] = None

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
        return data

    async def get(self, path: str, **kw):
        return await self.client.get(path, **kw)

    async def post(self, path: str, **kw):
        return await self.client.post(path, **kw)

    async def put(self, path: str, **kw):
        return await self.client.put(path, **kw)

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
    else:
        await client.setup()
        _AUTH_STATE_A = {"cookies": client.client.cookies, "workspace_id": client.workspace_id}
    yield client
    await client.client.aclose()


@pytest.fixture
async def tc_b():
    global _AUTH_STATE_B
    client = HelperClient(BASE_URL)
    if _AUTH_STATE_B:
        client.client.cookies = _AUTH_STATE_B["cookies"]
        client.workspace_id = _AUTH_STATE_B["workspace_id"]
    else:
        await client.setup()
        _AUTH_STATE_B = {"cookies": client.client.cookies, "workspace_id": client.workspace_id}
    yield client
    await client.client.aclose()


async def setup_commerce(tc: HelperClient):
    """Create merchant, products, agent, intent, authority via real endpoints."""
    r = await tc.post("/api/v1/commerce/merchants", json={
        "name": "QA Tech Store Risk", "description": "Test merchant", "status": "ACTIVE"
    })
    assert r.status_code in [200, 201]
    merchant_id = r.json()["id"]

    products = {}
    for name, price, cat in [
        ("Laptop 40k", 4000000, "electronics"),
        ("Laptop 120k", 12000000, "electronics"),
    ]:
        r = await tc.post("/api/v1/commerce/products", json={
            "merchant_id": merchant_id, "name": name, "category": cat,
            "price": price, "currency": "INR", "inventory": 100, "status": "ACTIVE"
        })
        assert r.status_code in [200, 201]
        products[name] = r.json()

    r = await tc.post("/api/v1/agents", json={
        "name": "Risk Agent QA",
        "description": "Risk tests",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    })
    assert r.status_code in [200, 201]
    agent = r.json()
    agent_id = agent["id"]

    r = await tc.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"})
    assert r.status_code == 200

    r = await tc.post(f"/api/v1/agents/{agent_id}/credentials", json={"name": "QA Cred"})
    assert r.status_code in [200, 201]
    cred = r.json()
    agent_token = f"{cred['client_id']}:{cred['client_secret']}"

    r = await tc.post("/api/v1/intents", json={
        "title": "Buy Laptop Risk QA",
        "intent_type": "PURCHASE",
        "natural_language_request": "Buy electronics up to 80k INR",
        "agent_id": agent_id,
        "structured_constraints": {
            "amount": {"maximum": 8000000, "currency": "INR"},
            "product": {"category": "electronics"},
            "approval": {"approval_required_above": 5000000}
        },
        "status": "ACTIVE"
    })
    assert r.status_code in [200, 201]
    intent_id = r.json()["id"]

    r = await tc.post("/api/v1/authorities", json={
        "agent_id": agent_id,
        "intent_id": intent_id,
        "allowed_capabilities": ["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        "amount_limit": 8000000,
        "currency": "INR",
        "approval_threshold": 5000000,
        "status": "ACTIVE"
    })
    assert r.status_code in [200, 201]
    authority_id = r.json()["id"]

    return {
        "merchant_id": merchant_id,
        "products": products,
        "agent_id": agent_id,
        "agent_token": agent_token,
        "intent_id": intent_id,
        "authority_id": authority_id,
    }


@pytest.fixture
async def env(tc: HelperClient):
    global _COMMERCE_ENV
    if not _COMMERCE_ENV:
        _COMMERCE_ENV = await setup_commerce(tc)
    return _COMMERCE_ENV


async def exec_tool(tc: HelperClient, env: dict, run_id: str, tool: str, inp: dict):
    return await tc.post(
        f"/api/v1/agent-runtime/runs/{run_id}/actions",
        json={"tool_name": tool, "input": inp},
        headers={"Authorization": f"Bearer {env['agent_token']}"}
    )


async def test_A_legitimate_low_risk_action(tc: HelperClient, env: dict):
    agent_id = env["agent_id"]
    auth_id = env["authority_id"]
    product = env["products"]["Laptop 40k"]
    
    r = await tc.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id, "input": "Buy Laptop 40k", "authority_id": auth_id
    })
    assert r.status_code == 200
    run_id = r.json()["id"]
    
    # Execute create_cart tool (which triggers a Gate decision that uses Risk!)
    r = await exec_tool(tc, env, run_id, "create_cart", {})
    assert r.status_code == 200
    
    # Some agent runtime endpoints don't return 'action_id' cleanly.
    # Let's get the risk assessments directly for this run.
    r = await tc.get(f"/api/v1/risk/assessments?agent_id={agent_id}")
    assert r.status_code == 200
    assessments = r.json()
    
    # Filter for this run
    run_assessments = [a for a in assessments if a["agent_run_id"] == run_id]
    assert len(run_assessments) > 0
    
    assessment = run_assessments[0]
    assert assessment["agent_id"] == agent_id
    assert assessment["risk_level"] in ["LOW", "MEDIUM"]
    assert "risk_score" in assessment
    assert len(assessment["signals"]) > 0


async def test_B_elevated_risk_action(tc: HelperClient, env: dict):
    agent_id = env["agent_id"]
    auth_id = env["authority_id"]
    product = env["products"]["Laptop 120k"] # Exceeds 80k authority limit
    
    r = await tc.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id, "input": "Buy Laptop 120k", "authority_id": auth_id
    })
    assert r.status_code == 200
    run_id = r.json()["id"]
    
    r = await exec_tool(tc, env, run_id, "create_cart", {})
    assert r.status_code == 200
    cart_id = r.json()["output"]["cart_id"]
    
    # Trigger elevated risk (amount exceeds authority limit / approval threshold)
    r = await exec_tool(tc, env, run_id, "add_to_cart", {"cart_id": cart_id, "product_id": product["id"], "quantity": 1})
    assert r.status_code == 200
    
    r = await exec_tool(tc, env, run_id, "checkout", {"cart_id": cart_id})
    
    if r.status_code == 200:
        order_id = r.json()["output"]["order_id"]
        r = await exec_tool(tc, env, run_id, "pay_order", {"order_id": order_id})
        
    # Since amount is 120k and limit is 80k, Gate will BLOCK it or REVIEW it.
    assert r.status_code in [402, 403]
    
    r = await tc.get(f"/api/v1/risk/assessments?agent_id={agent_id}")
    run_assessments = [a for a in r.json() if a["agent_run_id"] == run_id]
    
    # The last assessment for this run (for the pay_order action) should be HIGH/CRITICAL
    assessment = run_assessments[0] # Order is descending by created_at
    assert assessment["risk_level"] in ["HIGH", "CRITICAL"]


async def test_C_risk_gate_integration(tc: HelperClient, env: dict):
    agent_id = env["agent_id"]
    auth_id = env["authority_id"]
    
    r = await tc.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id, "input": "Buy high risk", "authority_id": auth_id
    })
    run_id = r.json()["id"]
    
    # We query the Risk API endpoint manually to check integration
    req = {
        "agent_id": agent_id,
        "agent_run_id": run_id,
        "intent_id": env["intent_id"],
        "authority_id": auth_id,
        "transaction": {
            "amount": 9000000, # HIGH risk
            "currency": "INR"
        },
        "merchant_id": env["merchant_id"],
        "product_category": "electronics"
    }
    
    # Call risk directly and verify it is consumed correctly
    r = await tc.post("/api/v1/risk/evaluate?persist=true", json=req)
    assert r.status_code == 200
    assessment = r.json()
    
    assert assessment["risk_level"] in ["HIGH", "CRITICAL"]


async def test_D_risk_data_integrity(tc: HelperClient, env: dict):
    # Risk API cannot be overridden with fake risk values in the request payload
    agent_id = env["agent_id"]
    auth_id = env["authority_id"]
    
    req = {
        "agent_id": agent_id,
        "agent_run_id": f"run_{uuid.uuid4().hex}",
        "intent_id": env["intent_id"],
        "authority_id": auth_id,
        "transaction": {
            "amount": 5000000,
            "currency": "INR"
        },
        "risk_score": 0, # Maliciously trying to inject 0 risk
        "risk_level": "LOW"
    }
    
    r = await tc.post("/api/v1/risk/evaluate", json=req)
    assert r.status_code == 200 # It accepts the request but ignores the fields
    
    assessment = r.json()
    assert assessment["risk_score"] > 0 # Since it calculates properly, not 0 as requested


async def test_E_workspace_isolation(tc: HelperClient, tc_b: HelperClient, env: dict):
    r = await tc.get(f"/api/v1/risk/assessments?agent_id={env['agent_id']}")
    assessments = r.json()
    assert len(assessments) > 0
    risk_id = assessments[0]["id"]
    
    r2 = await tc_b.get(f"/api/v1/risk/assessments/{risk_id}")
    assert r2.status_code == 404


async def test_F_agent_lifecycle(tc: HelperClient, env: dict):
    agent_id = env["agent_id"]
    
    # Pause agent
    await tc.post(f"/api/v1/agents/{agent_id}/status", json={"status": "PAUSED"})
    
    r = await tc.post("/api/v1/agent-runtime/runs", json={
        "agent_id": agent_id, "input": "Buy Laptop 40k", "authority_id": env["authority_id"]
    })
    # Cannot create run if agent is paused
    assert r.status_code in [400, 403]
    
    # Restore agent
    await tc.post(f"/api/v1/agents/{agent_id}/status", json={"status": "ACTIVE"})


async def test_G_persistence(tc: HelperClient, env: dict):
    r = await tc.get(f"/api/v1/risk/assessments?limit=1")
    risk_id = r.json()[0]["id"]
    
    # Reload from DB
    r2 = await tc.get(f"/api/v1/risk/assessments/{risk_id}")
    assert r2.status_code == 200
    assessment = r2.json()
    
    assert assessment["id"] == risk_id
    assert "risk_score" in assessment


async def test_H_cross_system_consistency(tc: HelperClient, env: dict):
    agent_id = env["agent_id"]
    
    r = await tc.get(f"/api/v1/risk/assessments?agent_id={agent_id}&limit=10")
    assessments = r.json()
    
    for assessment in assessments:
        assert assessment["agent_id"] == agent_id
        if assessment["agent_run_id"] and not assessment["agent_run_id"].startswith("run_"):
            # run should exist
            run_r = await tc.get(f"/api/v1/agent-runtime/runs/{assessment['agent_run_id']}")
            assert run_r.status_code == 200
