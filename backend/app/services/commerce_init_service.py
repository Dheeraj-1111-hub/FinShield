import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.commerce import Merchant, Product, MerchantStatus, ProductStatus

async def initialize_sandbox_catalog(db: AsyncSession, workspace_id: str) -> None:
    """Idempotently ensure a sandbox merchant and products exist for the given workspace.
    Mirrors seed_commerce.py data but safe for repeated calls.
    """
    # Ensure merchant exists
    result = await db.execute(select(Merchant).where(Merchant.workspace_id == workspace_id))
    merchant = result.scalars().first()
    if not merchant:
        merchant = Merchant(
            id=f"merch_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            name="Global Tech Sandbox",
            description="Sandbox electronics merchant",
            status=MerchantStatus.ACTIVE,
        )
        db.add(merchant)
        await db.flush()  # get merchant.id for FK
    # Ensure products exist for this merchant
    prod_res = await db.execute(select(Product).where(Product.merchant_id == merchant.id))
    existing = prod_res.scalars().all()
    if not existing:
        products = [
            Product(
                merchant_id=merchant.id,
                name="Budget Laptop 15-inch",
                description="Reliable laptop for everyday use.",
                category="electronics",
                price=150,
                currency="INR",
                inventory=50,
                status=ProductStatus.ACTIVE,
            ),
            Product(
                merchant_id=merchant.id,
                name="Gaming Laptop Pro",
                description="High performance gaming laptop.",
                category="electronics",
                price=85000,
                currency="INR",
                inventory=10,
                status=ProductStatus.ACTIVE,
            ),
            Product(
                merchant_id=merchant.id,
                name="Wireless Mouse",
                description="Ergonomic wireless mouse.",
                category="accessories",
                price=999,
                currency="INR",
                inventory=100,
                status=ProductStatus.ACTIVE,
            ),
        ]
        db.add_all(products)
    # Caller will commit transaction
