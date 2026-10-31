import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.policy import PolicyStatus, PolicyType
from tests.test_api_workspaces import create_test_user_and_workspace
from app.models.workspace import WorkspaceRole

@pytest.fixture
async def owner_client(client: AsyncClient, db_session: AsyncSession):
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, "owner_policies@test.com", WorkspaceRole.OWNER)
    client.cookies.set("finshield_session", token)
    return client, ws_id

@pytest.fixture
async def member_client(client: AsyncClient, db_session: AsyncSession, owner_client):
    _, ws_id = owner_client
    # Add member to owner's workspace
    user_id, _, token = await create_test_user_and_workspace(db_session, "member_policies@test.com", WorkspaceRole.VIEWER, create_ws=False, join_ws_id=ws_id)
    # The member needs their own client instance to hold their cookies, not the global one
    # For tests, we can just create a new AsyncClient instance
    new_client = AsyncClient(transport=client._transport, base_url="http://test")
    new_client.cookies.set("finshield_session", token)
    return new_client, ws_id

@pytest.mark.asyncio
async def test_create_and_get_policy(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    policy_data = {
        "name": "Limit Shopping",
        "policy_type": "TRANSACTION_LIMIT",
        "conditions": {
            "transaction_amount": {"operator": "GT", "value": 50000}
        },
        "actions": {
            "decision": "REVIEW",
            "reason": "Exceeds 50K"
        }
    }
    
    # Create
    res = await client.post("/api/v1/policies", json=policy_data)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Limit Shopping"
    assert data["status"] == "DRAFT"
    assert data["policy_type"] == "TRANSACTION_LIMIT"
    policy_id = data["id"]
    
    # Get List
    res_list = await client.get("/api/v1/policies")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
    
    # Get Detail
    res_detail = await client.get(f"/api/v1/policies/{policy_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == policy_id

@pytest.mark.asyncio
async def test_update_and_delete_policy(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    policy_data = {
        "name": "Update Test",
        "policy_type": "MERCHANT"
    }
    res = await client.post("/api/v1/policies", json=policy_data)
    policy_id = res.json()["id"]
    
    # Update to ACTIVE
    res_update = await client.patch(f"/api/v1/policies/{policy_id}", json={"status": "ACTIVE"})
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "ACTIVE"
    
    # Delete (Archive)
    res_delete = await client.delete(f"/api/v1/policies/{policy_id}")
    assert res_delete.status_code == 204
    
    # Verify it doesn't show in list
    res_list = await client.get("/api/v1/policies")
    assert not any(p["id"] == policy_id for p in res_list.json())

@pytest.mark.asyncio
async def test_policy_evaluator(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    # Policy 1: BLOCK over 100K
    await client.post("/api/v1/policies", json={
        "name": "Block High Value",
        "policy_type": "TRANSACTION_LIMIT",
        "status": "ACTIVE",
        "priority": 100,
        "conditions": {"transaction_amount": {"operator": "GT", "value": 100000}},
        "actions": {"decision": "BLOCK", "reason": "Amount exceeds 100K"}
    })
    
    # Policy 2: REVIEW over 50K
    await client.post("/api/v1/policies", json={
        "name": "Review Medium Value",
        "policy_type": "APPROVAL",
        "status": "ACTIVE",
        "priority": 90,
        "conditions": {"transaction_amount": {"operator": "GT", "value": 50000}},
        "actions": {"decision": "REVIEW", "reason": "Amount exceeds 50K"}
    })
    
    # Evaluate 40K -> should be ALLOW
    res = await client.post("/api/v1/policies/evaluate", json={
        "agent_id": "test",
        "amount": 40000,
        "currency": "INR"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "ALLOW"
    assert len(data["matched_policies"]) == 0
    
    # Evaluate 60K -> should be REVIEW
    res = await client.post("/api/v1/policies/evaluate", json={
        "agent_id": "test",
        "amount": 60000,
        "currency": "INR"
    })
    data = res.json()
    assert data["decision"] == "REVIEW"
    assert len(data["matched_policies"]) == 1
    
    # Evaluate 120K    # Evaluate 120K
    res = await client.post("/api/v1/policies/evaluate", json={
        "agent_id": "test",
        "amount": 120000,
        "currency": "INR",
        "capabilities": []
    })
    # Precedence: BLOCK > REVIEW > ALLOW
    assert res.json()["decision"] == "BLOCK"
    assert any("Amount exceeds 100K" in r for r in res.json()["reasons"])

@pytest.mark.asyncio
async def test_member_cannot_mutate_policies(owner_client, member_client, db_session: AsyncSession):
    # Owner creates a policy
    owner, ws_id = owner_client
    res = await owner.post("/api/v1/policies", json={
        "name": "Owner Policy",
        "policy_type": "APPROVAL",
        "actions": {"decision": "REVIEW"}
    })
    assert res.status_code == 201
    policy_id = res.json()["id"]
    
    member, _ = member_client
    
    # Member attempts to create
    res_create = await member.post("/api/v1/policies", json={
        "name": "Member Policy",
        "policy_type": "APPROVAL",
        "actions": {"decision": "REVIEW"}
    })
    assert res_create.status_code == 403
    
    # Member attempts to update
    res_patch = await member.patch(f"/api/v1/policies/{policy_id}", json={"status": "ACTIVE"})
    assert res_patch.status_code == 403
    
    # Member attempts to delete
    res_delete = await member.delete(f"/api/v1/policies/{policy_id}")
    assert res_delete.status_code == 403
    
    # Member CAN evaluate policies (evaluation does not require OWNER/ADMIN)
    res_eval = await member.post("/api/v1/policies/evaluate", json={
        "agent_id": "test",
        "amount": 100,
        "currency": "INR",
        "capabilities": []
    })
    assert res_eval.status_code == 200
