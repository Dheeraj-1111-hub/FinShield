import pytest
import asyncio
from httpx import AsyncClient, Cookies
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

import uuid

@pytest.fixture
async def e2e_context(client: AsyncClient, db_session: AsyncSession):
    email = f"e2e_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "E2E User Edge Cases"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}

@pytest.fixture
async def sec_user_client(client: AsyncClient, db_session: AsyncSession):
    email = f"attacker_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Attacker User"
    })
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}


@pytest.mark.asyncio
async def test_security_idor_sweep(client: AsyncClient, db_session: AsyncSession, e2e_context, sec_user_client):
    """
    17.5.1 - IDOR Sweep
    Ensure `sec_user_client` cannot access or mutate resources in `e2e_context` workspace.
    """
    ctx_victim = e2e_context
    ctx_attacker = sec_user_client

    # 1. Victim creates an agent
    agent_res = await client.post("/api/v1/agents", json={
        "name": "Victim Agent",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "PAY_ORDER"]
    }, cookies=ctx_victim["cookies"], headers=ctx_victim["headers"])
    agent_id = agent_res.json()["id"]
    
    # 2. Attacker attempts to GET victim agent
    get_res = await client.get(f"/api/v1/agents/{agent_id}", cookies=ctx_attacker["cookies"], headers=ctx_attacker["headers"])
    assert get_res.status_code == 404  # Not Found or 403 Forbidden is acceptable for IDOR protection
    
    # 3. Attacker attempts to UPDATE victim agent
    upd_res = await client.patch(f"/api/v1/agents/{agent_id}", json={
        "name": "Hacked Agent"
    }, cookies=ctx_attacker["cookies"], headers=ctx_attacker["headers"])
    assert upd_res.status_code in [403, 404]




@pytest.mark.asyncio
async def test_security_audit_integrity(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.5.2 - Audit Forensic Chain & Integrity
    Verify complete event chains and integrity hashing.
    """
    ctx = e2e_context
    
    # 1. Trigger an event (create policy)
    policy_res = await client.post("/api/v1/policies", json={
        "name": "Audit Test Policy",
        "policy_type": "TRANSACTION_LIMIT",
        "actions": {"action": "BLOCK"},
        "conditions": {"max_amount": 9999}
    }, cookies=ctx["cookies"], headers=ctx["headers"])
    assert policy_res.status_code == 201
    
    # 2. Check audit logs exist
    audit_res = await client.get("/api/v1/audit/", cookies=ctx["cookies"], headers=ctx["headers"])
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) > 0
    
    # Find the specific event
    policy_event = next((e for e in events if e["event_type"] == "POLICY_CREATED"), None)
    assert policy_event is not None
    
    # 3. Verify Integrity API (Happy Path)
    verify_res = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] == True
    
    # 4. Mutate DB directly to tamper with audit log
    event_id = policy_event["id"]
    await db_session.execute(text(f"UPDATE audit_events SET payload = '{{\"tampered\": true}}' WHERE id = '{event_id}'"))
    await db_session.commit()
    
    # 5. Verify Integrity API (Tampered Path)
    verify_res2 = await client.post("/api/v1/audit/integrity/verify", cookies=ctx["cookies"], headers=ctx["headers"])
    assert verify_res2.status_code == 200
    assert verify_res2.json()["valid"] == False
    assert any(link["event_id"] == event_id for link in verify_res2.json()["broken_links"])

