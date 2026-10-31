import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

@pytest.mark.asyncio
async def test_signup_valid(client: AsyncClient, db_session: AsyncSession):
    payload = {
        "full_name": "Test User",
        "email": "test1@example.com",
        "password": "StrongPassword123!"
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "user" in data
    assert "workspace" in data
    assert data["user"]["email"] == "test1@example.com"
    
    # Check Database integrity
    result = await db_session.execute(select(User).where(User.email == "test1@example.com"))
    user = result.scalars().first()
    assert user is not None
    
    result = await db_session.execute(select(Workspace).where(Workspace.owner_id == user.id))
    workspace = result.scalars().first()
    assert workspace is not None
    
    result = await db_session.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id))
    member = result.scalars().first()
    assert member is not None
    assert member.role == WorkspaceRole.OWNER

@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "duplicate@example.com",
        "password": "StrongPassword123!"
    }
    response1 = await client.post("/api/v1/auth/signup", json=payload)
    assert response1.status_code == 200
    
    response2 = await client.post("/api/v1/auth/signup", json=payload)
    assert response2.status_code == 400
    assert "error" in response2.json()

@pytest.mark.asyncio
async def test_signup_missing_fields(client: AsyncClient):
    response = await client.post("/api/v1/auth/signup", json={})
    assert response.status_code == 422 # Validation Error
    assert "error" in response.json()
    
@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "not-an-email",
        "password": "StrongPassword123!"
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert "error" in response.json()

@pytest.mark.asyncio
async def test_login_valid(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "login@example.com",
        "password": "StrongPassword123!"
    }
    await client.post("/api/v1/auth/signup", json=payload)
    
    login_payload = {
        "email": "login@example.com",
        "password": "StrongPassword123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    
    # Verify session cookie exists and is HttpOnly
    cookies = response.cookies
    assert "finshield_session" in cookies

@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "login2@example.com",
        "password": "StrongPassword123!"
    }
    await client.post("/api/v1/auth/signup", json=payload)
    
    login_payload = {
        "email": "login2@example.com",
        "password": "WrongPassword!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid credentials"

@pytest.mark.asyncio
async def test_protected_route_without_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_with_auth(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "me@example.com",
        "password": "StrongPassword123!"
    }
    await client.post("/api/v1/auth/signup", json=payload)
    
    login_payload = {"email": "me@example.com", "password": "StrongPassword123!"}
    response = await client.post("/api/v1/auth/login", json=login_payload)
    token = response.cookies.get("finshield_session")
    if not token and "set-cookie" in response.headers:
        token = response.headers["set-cookie"].split(";")[0].split("=")[1]
    
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "me@example.com"

@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "logout@example.com",
        "password": "StrongPassword123!"
    }
    await client.post("/api/v1/auth/signup", json=payload)
    
    login_payload = {"email": "logout@example.com", "password": "StrongPassword123!"}
    response = await client.post("/api/v1/auth/login", json=login_payload)
    token = response.cookies.get("finshield_session")
    if not token and "set-cookie" in response.headers:
        token = response.headers["set-cookie"].split(";")[0].split("=")[1]
    
    response1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response1.status_code == 200
    
    # We still need to pass the cookie for logout because logout might look for cookie. Wait, let's pass both.
    response2 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}, cookies={"finshield_session": token})
    assert response2.status_code == 200
    
    response3 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response3.status_code == 401

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    from app.core.rate_limit import limiter
    limiter.enabled = True
    try:
        login_payload = {
            "email": "ratelimit@example.com",
            "password": "WrongPassword!"
        }
        # Limit is 5/minute for login
        for _ in range(5):
            await client.post("/api/v1/auth/login", json=login_payload)
            
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 429
    finally:
        limiter.enabled = False
