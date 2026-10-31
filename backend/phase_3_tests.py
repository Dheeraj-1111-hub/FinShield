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
from app.models.gate import ApprovalStatus, DecisionResult, GateDecision, ApprovalRequest

from app.services.agent_runtime_service import AgentRuntimeService
from app.services.commerce_service import CommerceService
from app.core.security import get_password_hash
from app.schemas.execution_context import ExecutionContext

logger = logging.getLogger(__name__)

async def setup_db():
    engine = create_async_engine('sqlite+aiosqlite:///./finshield.db')
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return async_session

async def get_workspace(db):
    result = await db.execute(select(Workspace).limit(1))
    return result.scalar_one_or_none()

async def create_agent(db, workspace_id, status=AgentStatus.ACTIVE):
    agent_id = f"agt_{uuid.uuid4().hex[:8]}"
    agent = Agent(
        id=agent_id,
        workspace_id=workspace_id,
        name="Test Agent",
        description="Phase 3 Test Agent",
        type="SHOPPING",
        status=status,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db.add(agent)
    await db.commit()
    return agent

async def create_authority(db, workspace_id, agent_id, limit=80000, threshold=None, status=AuthorityStatus.ACTIVE):
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:8]}",
        workspace_id=workspace_id,
        title="Buy a Server",
        intent_type="PURCHASE",
        natural_language_request="Buy a server",
        structured_constraints={"amount_limit": limit, "currency": "INR"},
        status=IntentStatus.ACTIVE,
        version=1
    )
    db.add(intent)
    await db.commit()

    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:8]}",
        workspace_id=workspace_id,
        agent_id=agent_id,
        intent_id=intent.id,
        monetary_limit=limit,
        approval_threshold=threshold,
        currency="INR",
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        status=status,
        version=1
    )
    db.add(authority)
    await db.commit()
    return authority

async def find_product(db, workspace_id):
    ctx = ExecutionContext(is_human=False, is_agent=True, agent_id="test")
    # Using CommerceService directly just to get product info for test setup
    products = await CommerceService.list_products(db, workspace_id)
    for p in products:
        if "Quantum" in p.name:
            return p.id, p.price
    return None, None

async def test_golden_path():
    async_session = await setup_db()
    async with async_session() as db:
        ws = await get_workspace(db)
        agent = await create_agent(db, ws.id)
        auth = await create_authority(db, ws.id, agent.id, limit=80000)
        
        run = await AgentRuntimeService.create_run(db, ws.id, agent.id, "Buy server", authority_id=auth.id)
        
        product_id, price = await find_product(db, ws.id)
        
        try:
            act1 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "create_cart", {})
            cart_id = act1.output.get("cart_id")
            
            act2 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1})
            
            act3 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "checkout", {"cart_id": cart_id})
            order_id = act3.output.get("order_id")
            
            act4 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "pay_order", {"order_id": order_id})
            print("Golden Path: PASS")
        except Exception as e:
            print(f"Golden Path: FAIL - {e}")

async def test_review_path():
    async_session = await setup_db()
    async with async_session() as db:
        ws = await get_workspace(db)
        agent = await create_agent(db, ws.id)
        # Approval threshold is 10k, so 75k server should trigger REVIEW
        auth = await create_authority(db, ws.id, agent.id, limit=80000, threshold=10000)
        
        run = await AgentRuntimeService.create_run(db, ws.id, agent.id, "Buy server", authority_id=auth.id)
        product_id, price = await find_product(db, ws.id)
        
        act1 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "create_cart", {})
        cart_id = act1.output.get("cart_id")
        
        # add_to_cart doesn't have an amount so gate allows it.
        await AgentRuntimeService.execute_action(db, ws.id, run.id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1})
        
        try:
            # Checkout hydrates the amount, which triggers REVIEW (402)
            await AgentRuntimeService.execute_action(db, ws.id, run.id, "checkout", {"cart_id": cart_id})
            print("Review Path: FAIL - Expected 402 exception for review on checkout")
            return
        except Exception as e:
            if "402" in str(e):
                # Approve it
                stmt = select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run.id)
                appr_res = await db.execute(stmt)
                approval = appr_res.scalar_one_or_none()
                if not approval:
                    print("Review Path: FAIL - No approval request created")
                    return
                approval.status = ApprovalStatus.APPROVED
                await db.commit()
                
                # Try again (revalidation)
                try:
                    await AgentRuntimeService.execute_action(db, ws.id, run.id, "checkout", {"cart_id": cart_id})
                    print("Review Path: PASS")
                except Exception as e2:
                    print(f"Review Path: FAIL on revalidation - {e2}")
            else:
                print(f"Review Path: FAIL - Expected 402, got {e}")

