import asyncio
from httpx import AsyncClient
import uuid
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from app.models.commerce import Merchant, Order, OrderStatus
from datetime import datetime, timezone, timedelta

async def run():
    async with AsyncSessionLocal() as db_session:
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
            user_id=user.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OWNER
        )
        db_session.add(member)
        
        token = generate_session_token()
        session = Session(
            id=f"sess_{uuid.uuid4().hex}",
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db_session.add(session)
        
        merchant = Merchant(
            id=f"merch_{uuid.uuid4().hex[:16]}",
            workspace_id=workspace.id,
            name="Test Merchant",
            status="ACTIVE"
        )
        db_session.add(merchant)
        
        order = Order(
            id=f"ord_{uuid.uuid4().hex[:16]}",
            workspace_id=workspace.id,
            merchant_id=merchant.id,
            cart_id=f"crt_{uuid.uuid4().hex[:16]}",
            status=OrderStatus.PENDING_PAYMENT,
            subtotal=2499900,
            total=2499900,
            currency="INR"
        )
        db_session.add(order)
        await db_session.commit()

        headers = {"Cookie": f"finshield_session={token}"}

    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_create = await client.post(
            "/api/v1/payments/intents",
            headers=headers,
            json={
                "payment_intent_id": f"pi_{uuid.uuid4().hex}",
                "idempotency_key": f"idem_{uuid.uuid4().hex}",
                "order_id": order.id,
                "amount": 1, 
                "currency": "USD" 
            }
        )
        print("STATUS:", resp_create.status_code)
        try:
            print("BODY:", resp_create.json())
        except Exception as e:
            print("BODY ERROR:", e)
            print("TEXT:", resp_create.text)

if __name__ == "__main__":
    asyncio.run(run())
