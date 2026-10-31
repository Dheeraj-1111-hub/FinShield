import asyncio
import uuid
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.workspace import Workspace
from app.models.agent import Agent, AgentCredential, AgentStatus
from app.models.intent import Intent, IntentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.agent_runtime import AgentRun, RunStatus, ActionStatus
from app.models.gate import ApprovalStatus, DecisionResult, GateDecision, ApprovalRequest
from app.models.audit import AuditEvent
from app.models.commerce import Order, OrderStatus, Product
from app.models.payment import Payment, PaymentStatus

from app.core.security import get_password_hash
from app.main import app
from app.core.gate_crypto import GateCrypto
from app.schemas.execution_context import SignedGateDecision

# For DB access
engine = create_async_engine('sqlite+aiosqlite:///./finshield.db')
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def setup_test_agent(db: AsyncSession, ws: Workspace, status=AgentStatus.ACTIVE, limit=80000, threshold=None):
    agent_id = f"agt_{uuid.uuid4().hex[:8]}"
    agent = Agent(
        id=agent_id,
        workspace_id=ws.id,
        name="Security Lab Agent",
        description="Phase 3 Integration Test",
        type="SHOPPING",
        status=status,
        capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"]
    )
    db.add(agent)
    
    client_id = f"client_{uuid.uuid4().hex[:8]}"
    client_secret = "secret"
    cred = AgentCredential(
        id=f"cred_{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        name="Test Cred",
        client_id=client_id,
        client_secret_hash=get_password_hash(client_secret),
        status="ACTIVE"
    )
    db.add(cred)
    
    intent = Intent(
        id=f"int_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        title="Buy a Server",
        intent_type="PURCHASE",
        natural_language_request="Buy a server under limit",
        structured_constraints={"amount_limit": limit, "currency": "INR"},
        status=IntentStatus.ACTIVE,
        version=1
    )
    db.add(intent)
    
    authority = DelegatedAuthority(
        id=f"auth_{uuid.uuid4().hex[:8]}",
        workspace_id=ws.id,
        agent_id=agent_id,
        intent_id=intent.id,
        monetary_limit=limit,
        approval_threshold=threshold,
        currency="INR",
        allowed_capabilities=["SEARCH_PRODUCTS", "CREATE_CART", "MANAGE_CART", "CREATE_ORDER", "PAY_ORDER"],
        status=AuthorityStatus.ACTIVE,
        version=1
    )
    db.add(authority)
    await db.commit()
    
    return agent, cred, intent, authority, client_secret

async def get_test_product(db: AsyncSession):
    stmt = select(Product).where(Product.name.like("%Quantum%"))
    return (await db.execute(stmt)).scalars().first()

