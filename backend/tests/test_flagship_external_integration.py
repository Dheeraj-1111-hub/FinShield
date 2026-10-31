import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.developer import ApiClient, ApiCredential
from app.services.developer_auth import DeveloperAuthService

@pytest.fixture
async def flagship_workspace(db_session: AsyncSession):
    # Setup user and workspace
    from app.models.user import User
    from app.models.workspace import Workspace
    
    user = User(id=f"usr_{uuid.uuid4().hex}", email="flagship@finshield.com", full_name="Flagship Dev", password_hash="fakehash123")
    db_session.add(user)
    await db_session.commit()
    
    ws = Workspace(id=f"ws_{uuid.uuid4().hex}", name="Flagship Test Workspace", slug=f"flagship-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    db_session.add(ws)
    await db_session.commit()
    return ws

@pytest.fixture
async def developer_client_and_secret(db_session: AsyncSession, flagship_workspace):
    client_id = f"cli_{uuid.uuid4().hex}"
    client = ApiClient(id=client_id, workspace_id=flagship_workspace.id, name="Flagship Test Client")
    db_session.add(client)
    
    auth_svc = DeveloperAuthService(db_session)
    raw_secret, prefix, secret_hash = auth_svc.generate_api_key()
    
    cred = ApiCredential(
        api_client_id=client_id,
        workspace_id=flagship_workspace.id,
        name="Flagship Test Key",
        credential_prefix=prefix,
        secret_hash=secret_hash,
        scopes=["agents:write", "intents:write", "commerce:write", "payments:write"]
    )
    db_session.add(cred)
    await db_session.commit()
    
    return client_id, raw_secret

@pytest.mark.asyncio
async def test_flagship_external_integration(client: AsyncClient, db_session: AsyncSession, flagship_workspace, developer_client_and_secret):
    client_id, raw_secret = developer_client_and_secret
    headers = {"Authorization": f"Bearer {raw_secret}"}

    # 1. Create intent as developer
    intent_payload = {
        "title": "Purchase Test",
        "intent_type": "PURCHASE",
        "natural_language_request": "Test purchasing from external client",
        "structured_constraints": {
            "product": {
                "category": "TestItem"
            }
        }
    }
    resp = await client.post(f"/api/v1/intents?workspace_id={flagship_workspace.id}", json=intent_payload, headers=headers)
    # Note: If it hits 401, it means our dependency isn't on that route, or something else failed.
    # This test ensures we've integrated it correctly.
    assert resp.status_code in [200, 201], f"Failed to create intent: {resp.text}"
    
    # We can stop here for this test since it verifies the core requirement: 
    # external API client successfully making a protected request via the public API.
