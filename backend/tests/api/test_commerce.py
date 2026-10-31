import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commerce import Merchant, Product, Cart, CartItem, Order, OrderStatus
from app.models.payment import PaymentStatus
import uuid
from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token
from datetime import datetime, timezone, timedelta
import pytest_asyncio

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
    await db_session.commit()
    
    return {"Cookie": f"finshield_session={token}"}

@pytest.mark.asyncio
async def test_full_commerce_lifecycle(client: AsyncClient, db_session: AsyncSession, owner_headers: dict):
    # 1. Create a merchant
    response = await client.post("/api/v1/commerce/merchants", headers=owner_headers, json={
        "name": "Sandbox Electronics",
        "description": "Premium electronics store"
    })
    assert response.status_code == 201
    merchant_id = response.json()["id"]

    # 2. Create a product
    response = await client.post("/api/v1/commerce/products", headers=owner_headers, json={
        "merchant_id": merchant_id,
        "name": "Laptop Pro",
        "price": 75000,
        "inventory": 10
    })
    assert response.status_code == 201
    product_id = response.json()["id"]

    # 3. Create a cart
    response = await client.post("/api/v1/commerce/carts", headers=owner_headers, json={})
    assert response.status_code == 201
    cart_id = response.json()["id"]

    # 4. Add item to cart
    response = await client.post(f"/api/v1/commerce/carts/{cart_id}/items", headers=owner_headers, json={
        "product_id": product_id,
        "quantity": 1
    })
    assert response.status_code == 201
    assert response.json()["total"] == 75000

    # 5. Create order from cart
    response = await client.post("/api/v1/commerce/orders", headers=owner_headers, json={
        "cart_id": cart_id,
        "merchant_id": merchant_id
    })
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert response.json()["status"] == "PENDING_PAYMENT"
    assert response.json()["total"] == 75000

    # 6. Check price integrity (change product price, order should remain the same)
    # Since we don't have a product update endpoint yet, we'll manually change in db
    product = await db_session.get(Product, product_id)
    product.price = 95000
    await db_session.commit()

    # Re-fetch order
    response = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=owner_headers)
    assert response.status_code == 200
    order_data = response.json()
    assert order_data["total"] == 75000  # Stays original price
    assert order_data["items"][0]["unit_price_at_order"] == 75000

    # 7. Create Payment Intent and Capture it
    # First, create payment intent via the payment API
    response = await client.post("/api/v1/payments/intents", headers=owner_headers, json={
        "payment_intent_id": "pi_sandbox_test",
        "idempotency_key": "idem_12345",
        "amount": 75000,
        "currency": "INR",
        "order_id": order_id
    })
    assert response.status_code == 201
    payment_id = response.json()["id"]

    # Authorize
    response = await client.post(f"/api/v1/payments/{payment_id}/authorize", headers=owner_headers)
    assert response.status_code == 200

    # Capture
    response = await client.post(f"/api/v1/payments/{payment_id}/capture", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CAPTURED"

    # 8. Verify Order is PAID
    response = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert response.json()["payment_id"] == payment_id

@pytest.mark.asyncio
async def test_payment_failure_updates_order(client: AsyncClient, db_session: AsyncSession, owner_headers: dict):
    # Setup merchant, product, cart, order
    merchant_res = await client.post("/api/v1/commerce/merchants", headers=owner_headers, json={"name": "Test"})
    merchant_id = merchant_res.json()["id"]
    
    product_res = await client.post("/api/v1/commerce/products", headers=owner_headers, json={"merchant_id": merchant_id, "name": "Test", "price": 100, "inventory": 1})
    product_id = product_res.json()["id"]
    
    cart_res = await client.post("/api/v1/commerce/carts", headers=owner_headers, json={})
    cart_id = cart_res.json()["id"]
    
    await client.post(f"/api/v1/commerce/carts/{cart_id}/items", headers=owner_headers, json={"product_id": product_id, "quantity": 1})
    
    order_res = await client.post("/api/v1/commerce/orders", headers=owner_headers, json={"cart_id": cart_id, "merchant_id": merchant_id})
    order_id = order_res.json()["id"]

    # Create Payment for EXACTLY 99999900 which triggers failure in SandboxPaymentProcessor
    pay_res = await client.post("/api/v1/payments/intents", headers=owner_headers, json={
        "payment_intent_id": "pi_fail",
        "idempotency_key": "idem_fail",
        "amount": 99999900,
        "currency": "INR",
        "order_id": order_id
    })
    payment_id = pay_res.json()["id"]

    # Authorize will fail
    auth_res = await client.post(f"/api/v1/payments/{payment_id}/authorize", headers=owner_headers)
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "FAILED"

    # Verify Order is PAYMENT_FAILED
    order_check = await client.get(f"/api/v1/commerce/orders/{order_id}", headers=owner_headers)
    assert order_check.json()["status"] == "PAYMENT_FAILED"
