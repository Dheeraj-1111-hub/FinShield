import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent import AgentType, AgentStatus
from tests.test_api_workspaces import create_test_user_and_workspace
from app.models.workspace import WorkspaceRole

@pytest.fixture
async def owner_client(client: AsyncClient, db_session: AsyncSession):
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, "owner_agents@test.com", WorkspaceRole.OWNER)
    client.cookies.set("finshield_session", token)
    return client, ws_id

@pytest.mark.asyncio
async def test_create_agent(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {
        "name": "Test Shopping Agent",
        "description": "An autonomous shopping assistant",
        "type": "SHOPPING",
        "capabilities": ["SEARCH_PRODUCTS", "CREATE_CART"],
        "max_transaction_amount": 10000,
        "currency": "USD"
    }
    
    response = await client.post("/api/v1/agents", json=agent_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Shopping Agent"
    assert data["type"] == "SHOPPING"
    assert data["status"] == "DRAFT"
    assert "SEARCH_PRODUCTS" in data["capabilities"]

@pytest.mark.asyncio
async def test_get_agents(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {
        "name": "Test Shopping Agent",
        "type": "SHOPPING"
    }
    await client.post("/api/v1/agents", json=agent_data)
    
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Shopping Agent"

@pytest.mark.asyncio
async def test_update_agent_status(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {
        "name": "Test Shopping Agent",
        "type": "SHOPPING"
    }
    create_response = await client.post("/api/v1/agents", json=agent_data)
    agent_id = create_response.json()["id"]
    
    status_data = {
        "status": "ACTIVE"
    }
    response = await client.post(f"/api/v1/agents/{agent_id}/status", json=status_data)
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

@pytest.mark.asyncio
async def test_invalid_status_transition(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {
        "name": "Test Shopping Agent",
        "type": "SHOPPING"
    }
    create_response = await client.post("/api/v1/agents", json=agent_data)
    agent_id = create_response.json()["id"]
    
    # Trying to go from DRAFT to PAUSED is invalid
    status_data = {
        "status": "PAUSED"
    }
    response = await client.post(f"/api/v1/agents/{agent_id}/status", json=status_data)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_update_agent(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {"name": "Test Shopping Agent", "type": "SHOPPING"}
    create_res = await client.post("/api/v1/agents", json=agent_data)
    agent_id = create_res.json()["id"]
    
    update_data = {
        "description": "Updated description",
        "capabilities": ["SEARCH_PRODUCTS"],
        "max_transaction_amount": 5000
    }
    res = await client.patch(f"/api/v1/agents/{agent_id}", json=update_data)
    assert res.status_code == 200
    
    data = res.json()
    assert data["description"] == "Updated description"
    assert data["capabilities"] == ["SEARCH_PRODUCTS"]
    assert data["max_transaction_amount"] == 5000

@pytest.mark.asyncio
async def test_credentials_management(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {"name": "Test Agent", "type": "SHOPPING"}
    create_res = await client.post("/api/v1/agents", json=agent_data)
    agent_id = create_res.json()["id"]
    
    cred_data = {"name": "Production Key"}
    res = await client.post(f"/api/v1/agents/{agent_id}/credentials", json=cred_data)
    assert res.status_code == 201
    
    cred = res.json()
    assert cred["name"] == "Production Key"
    assert "client_secret" in cred
    cred_id = cred["id"]
    
    list_res = await client.get(f"/api/v1/agents/{agent_id}/credentials")
    assert list_res.status_code == 200
    creds_list = list_res.json()
    assert len(creds_list) == 1
    assert "client_secret" not in creds_list[0]
    
    del_res = await client.delete(f"/api/v1/agents/{agent_id}/credentials/{cred_id}")
    assert del_res.status_code == 204
    
    list_res2 = await client.get(f"/api/v1/agents/{agent_id}/credentials")
    assert list_res2.json()[0]["status"] == "REVOKED"

@pytest.mark.asyncio
async def test_agent_activity(owner_client, db_session: AsyncSession):
    client, ws_id = owner_client
    
    agent_data = {"name": "Audit Test Agent", "type": "FINANCE"}
    create_res = await client.post("/api/v1/agents", json=agent_data)
    agent_id = create_res.json()["id"]
    
    status_data = {"status": "ACTIVE"}
    await client.post(f"/api/v1/agents/{agent_id}/status", json=status_data)
    
    res = await client.get(f"/api/v1/agents/{agent_id}/activity")
    assert res.status_code == 200
    
    activities = res.json()
    assert len(activities) >= 2
    actions = [a["action"] for a in activities]
    assert "CREATED" in actions
    assert "STATUS_CHANGED" in actions
