import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserStatus
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from app.models.session import Session
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.workspace_settings import WorkspaceSettings
from datetime import datetime, timedelta, timezone
import uuid

async def create_test_user_and_workspace(db_session, email="owner@test.com", role=WorkspaceRole.OWNER, create_ws=True, join_ws_id=None):
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        password_hash=get_password_hash("Password123!"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    token = generate_session_token()
    token_hash = hash_session_token(token)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    
    workspace_id = None
    if create_ws:
        workspace_id = str(uuid.uuid4())
        workspace = Workspace(
            id=workspace_id,
            name=f"{email}'s Workspace",
            slug=f"ws-{user_id[:8]}",
            owner_id=user_id
        )
        db_session.add(workspace)
    
    if join_ws_id or create_ws:
        target_ws_id = join_ws_id or workspace_id
        member = WorkspaceMember(
            id=str(uuid.uuid4()),
            workspace_id=target_ws_id,
            user_id=user_id,
            role=role
        )
        db_session.add(member)
        
    await db_session.commit()
    return user_id, workspace_id, token

@pytest.fixture
async def owner_client(client: AsyncClient, db_session: AsyncSession):
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, "owner@test.com", WorkspaceRole.OWNER)
    client.cookies.set("finshield_session", token)
    return client, ws_id

@pytest.fixture
async def member_client(client: AsyncClient, db_session: AsyncSession):
    # Create Owner first
    owner_user_id, ws_id, _ = await create_test_user_and_workspace(db_session, "owner2@test.com", WorkspaceRole.OWNER)
    
    # Create Member in the same workspace
    member_user_id, _, member_token = await create_test_user_and_workspace(db_session, "member@test.com", WorkspaceRole.VIEWER, create_ws=False, join_ws_id=ws_id)
    
    client2 = AsyncClient(transport=client._transport, base_url="http://test")
    client2.cookies.set("finshield_session", member_token)
    return client2, ws_id

@pytest.fixture
async def other_owner_client(client: AsyncClient, db_session: AsyncSession):
    user_id, ws_id, token = await create_test_user_and_workspace(db_session, "other@test.com", WorkspaceRole.OWNER)
    client3 = AsyncClient(transport=client._transport, base_url="http://test")
    client3.cookies.set("finshield_session", token)
    return client3, ws_id

@pytest.mark.asyncio
async def test_read_workspace(owner_client):
    client, ws_id = owner_client
    response = await client.get("/api/v1/workspaces/current")
    assert response.status_code == 200
    assert response.json()["workspace"]["id"] == ws_id

@pytest.mark.asyncio
async def test_update_workspace_as_owner(owner_client):
    client, ws_id = owner_client
    response = await client.patch("/api/v1/workspaces/current", json={"currency": "INR"})
    assert response.status_code == 200
    assert response.json()["workspace"]["currency"] == "INR"

