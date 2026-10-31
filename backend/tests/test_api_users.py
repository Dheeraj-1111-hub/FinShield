import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserStatus
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from app.models.session import Session
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from datetime import datetime, timedelta, timezone
import uuid

@pytest.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession):
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email="test_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    # Create session
    token = generate_session_token()
    token_hash = hash_session_token(token)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    
    # Create Workspace
    workspace_id = str(uuid.uuid4())
    workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        slug="test-workspace",
        owner_id=user_id
    )
    db_session.add(workspace)
    
    # Create WorkspaceMember
    member = WorkspaceMember(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    
    await db_session.commit()
    
    client.cookies.set("finshield_session", token)
    return client, user

@pytest.mark.asyncio
async def test_read_profile(auth_client):
    client, user = auth_client
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test_user@example.com"
    assert data["user"]["full_name"] == "Test User"

@pytest.mark.asyncio
async def test_update_profile_valid(auth_client):
    client, user = auth_client
    response = await client.patch("/api/v1/users/me", json={"full_name": "Sai Dheeraj"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["full_name"] == "Sai Dheeraj"
    
    # Re-fetch
    response2 = await client.get("/api/v1/users/me")
    assert response2.json()["user"]["full_name"] == "Sai Dheeraj"

@pytest.mark.asyncio
async def test_read_and_update_preferences(auth_client):
    client, user = auth_client
    # Read (should create default)
    response = await client.get("/api/v1/users/me/preferences")
    assert response.status_code == 200
    prefs = response.json()["preferences"]
    assert prefs["language"] == "en"
    
    response2 = await client.patch("/api/v1/users/me/preferences", json={"language": "fr", "timezone": "Europe/Paris"})
    assert response2.status_code == 200
    prefs2 = response2.json()["preferences"]
    assert prefs2["language"] == "fr"
    assert prefs2["timezone"] == "Europe/Paris"

@pytest.mark.asyncio
async def test_update_notification_preferences_valid(auth_client):
    client, _ = auth_client
    update_data = {
        "notification_preferences": {
            "txThreshold": 75000,
            "dailyThreshold": 300000,
            "security": {"critical_security": False}
        }
    }
    response = await client.patch("/api/v1/users/me/preferences", json=update_data)
    assert response.status_code == 200
    prefs = response.json()["preferences"]["notification_preferences"]
    assert prefs["txThreshold"] == 75000
    assert prefs["dailyThreshold"] == 300000
    assert prefs["security"]["critical_security"] is False
    
    # Verify persistence
    response2 = await client.get("/api/v1/users/me/preferences")
    prefs2 = response2.json()["preferences"]["notification_preferences"]
    assert prefs2["txThreshold"] == 75000
    assert prefs2["dailyThreshold"] == 300000

@pytest.mark.asyncio
async def test_update_notification_preferences_invalid_tx(auth_client):
    client, _ = auth_client
    update_data = {
        "notification_preferences": {
            "txThreshold": -100
        }
    }
    response = await client.patch("/api/v1/users/me/preferences", json=update_data)
    assert response.status_code == 400
    assert "Invalid Transaction Exceeds threshold" in response.json().get("detail", response.json().get("error", {}).get("message", ""))

@pytest.mark.asyncio
async def test_update_notification_preferences_invalid_daily(auth_client):
    client, _ = auth_client
    update_data = {
        "notification_preferences": {
            "dailyThreshold": "invalid"
        }
    }
    response = await client.patch("/api/v1/users/me/preferences", json=update_data)
    assert response.status_code == 400
    assert "Invalid Daily Agent Exposure threshold" in response.json().get("detail", response.json().get("error", {}).get("message", ""))
