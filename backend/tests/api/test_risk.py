import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token

@pytest_asyncio.fixture
async def owner_headers(db_session: AsyncSession):
    user = User(
        id=f"usr_{uuid.uuid4().hex}", 
        email=f"{uuid.uuid4().hex}@test.com", 
        password_hash=get_password_hash("password"), 
        full_name="Test Owner",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    workspace = Workspace(
        id=f"ws_{uuid.uuid4().hex}", 
        name="Test Workspace", 
        slug=f"test-ws-{uuid.uuid4().hex[:8]}", 
        owner_id=user.id
    )
    db_session.add(workspace)
    
    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex}",
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    
    token = generate_session_token()
    session = Session(
        id=f"ses_{uuid.uuid4().hex}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    await db_session.commit()
    
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": workspace.id
    }

@pytest.mark.asyncio
async def test_evaluate_risk_deterministic(
    client: AsyncClient,
    owner_headers
):
    request_data = {
        "agent_id": "ag_123",
        "merchant_id": "m_new",
        "product_category": "ELECTRONICS",
        "transaction": {
            "amount": 50000,
            "currency": "INR"
        }
    }
    
    # Run evaluation 1
    response1 = await client.post("/api/v1/risk/evaluate?persist=true", json=request_data, headers=owner_headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    # Run evaluation 2
    response2 = await client.post("/api/v1/risk/evaluate?persist=false", json=request_data, headers=owner_headers)
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Assert determinism
    assert data1["risk_score"] == data2["risk_score"]
    assert data1["risk_level"] == data2["risk_level"]
    assert len(data1["signals"]) == len(data2["signals"])
    
    for s1, s2 in zip(data1["signals"], data2["signals"]):
        assert s1["signal_type"] == s2["signal_type"]
        assert s1["score"] == s2["score"]

@pytest.mark.asyncio
async def test_get_risk_summary(
    client: AsyncClient,
    owner_headers
):
    response = await client.get("/api/v1/risk/summary", headers=owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_assessments" in data
    assert "average_score" in data