async def test_block_path():
    async_session = await setup_db()
    async with async_session() as db:
        ws = await get_workspace(db)
        agent = await create_agent(db, ws.id)
        # Limit is 10k, so 75k server should trigger BLOCK (AUTHORITY_EXCEEDED)
        auth = await create_authority(db, ws.id, agent.id, limit=10000)
        
        run = await AgentRuntimeService.create_run(db, ws.id, agent.id, "Buy server", authority_id=auth.id)
        product_id, price = await find_product(db, ws.id)
        
        act1 = await AgentRuntimeService.execute_action(db, ws.id, run.id, "create_cart", {})
        cart_id = act1.output.get("cart_id")
        
        await AgentRuntimeService.execute_action(db, ws.id, run.id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1})
        
        try:
            # Checkout hydrates the amount, which exceeds limit and triggers BLOCK (403)
            await AgentRuntimeService.execute_action(db, ws.id, run.id, "checkout", {"cart_id": cart_id})
            print("Block Path: FAIL - Action was not blocked")
        except Exception as e:
            if "403" in str(e) and "blocked" in str(e).lower():
                print("Block Path: PASS")
            else:
                print(f"Block Path: FAIL - Expected Gate block, got {e}")

async def test_bypass_path():
    async_session = await setup_db()
    async with async_session() as db:
        ws = await get_workspace(db)
        agent = await create_agent(db, ws.id)
        
        from app.schemas.commerce import CartCreate
        ctx = ExecutionContext(is_human=False, is_agent=True, agent_id=agent.id, is_agent_runtime=False)
        
        try:
            # Should fail because is_agent_runtime=False and no decision token
            await CommerceService.create_cart(db, ws.id, CartCreate(agent_id=agent.id, currency="USD"), ctx)
            print("Bypass Path: FAIL - Agent directly bypassed gate without runtime.")
        except Exception as e:
            if "403" in str(e) and "Agents must execute via AgentRuntimeService" in str(e):
                print("Bypass Path: PASS")
            else:
                print(f"Bypass Path: FAIL - Expected 403 Runtime requirement, got {e}")

async def test_revoked_agent():
    async_session = await setup_db()
    async with async_session() as db:
        ws = await get_workspace(db)
        agent = await create_agent(db, ws.id, status=AgentStatus.REVOKED)
        auth = await create_authority(db, ws.id, agent.id, limit=80000)
        
        try:
            await AgentRuntimeService.create_run(db, ws.id, agent.id, "Buy server", authority_id=auth.id)
            print("Revocation Path: FAIL - Run created for revoked agent")
        except Exception as e:
            if "403" in str(e) and "Cannot execute runs for agent in AgentStatus.REVOKED state" in str(e):
                print("Revocation Path: PASS")
            else:
                print(f"Revocation Path: FAIL - {e}")

async def run_all():
    print("--- Running Golden Path ---")
    await test_golden_path()
    print("--- Running Review Path ---")
    await test_review_path()
    print("--- Running Block Path ---")
    await test_block_path()
    print("--- Running Bypass Path ---")
    await test_bypass_path()
    print("--- Running Revocation Path ---")
    await test_revoked_agent()

if __name__ == '__main__':
    asyncio.run(run_all())
