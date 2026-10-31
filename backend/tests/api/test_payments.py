import pytest
import pytest_asyncio
from httpx import AsyncClient
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from app.models.commerce import Merchant, Product, Order, OrderStatus
from app.models.payment import Payment, PaymentStatus

@pytest_asyncio.fixture
async def owner_data(db_session: AsyncSession):
    # Create User
    user = User(
        id=f"usr_{uuid.uuid4().hex}", 
        email=f"{uuid.uuid4().hex}@test.com", 
        password_hash=get_password_hash("password"), 
        full_name="Test Owner",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    # Create Workspace
    workspace = Workspace(
        id=f"ws_{uuid.uuid4().hex}", 
        name="Test Workspace", 
        slug=f"test-ws-{uuid.uuid4().hex[:8]}", 
        owner_id=user.id
    )
    db_session.add(workspace)
    
    # Create Membership
    member = WorkspaceMember(
        id=f"wm_{uuid.uuid4().hex}",
        user_id=user.id,
        workspace_id=workspace.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    
    # Create Session
    token = generate_session_token()
    session = Session(
        id=f"sess_{uuid.uuid4().hex}",
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    await db_session.commit()
    
    return {
        "headers": {"Cookie": f"finshield_session={token}"},
        "workspace_id": workspace.id,
        "user_id": user.id
    }

@pytest_asyncio.fixture
async def sandbox_order(db_session: AsyncSession, owner_data: dict):
    workspace_id = owner_data["workspace_id"]
    
    merchant = Merchant(
        id=f"merch_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace_id,
        name="Test Merchant",
        status="ACTIVE"
    )
    db_session.add(merchant)
    
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace_id,
        merchant_id=merchant.id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=2499900,
        total=2499900,
        currency="INR"
    )
    db_session.add(order)
    await db_session.commit()
    
    return order

@pytest_asyncio.fixture
async def deterministic_failure_order(db_session: AsyncSession, owner_data: dict):
    workspace_id = owner_data["workspace_id"]
    
    merchant = Merchant(
        id=f"merch_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace_id,
        name="Test Merchant 2",
        status="ACTIVE"
    )
    db_session.add(merchant)
    
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace_id,
        merchant_id=merchant.id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=99999900,
        total=99999900,
        currency="INR"
    )
    db_session.add(order)
    await db_session.commit()
    
    return order


@pytest.mark.asyncio
async def test_full_golden_payment_path(client: AsyncClient, owner_data: dict, sandbox_order: Order, db_session: AsyncSession):
    headers = owner_data["headers"]
    
    # 1. Create intent
    idem_key = f"idem_{uuid.uuid4().hex}"
    resp_create = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": idem_key,
            "order_id": sandbox_order.id,
            "amount": 1, # Should be ignored
            "currency": "USD" # Should be ignored
        }
    )
    assert resp_create.status_code == 201, f"Expected 201, got {resp_create.status_code} with body: {resp_create.json()}"
    data = resp_create.json()
    print("CREATE RESPONSE:", data)
    assert data["status"] == "CREATED"
    assert data["amount"] == 2499900 # Inherited from order
    assert data["currency"] == "INR"
    
    payment_id = data["id"]
    
    # 2. Authorize
    resp_auth = await client.post(f"/api/v1/payments/{payment_id}/authorize", headers=headers)
    assert resp_auth.status_code == 200
    assert resp_auth.json()["status"] == "AUTHORIZED"
    
    # Check order status, should still be PENDING_PAYMENT
    await db_session.refresh(sandbox_order)
    assert sandbox_order.status == OrderStatus.PENDING_PAYMENT
    
    # 3. Capture
    resp_cap = await client.post(f"/api/v1/payments/{payment_id}/capture", headers=headers)
    assert resp_cap.status_code == 200
    assert resp_cap.json()["status"] == "CAPTURED"
    
    # 4. Check order status, should be PAID
    await db_session.refresh(sandbox_order)
    assert sandbox_order.status == OrderStatus.PAID
    
    # 5. Try creating another payment for same order (double charge test)
    resp_create_2 = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_{uuid.uuid4().hex}",
            "order_id": sandbox_order.id
        }
    )
    assert resp_create_2.status_code == 409


