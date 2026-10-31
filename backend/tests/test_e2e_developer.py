import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def e2e_context(client: AsyncClient, db_session: AsyncSession):
    email = f"e2e_dev_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "E2E Developer"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}

@pytest.mark.asyncio
async def test_developer_api_flow(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.6.1 - Developer API E2E
    Test creating an API credential, and verifying it works for authentication.
    """
    ctx = e2e_context
    ws_id = ctx["ws_id"]

    # 1. Create API Client App
    app_res = await client.post("/api/v1/developers/clients", params={"workspace_id": ws_id}, json={
        "name": "Test App",
        "description": "Integration test app"
    }, cookies=ctx["cookies"], headers=ctx["headers"])
    assert app_res.status_code == 201
    client_id = app_res.json()["id"]

    # 2. Create API Credential
    cred_res = await client.post("/api/v1/developers/credentials", params={"workspace_id": ws_id}, json={
        "api_client_id": client_id,
        "name": "Production Key",
        "scopes": ["*"]
    }, cookies=ctx["cookies"], headers=ctx["headers"])
    assert cred_res.status_code == 201
    secret = cred_res.json()["secret"]

    # 3. Authenticate using Bearer Token (API Key)
    api_headers = {
        "Authorization": f"Bearer {secret}",
        "X-Workspace-ID": ws_id
    }
    
    # Let's try fetching policies with the API key
    async with AsyncClient(transport=client._transport, base_url="http://test") as anon_client:
        policy_res = await anon_client.get("/api/v1/policies", headers=api_headers)
        assert policy_res.status_code == 200

    # 4. Revoke Credential
    cred_id = cred_res.json()["id"]
    revoke_res = await client.post(f"/api/v1/developers/credentials/{cred_id}/revoke", params={"workspace_id": ws_id}, cookies=ctx["cookies"], headers=ctx["headers"])
    assert revoke_res.status_code == 204

    # 5. Verify Revoked Key Fails
    async with AsyncClient(transport=client._transport, base_url="http://test") as anon_client:
        policy_res_fail = await anon_client.get("/api/v1/policies", headers=api_headers)
        assert policy_res_fail.status_code == 401

@pytest.mark.asyncio
async def test_webhook_endpoints(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.6.2 - Webhooks E2E
    Test creating webhook endpoints and listing them.
    """
    ctx = e2e_context
    ws_id = ctx["ws_id"]

    # 1. Create Webhook
    wh_res = await client.post("/api/v1/developers/webhooks", params={"workspace_id": ws_id}, json={
        "url": "https://webhook.site/test-123",
        "description": "Test Webhook",
        "subscribed_events": ["POLICY_CREATED", "AGENT_RUN_COMPLETED"]
    }, cookies=ctx["cookies"], headers=ctx["headers"])
    
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    # 2. List Webhooks
    list_res = await client.get("/api/v1/developers/webhooks", params={"workspace_id": ws_id}, cookies=ctx["cookies"], headers=ctx["headers"])
    assert list_res.status_code == 200
    assert any(wh["id"] == wh_id for wh in list_res.json())
