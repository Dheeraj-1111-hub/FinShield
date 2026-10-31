import asyncio
import uuid
from app.db.database import AsyncSessionLocal
from app.models.commerce import Merchant, Product
from sqlalchemy import select

async def seed_data():
    async with AsyncSessionLocal() as db:
        # Assuming there is a default workspace, let's just get the first one
        from app.models.workspace import Workspace
        result = await db.execute(select(Workspace))
        workspace = result.scalars().first()
        if not workspace:
            print("No workspace found. Please log in to the frontend first to create a default workspace.")
            return

        workspace_id = workspace.id

        # Check if merchant exists
        merch_res = await db.execute(select(Merchant).where(Merchant.workspace_id == workspace_id))
        merchant = merch_res.scalars().first()
        
        if not merchant:
            merchant = Merchant(
                id=f"merch_{uuid.uuid4().hex[:16]}",
                workspace_id=workspace_id,
                name="Sandbox Merchant Corp",
                description="Test merchant for Finshield",
                status="ACTIVE"
            )
            db.add(merchant)
            await db.commit()
            print(f"Created Merchant: {merchant.name}")
        
        # Add some products
        prod_res = await db.execute(select(Product).where(Product.merchant_id == merchant.id))
        existing_products = prod_res.scalars().all()
        
        if len(existing_products) == 0:
            products = [
                Product(
                    id=f"prod_{uuid.uuid4().hex[:16]}",
                    merchant_id=merchant.id,
                    name="Standard Office Laptop",
                    description="Standard laptop under 80k",
                    category="Hardware",
                    price=75000, # 75,000
                    currency="INR",
                    inventory=999
                ),
                Product(
                    id=f"prod_{uuid.uuid4().hex[:16]}",
                    merchant_id=merchant.id,
                    name="CyberShield Quantum Server",
                    description="Quantum level security server",
                    category="Hardware",
                    price=75000, # 75,000
                    currency="INR",
                    inventory=10
                ),
                Product(
                    id=f"prod_{uuid.uuid4().hex[:16]}",
                    merchant_id=merchant.id,
                    name="Premium Developer Laptop",
                    description="High performance laptop over 100k",
                    category="Hardware",
                    price=120000, # 120,000
                    currency="INR",
                    inventory=15
                ),
                Product(
                    id=f"prod_{uuid.uuid4().hex[:16]}",
                    merchant_id=merchant.id,
                    name="SaaS Subscription - GitHub",
                    description="Copilot and Actions billing.",
                    category="Software",
                    price=15000, # 15,000
                    currency="INR",
                    inventory=999
                )
            ]
            db.add_all(products)
            await db.commit()
            print(f"Created {len(products)} products.")
        else:
            print("Products already exist.")

if __name__ == "__main__":
    asyncio.run(seed_data())