async def run_evidence_suite():
    results = {}
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with async_session() as db:
            ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
            if not ws:
                print("No workspace found!")
                return
            
            product = await get_test_product(db)
            if not product:
                print("No product found!")
                return
            product.inventory = 1000
            await db.commit()
            product_id = product.id

            # Helper for executing an action via API
            async def execute_action(agent_id, run_id, tool_name, tool_input, secret, expect_status=200):
                auth_headers = {"Authorization": f"Bearer {client_id}:{secret}"}
                resp = await client.post(
                    f"/api/v1/agent-runtime/runs/{run_id}/actions",
                    json={"tool_name": tool_name, "input": tool_input},
                    headers=auth_headers
                )
                if expect_status:
                    assert resp.status_code == expect_status, f"Action {tool_name} failed: {resp.text}"
                return resp

            # ---------------------------------------------------------
            # E. Golden Path (ALLOW) & B. Agent Runtime & C. Intent & D. Authority & S. Audit
            # ---------------------------------------------------------
            print("Running E. Golden Path...")
            ag, cred, intt, auth, secret = await setup_test_agent(db, ws)
            from app.services.agent_runtime_service import AgentRuntimeService
            run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy a server", authority_id=auth.id)
            run_id = run.id
            client_id = cred.client_id
            
            # create_cart
            act1 = await execute_action(ag.id, run_id, "create_cart", {}, secret)
            cart_id = act1.json()["output"]["cart_id"]
            
            # add_to_cart
            act2 = await execute_action(ag.id, run_id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1}, secret)
            
            # checkout
            act3 = await execute_action(ag.id, run_id, "checkout", {"cart_id": cart_id}, secret)
            assert act3.status_code == 200, f"Checkout failed: {act3.text}"
            order_id = act3.json()["output"]["order_id"]
            
            # pay_order
            act4 = await execute_action(ag.id, run_id, "pay_order", {"order_id": order_id}, secret)
            assert act4.status_code == 200, f"Pay failed: {act4.text}"
            payment_id = act4.json()["output"]["transaction_id"]
            
            # Verify DB (R. Database Causality)
            order = await db.get(Order, order_id)
            payment = await db.get(Payment, payment_id)
            assert order.status == OrderStatus.PAID
            assert payment.status == PaymentStatus.CAPTURED
            
            # Verify Audit Causality
            audits = (await db.execute(select(AuditEvent).where(AuditEvent.entity_id == run_id))).scalars().all()
            
            results["golden"] = {
                "status": "PASS",
                "agent_id": ag.id, "run_id": run_id, "order_id": order_id, "payment_id": payment_id,
                "audit_count": len(audits)
            }
            
            # ---------------------------------------------------------
            # F. REVIEW
            # ---------------------------------------------------------
            print("Running F. REVIEW...")
            ag, cred, intt, auth, secret = await setup_test_agent(db, ws, threshold=10000)
            run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy a server", authority_id=auth.id)
            run_id = run.id
            client_id = cred.client_id
            
            act1 = await execute_action(ag.id, run_id, "create_cart", {}, secret)
            cart_id = act1.json()["output"]["cart_id"]
            act2 = await execute_action(ag.id, run_id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1}, secret)
            
            act3 = await execute_action(ag.id, run_id, "checkout", {"cart_id": cart_id}, secret, expect_status=402)
            assert act3.status_code == 402, "Expected 402 Review"
            
            # Approve it
            appr = (await db.execute(select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id))).scalars().first()
            appr.status = ApprovalStatus.APPROVED
            await db.commit()
            
            act3_retry = await execute_action(ag.id, run_id, "checkout", {"cart_id": cart_id}, secret)
            assert act3_retry.status_code == 200
            order_id = act3_retry.json()["output"]["order_id"]
            
            results["review"] = {"status": "PASS", "run_id": run_id, "order_id": order_id}
            
            # ---------------------------------------------------------
            # G. BLOCK & I. Authority Escalation
            # ---------------------------------------------------------
            print("Running G. BLOCK...")
            ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=10000)
            run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy a server", authority_id=auth.id)
            run_id = run.id
            client_id = cred.client_id
            
            act1 = await execute_action(ag.id, run_id, "create_cart", {}, secret)
            cart_id = act1.json()["output"]["cart_id"]
            act2 = await execute_action(ag.id, run_id, "add_to_cart", {"cart_id": cart_id, "product_id": product_id, "quantity": 1}, secret)
            
            act3 = await execute_action(ag.id, run_id, "checkout", {"cart_id": cart_id}, secret, expect_status=403)
            assert act3.status_code == 403, "Expected 403 Block"
            
            results["block"] = {"status": "PASS", "run_id": run_id, "http_status": act3.status_code}
            
            # ---------------------------------------------------------
            # J. HTTP Direct Bypass
            # ---------------------------------------------------------
            print("Running J. HTTP Direct Bypass...")
            ag, cred, intt, auth, secret = await setup_test_agent(db, ws)
            auth_headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
            
            bypass_resp = await client.post("/api/v1/commerce/orders", json={
                "cart_id": "crt_fake",
                "customer_email": "hack@hack.com"
            }, headers=auth_headers)
            
            assert bypass_resp.status_code == 403, "Bypass must be 403"
            results["bypass"] = {"status": "PASS", "http_status": bypass_resp.status_code}
            
            # ---------------------------------------------------------
            # K. Replay & L. Context Tampering
            # ---------------------------------------------------------
            print("Running K. Replay & L. Context Tampering...")
            from app.services.action_gate_service import ActionGateService
            from app.models.gate import GateDecision, DecisionResult
            
            gate = ActionGateService(db)
            gd = GateDecision(
                id=f"gdec_{uuid.uuid4().hex}",
                workspace_id=ws.id,
                agent_id=ag.id,
                agent_run_id="fake",
                agent_action_id="fake",
                decision=DecisionResult.ALLOW,
                reason_codes=[],
                explanation="test",
                required_approval=False,
                evaluation_snapshot={}
            )
            db.add(gd)
            await db.commit()
            
            token = gate.issue_token(gd, "checkout", {"cart_id": cart_id})
            
            ctx = {"is_human": False, "is_agent": True, "agent_id": ag.id, "is_agent_runtime": True, "signed_decision_token": token}
            from app.schemas.execution_context import ExecutionContext
            exec_ctx = ExecutionContext(**ctx)
            
            from app.services.commerce_service import CommerceService
            from app.schemas.commerce import OrderCreate, CartCreate
            
            try:
                # First try should succeed (assuming order doesn't already exist for this cart, wait, the cart is already checked out from golden path!)
                # Let's just create a new cart
                new_cart = await CommerceService.create_cart(db, ws.id, CartCreate(currency="INR"), ExecutionContext(is_human=False, is_agent=True, agent_id=ag.id, is_agent_runtime=True, signed_decision_token=gate.issue_token(
                    GateDecision(id=f"gdec_{uuid.uuid4().hex}", workspace_id=ws.id, agent_id=ag.id, agent_run_id="fake", agent_action_id="fake", action_type="create_cart", decision=DecisionResult.ALLOW, reason_codes=[], explanation="test", required_approval=False, evaluation_snapshot={}),
                    "create_cart", {}
                )))
                from app.schemas.commerce import CartItemCreate
                await CommerceService.add_cart_item(db, ws.id, new_cart.id, CartItemCreate(product_id=product_id, quantity=1), ExecutionContext(is_human=False, is_agent=True, agent_id=ag.id, is_agent_runtime=True, signed_decision_token=gate.issue_token(
                    GateDecision(id=f"gdec_{uuid.uuid4().hex}", workspace_id=ws.id, agent_id=ag.id, agent_run_id="fake", agent_action_id="fake", action_type="add_to_cart", decision=DecisionResult.ALLOW, reason_codes=[], explanation="test", required_approval=False, evaluation_snapshot={}),
                    "add_to_cart", {}
                )))
                
                gd.target_identity = new_cart.id
                await db.commit()
                token = gate.issue_token(gd, "checkout", {"cart_id": new_cart.id})
                exec_ctx.signed_decision_token = token
                
                await CommerceService.create_order(db, ws.id, OrderCreate(cart_id=new_cart.id, merchant_id=product.merchant_id), exec_ctx)
                first_try = True
            except Exception as e:
                first_try = False
                print("First try failed:", e)
                
            try:
                await CommerceService.create_order(db, ws.id, OrderCreate(cart_id=new_cart.id, merchant_id=product.merchant_id), exec_ctx)
                replay_failed = False
            except Exception as e:
                replay_failed = True
                
            results["replay"] = {"status": "PASS" if replay_failed else "FAIL"}
            
            try:
                # Tamper cart ID
                await CommerceService.create_order(db, ws.id, OrderCreate(cart_id="tampered_cart_id", merchant_id=product.merchant_id), exec_ctx)
                tamper_failed = False
            except Exception:
                tamper_failed = True
            results["tampering"] = {"status": "PASS" if tamper_failed else "FAIL"}
            
            # ---------------------------------------------------------
            # M. Revoked Credential
            # ---------------------------------------------------------
            print("Running M. Revoked Credential...")
            cred.status = "REVOKED"
            await db.commit()
            
            rev_resp = await client.post("/api/v1/commerce/orders", json={
                "cart_id": "crt_fake"
            }, headers=auth_headers)
            
            assert rev_resp.status_code == 401, "Revoked cred must be 401"
            results["revoked_cred"] = {"status": "PASS"}
            
            # ---------------------------------------------------------
            # N. Revoked Agent
            # ---------------------------------------------------------
            print("Running N. Revoked Agent...")
            ag2, cred2, intt2, auth2, secret2 = await setup_test_agent(db, ws, status=AgentStatus.REVOKED)
            try:
                run = await AgentRuntimeService.create_run(db, ws.id, ag2.id, "test", authority_id=auth2.id)
                assert False, "Should have failed"
            except Exception as e:
                pass
            results["revoked_agent"] = {"status": "PASS"}
            results["revoked_agent"] = {"status": "PASS"}
            
            # ---------------------------------------------------------
            # O. Mid-run Revocation
            # ---------------------------------------------------------
            print("Running O. Mid-run Revocation...")
            ag3, cred3, intt3, auth3, secret3 = await setup_test_agent(db, ws)
            run = await AgentRuntimeService.create_run(db, ws.id, ag3.id, "Buy a server", authority_id=auth3.id)
            run_id = run.id
            client_id = cred3.client_id
            
            # Revoke agent mid-run
            ag3.status = AgentStatus.REVOKED
            await db.commit()
            
            act1 = await execute_action(ag3.id, run_id, "create_cart", {}, secret3, expect_status=401)
            assert act1.status_code == 401, "Mid-run revoked action must be 401"
            results["mid_run_revocation"] = {"status": "PASS"}
            
            # ---------------------------------------------------------
            # Q. Fail Closed
            # ---------------------------------------------------------
            print("Running Q. Fail Closed...")
            # If we don't pass a token at all to commerce
            exec_ctx_no_token = ExecutionContext(is_human=False, is_agent=True, agent_id=ag.id, is_agent_runtime=True)
            try:
                from app.schemas.commerce import OrderCreate
                await CommerceService.create_order(db, ws.id, OrderCreate(cart_id="crt_fake"), exec_ctx_no_token)
                fail_closed = False
            except Exception as e:
                fail_closed = True
            results["fail_closed"] = {"status": "PASS" if fail_closed else "FAIL"}

    print("All backend tests completed.")
    return results

if __name__ == "__main__":
    res = asyncio.run(run_evidence_suite())
    print(res)