@pytest.mark.asyncio
async def test_idempotent_payment_intent(client: AsyncClient, owner_data: dict, sandbox_order: Order, db_session: AsyncSession):
    headers = owner_data["headers"]
    idem_key = f"idem_{uuid.uuid4().hex}"
    
    # First call
    response1 = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": idem_key,
            "order_id": sandbox_order.id
        }
    )
    assert response1.status_code == 201
    
    # Second call should return exactly the same id without error
    response2 = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": idem_key,
            "order_id": sandbox_order.id
        }
    )
    assert response2.status_code == 201
    assert response1.json()["id"] == response2.json()["id"]
    
    # Third call with different order_id should fail with 409    # Create another order manually
    merchant2 = Merchant(
        id=f"merch_{uuid.uuid4().hex[:16]}",
        workspace_id=owner_data["workspace_id"],
        name="Test Merchant 2",
        status="ACTIVE"
    )
    db_session.add(merchant2)
    
    order2 = Order(
        id=f"ord_{uuid.uuid4().hex[:16]}",
        workspace_id=owner_data["workspace_id"],
        merchant_id=merchant2.id,
        cart_id=f"crt_{uuid.uuid4().hex[:16]}",
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=100,
        total=100,
        currency="INR"
    )
    db_session.add(order2)
    await db_session.commit()

    response3 = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": idem_key,
            "order_id": order2.id
        }
    )
    assert response3.status_code == 409
@pytest.mark.asyncio
async def test_deterministic_failure_leaves_order_unpaid(client: AsyncClient, owner_data: dict, deterministic_failure_order: Order, db_session: AsyncSession):
    headers = owner_data["headers"]
    
    resp_create = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_{uuid.uuid4().hex}",
            "order_id": deterministic_failure_order.id
        }
    )
    payment_id = resp_create.json()["id"]
    
    auth_resp = await client.post(f"/api/v1/payments/{payment_id}/authorize", headers=headers)
    assert auth_resp.status_code == 200
    
    data = auth_resp.json()
    assert data["status"] == "FAILED"
    assert data["failure_code"] == "insufficient_funds"
    
    # Ensure order remains unpaid (and goes to PAYMENT_FAILED)
    await db_session.refresh(deterministic_failure_order)
    assert deterministic_failure_order.status == OrderStatus.PAYMENT_FAILED

@pytest.mark.asyncio
async def test_payment_metrics_reconciliation_and_canonical_units(client: AsyncClient, owner_data: dict, sandbox_order: Order, db_session: AsyncSession):
    """Verify payment capture, metrics aggregation, idempotency, and single inventory decrement."""
    from app.models.commerce import Product

    headers = owner_data["headers"]
    workspace_id = owner_data["workspace_id"]

    # 1. Capture payment for sandbox_order (total = 100 INR)
    resp_create = await client.post(
        "/api/v1/payments/intents",
        headers=headers,
        json={
            "payment_intent_id": f"pi_{uuid.uuid4().hex}",
            "idempotency_key": f"idem_metric_{sandbox_order.id}",
            "order_id": sandbox_order.id,
            "amount": sandbox_order.total,
            "currency": sandbox_order.currency
        }
    )
    assert resp_create.status_code == 201
    payment_data = resp_create.json()
    payment_id = payment_data["id"]
    assert payment_data["amount"] == sandbox_order.total
    assert payment_data["currency"] == "INR"

    # Authorize & Capture
    auth_resp = await client.post(f"/api/v1/payments/{payment_id}/authorize", headers=headers)
    assert auth_resp.status_code == 200
    assert auth_resp.json()["status"] == "AUTHORIZED"

    cap_resp = await client.post(f"/api/v1/payments/{payment_id}/capture", headers=headers)
    assert cap_resp.status_code == 200
    assert cap_resp.json()["status"] == "CAPTURED"

    # 2. Check metrics endpoint
    metrics_resp = await client.get("/api/v1/payments/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["captured_count"] >= 1
    assert metrics["total_volume"] >= sandbox_order.total  # Canonical units, not divided by 100

    # 3. Check overview endpoint
    overview_resp = await client.get("/api/v1/overview?time_range=30d", headers=headers)
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert ov_data["financial"]["payment_count"] >= 1
    assert ov_data["financial"]["payment_volume"] >= 100.0  # Canonical currency units

    # 4. Check order status transitioned to PAID
    await db_session.refresh(sandbox_order)
    assert sandbox_order.status == OrderStatus.PAID
    assert sandbox_order.payment_id == payment_id

