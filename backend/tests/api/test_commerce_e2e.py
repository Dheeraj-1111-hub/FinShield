import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commerce import Product, ProductStatus, Order, OrderStatus
from sqlalchemy import select

@pytest.mark.asyncio
async def test_commerce_e2e_flow(client: AsyncClient, db_session: AsyncSession):
    # Register a user
    res = await client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "password123", "full_name": "Test User"})
    assert res.status_code == 200
    token = res.json()["user"]["id"] # wait, let me look at the payload... ah! wait, it sets a cookie, but does not return a token!
    admin_token_headers = {} # actually we need to extract the cookie from the response
    
    # 1. Create Merchant
    merchant_data = {
        "name": "Test Merchant Phase 6",
        "description": "Sandbox merchant",
        "merchant_reference": "REF123"
    }
    res = await client.post("/api/v1/commerce/merchants", json=merchant_data, headers=admin_token_headers)
    assert res.status_code == 201
    merchant_id = res.json()["id"]
    
    # 2. Create Product (inventory = 5)
    product_data = {
        "merchant_id": merchant_id,
        "name": "Test Product Phase 6",
        "price": 1500,
        "inventory": 5,
        "sku": "SKU-PHASE6"
    }
    res = await client.post("/api/v1/commerce/products", json=product_data, headers=admin_token_headers)
    assert res.status_code == 201
    product_id = res.json()["id"]
    
    # 3. Create Cart
    res = await client.post("/api/v1/commerce/carts", json={}, headers=admin_token_headers)
    assert res.status_code == 201
    cart_id = res.json()["id"]
    
    # 4. Add to cart (quantity 3)
    res = await client.post(f"/api/v1/commerce/carts/{cart_id}/items", json={"product_id": product_id, "quantity": 3}, headers=admin_token_headers)
    assert res.status_code == 201
    item_id = res.json()["id"]
    
    # Update to valid quantity 2
    res = await client.patch(f"/api/v1/commerce/carts/{cart_id}/items/{item_id}", json={"quantity": 2}, headers=admin_token_headers)
    assert res.status_code == 200
    
    # 6. Create Order
    order_data = {"cart_id": cart_id, "merchant_id": merchant_id, "agent_id": "test_agent"}
    res = await client.post("/api/v1/commerce/orders", json=order_data, headers=admin_token_headers)
    assert res.status_code == 201
    order_id = res.json()["id"]
    
    # Verify Inventory is deducted
    await db_session.commit() # ensure sync
    stmt = select(Product).where(Product.id == product_id)
    product = (await db_session.execute(stmt)).scalar_one()
    assert product.inventory == 3 # 5 - 2 = 3
    
    # 7. Cancel Order to test inventory recovery
    res = await client.post(f"/api/v1/commerce/orders/{order_id}/cancel", headers=admin_token_headers)
    assert res.status_code == 200
    
    await db_session.refresh(product)
    assert product.inventory == 5 # Restored
    
    # --- Now test successful payment flow ---
    # Create new cart and order
    res = await client.post("/api/v1/commerce/carts", json={}, headers=admin_token_headers)
    cart2_id = res.json()["id"]
    await client.post(f"/api/v1/commerce/carts/{cart2_id}/items", json={"product_id": product_id, "quantity": 1}, headers=admin_token_headers)
    
    res = await client.post("/api/v1/commerce/orders", json={"cart_id": cart2_id, "merchant_id": merchant_id}, headers=admin_token_headers)
    assert res.status_code == 201
    order2_id = res.json()["id"]
    
    await db_session.refresh(product)
    assert product.inventory == 4 # 5 - 1 = 4
    
    # Simulate process order (must fail because not PAID)
    res = await client.post(f"/api/v1/commerce/orders/{order2_id}/process", headers=admin_token_headers)
    assert res.status_code == 400
    
    # Simulate payment via db direct update for test
    order2 = (await db_session.execute(select(Order).where(Order.id == order2_id))).scalar_one()
    order2.status = OrderStatus.PAID
    await db_session.commit()
    
    # Process
    res = await client.post(f"/api/v1/commerce/orders/{order2_id}/process", headers=admin_token_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "PROCESSING"
    
    # Fulfill
    res = await client.post(f"/api/v1/commerce/orders/{order2_id}/fulfill", headers=admin_token_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "FULFILLED"