@pytest.mark.asyncio
async def test_update_workspace_as_member_forbidden(member_client):
    client, ws_id = member_client
    # Member should not be able to patch workspace
    response = await client.patch("/api/v1/workspaces/current", json={"currency": "INR"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_read_settings(owner_client):
    client, ws_id = owner_client
    response = await client.get("/api/v1/workspaces/current/settings")
    assert response.status_code == 200
    assert response.json()["settings"]["risk_threshold"] == 80

@pytest.mark.asyncio
async def test_update_settings_valid(owner_client):
    client, ws_id = owner_client
    response = await client.patch("/api/v1/workspaces/current/settings", json={"risk_threshold": 90, "review_threshold": 80})
    assert response.status_code == 200
    assert response.json()["settings"]["risk_threshold"] == 90
    assert response.json()["settings"]["review_threshold"] == 80

@pytest.mark.asyncio
async def test_update_settings_validation_logic(owner_client):
    client, ws_id = owner_client
    # review_threshold must be < risk_threshold
    response = await client.patch("/api/v1/workspaces/current/settings", json={"risk_threshold": 80, "review_threshold": 90})
    assert response.status_code == 400
    assert "Review threshold must be less than risk threshold" in response.json()["error"]["message"]

@pytest.mark.asyncio
async def test_update_settings_concurrency(owner_client):
    client, ws_id = owner_client
    # Initial read
    response1 = await client.get("/api/v1/workspaces/current/settings")
    version1 = response1.json()["settings"]["version"]
    
    # First update
    response2 = await client.patch("/api/v1/workspaces/current/settings", json={"risk_threshold": 85, "version": version1})
    assert response2.status_code == 200
    version2 = response2.json()["settings"]["version"]
    assert version2 > version1
    
    # Try updating with old version
    response3 = await client.patch("/api/v1/workspaces/current/settings", json={"risk_threshold": 86, "version": version1})
    assert response3.status_code == 409
    assert "modified by another user" in response3.json()["error"]["message"]

@pytest.mark.asyncio
async def test_cross_workspace_isolation(owner_client, other_owner_client):
    client_a, ws_id_a = owner_client
    client_b, ws_id_b = other_owner_client
    
    # A updates their currency
    await client_a.patch("/api/v1/workspaces/current", json={"currency": "INR"})
    
    # B fetches theirs
    res_b = await client_b.get("/api/v1/workspaces/current")
    # It should not be INR (default is USD)
    assert res_b.json()["workspace"]["currency"] == "USD"
    
    # If the API takes a workspace_id in the URL in future, we would test that passing ws_id_a while logged in as B returns 403.
    # Currently, it relies on get_current_workspace dependency which intrinsically isolates.

@pytest.mark.asyncio
async def test_update_workspace_slug_valid(owner_client):
    client, ws_id = owner_client
    response = await client.patch("/api/v1/workspaces/current", json={"slug": "new-valid-slug"})
    assert response.status_code == 200
    assert response.json()["workspace"]["slug"] == "new-valid-slug"

@pytest.mark.asyncio
async def test_update_workspace_slug_invalid_formats(owner_client):
    client, ws_id = owner_client
    # Uppercase
    res1 = await client.patch("/api/v1/workspaces/current", json={"slug": "NewSlug"})
    assert res1.status_code == 400
    # Spaces
    res2 = await client.patch("/api/v1/workspaces/current", json={"slug": "new slug"})
    assert res2.status_code == 400
    # Special characters
    res3 = await client.patch("/api/v1/workspaces/current", json={"slug": "new-slug@#"})
    assert res3.status_code == 400

@pytest.mark.asyncio
async def test_update_workspace_slug_length(owner_client):
    client, ws_id = owner_client
    # Empty
    res1 = await client.patch("/api/v1/workspaces/current", json={"slug": ""})
    assert res1.status_code == 400
    # Too short
    res2 = await client.patch("/api/v1/workspaces/current", json={"slug": "a"})
    assert res2.status_code == 400
    # Too long (over 40 chars)
    res3 = await client.patch("/api/v1/workspaces/current", json={"slug": "a" * 41})
    assert res3.status_code == 400

@pytest.mark.asyncio
async def test_update_workspace_slug_duplicate(owner_client, other_owner_client):
    client_a, ws_id_a = owner_client
    client_b, ws_id_b = other_owner_client
    
    # A sets slug to 'target-slug'
    await client_a.patch("/api/v1/workspaces/current", json={"slug": "target-slug"})
    
    # B tries to set same slug
    res = await client_b.patch("/api/v1/workspaces/current", json={"slug": "target-slug"})
    assert res.status_code == 409
    assert "Workspace slug already exists" in res.json()["error"]["message"]

@pytest.mark.asyncio
async def test_update_workspace_slug_unauthorized(member_client):
    client, ws_id = member_client
    response = await client.patch("/api/v1/workspaces/current", json={"slug": "hacked-slug"})
    assert response.status_code == 403
