import asyncio
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.workspace import Workspace
from app.models.agent import Agent, AgentCredential, AgentStatus
from app.models.intent import Intent, IntentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.agent_runtime import AgentRun, RunStatus, ActionStatus
from app.models.gate import ApprovalStatus, DecisionResult
from app.models.payment import PaymentStatus

from app.services.agent_runtime_service import AgentRuntimeService
from app.services.approval_service import ApprovalService
from app.services.commerce_service import CommerceService
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

async def setup_db():
    engine = create_async_engine('sqlite+aiosqlite:///./finshield.db')
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return async_session

async def run_golden_path():
    async_session = await setup_db()
    async with async_session() as db:
        # Step 0: create or get workspace
        result = await db.execute(select(Workspace).limit(1))
        workspace = result.scalar_one_or_none()
        if not workspace:
            print("No workspace found!")
            return
            
        workspace_id = workspace.id

        # Step 1: Real Agent Identity
        agent_id = f"agt_{uuid.uuid4().hex[:8]}"
        agent = Agent(
            id=agent_id,
            workspace_id=workspace_id,
            name="Reference Agent",
            description="Deterministic Phase 3 Agent",
            type="SHOPPING",
            status=AgentStatus.ACTIVE,
            capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
        )
        db.add(agent)
        
        cred = AgentCredential(
            id=f"cred_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            name="Test Credential",
            client_id=f"client_{uuid.uuid4().hex[:8]}",
            client_secret_hash=get_password_hash("secret"),
            status="ACTIVE"
        )
        db.add(cred)
        await db.commit()

        # Step 2: Real Intent
        intent = Intent(
            id=f"int_{uuid.uuid4().hex[:8]}",
            workspace_id=workspace_id,
            title="Buy a CyberShield Quantum Server",
            intent_type="PURCHASE",
            natural_language_request="Buy a CyberShield Quantum Server for less than INR 80,000.",
            structured_constraints={"amount_limit": 80000, "currency": "INR"},
            status=IntentStatus.ACTIVE,
            version=1
        )
        db.add(intent)
        await db.commit()

        # Step 3: Real Delegated Authority
        authority = DelegatedAuthority(
            id=f"auth_{uuid.uuid4().hex[:8]}",
            workspace_id=workspace_id,
            agent_id=agent_id,
            intent_id=intent.id,
            monetary_limit=80000,
            currency="INR",
            allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
            status=AuthorityStatus.ACTIVE,
            version=1
        )
        db.add(authority)
        await db.commit()

        # Step 4: Real Agent Run & Golden Purchase
        run = await AgentRuntimeService.create_run(
            db, workspace_id, agent_id, 
            "Buy a CyberShield Quantum Server for less than INR 80,000.", 
            trigger_type="API", 
            authority_id=authority.id
        )

        print(f"Agent Run Created: {run.id}")

        # Deterministic steps
        try:
            # 1. Search products
            act1 = await AgentRuntimeService.execute_action(db, workspace_id, run.id, "search_products", {"query": "CyberShield Quantum Server"})
            results = act1.output.get("results", [])
            if not results:
                print("No product found")
                return
            product_id = results[0]["id"]
            price = results[0]["price"]
            print(f"Found product: {product_id} @ {price}")

            # 2. Create cart
            act2 = await AgentRuntimeService.execute_action(db, workspace_id, run.id, "create_cart", {})
            cart_id = act2.output.get("cart_id")
            print(f"Created cart: {cart_id}")

            # 3. Add to cart
            act3 = await AgentRuntimeService.execute_action(db, workspace_id, run.id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1})
            print(f"Added to cart")

            # 4. Checkout
            act4 = await AgentRuntimeService.execute_action(db, workspace_id, run.id, "checkout", {"cart_id": cart_id})
            order_id = act4.output.get("order_id")
            print(f"Checked out. Order: {order_id}")

            # 5. Pay order
            act5 = await AgentRuntimeService.execute_action(db, workspace_id, run.id, "pay_order", {"order_id": order_id})
            print(f"Paid order: {act5.output}")

            await AgentRuntimeService.finish_run(db, workspace_id, run.id, "Task completed successfully.")
            
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == '__main__':
    asyncio.run(run_golden_path())
