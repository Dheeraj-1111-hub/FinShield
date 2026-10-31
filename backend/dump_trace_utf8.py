import asyncio
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.database import AsyncSessionLocal, engine
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.gate import GateDecision, ApprovalRequest
from app.models.commerce import Order, Cart, Product
from app.models.payment import Payment
from app.models.authority import DelegatedAuthority
from app.models.intent import Intent
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check():
    async with AsyncSessionLocal() as db:
        print("=== RUN run_0757cd04ba9e4fa4 ===")
        stmt = select(AgentRun).options(selectinload(AgentRun.actions)).where(AgentRun.id == 'run_0757cd04ba9e4fa4')
        run = (await db.execute(stmt)).scalar_one_or_none()
        if run:
            print(f"ID: {run.id}, Status: {run.status}, Agent: {run.agent_id}, AuthID: {run.authority_id}, Session: {run.session_id}")
            print(f"Input: {repr(run.input)}")
            print(f"Output: {repr(run.output)}")
            print(f"CreatedAt: {run.created_at}, CompletedAt: {run.completed_at}")
            print(f"Actions ({len(run.actions)}):")
            for a in run.actions:
                print(f"  Action: {a.id}, Seq: {a.sequence_number}, Tool: {a.tool_name}, Status: {a.status}")
                print(f"    Input: {a.input}")
                print(f"    Output: {a.output}")
                print(f"    Alignment: {a.alignment_result}")
                print(f"    Error: {a.error_message}")
        
        if run and run.authority_id:
            auth = await db.get(DelegatedAuthority, run.authority_id)
            if auth:
                print(f"\nLinked Authority: {auth.id}, Limit: {auth.monetary_limit}, Currency: {auth.currency}, ApprovalThresh: {auth.approval_threshold}, IntentID: {auth.intent_id}")
                if auth.intent_id:
                    intent = await db.get(Intent, auth.intent_id)
                    if intent:
                        print(f"Linked Intent: {intent.id}, Type: {intent.intent_type}, Constraints: {intent.structured_constraints}")

        print("\n=== ALL ORDERS ===")
        stmt_orders = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
        orders = (await db.execute(stmt_orders)).scalars().all()
        for o in orders:
            print(f"Order {o.id}: Status={o.status}, Total={o.total}, Subtotal={o.subtotal}, Currency={o.currency}, CartID={o.cart_id}, PaymentID={o.payment_id}, AgentID={o.agent_id}, CreatedAt={o.created_at}")
            for item in o.items:
                print(f"  Item: ProductID={item.product_id}, Name={item.product_name_snapshot}, UnitPrice={item.unit_price_at_order}, Total={item.total}")

        print("\n=== ALL PAYMENTS ===")
        stmt_pay = select(Payment).order_by(Payment.created_at.desc())
        payments = (await db.execute(stmt_pay)).scalars().all()
        for p in payments:
            print(f"Payment {p.id}: Status={p.status}, Amount={p.amount}, Currency={p.currency}, OrderID={p.order_id}, AgentID={p.agent_id}, Metadata={p.metadata_}, CreatedAt={p.created_at}")

        print("\n=== RECENT GATE DECISIONS (last 10) ===")
        stmt_dec = select(GateDecision).order_by(GateDecision.created_at.desc()).limit(10)
        decs = (await db.execute(stmt_dec)).scalars().all()
        for d in decs:
            print(f"GateDecision {d.id}: Decision={d.decision}, RequiredApproval={d.required_approval}, RunID={d.agent_run_id}, ActionID={d.agent_action_id}, ApprovalID={d.approval_id}, CreatedAt={d.created_at}")
            print(f"  Snapshot: {d.evaluation_snapshot}")
            print(f"  Reasons: {d.reason_codes}, Explanation: {d.explanation}")

        print("\n=== ALL APPROVAL REQUESTS ===")
        stmt_appr = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
        apprs = (await db.execute(stmt_appr)).scalars().all()
        for ap in apprs:
            print(f"Approval {ap.id}: Status={ap.status}, RunID={ap.agent_run_id}, ActionID={ap.agent_action_id}, Amount={ap.amount}, Currency={ap.currency}, Reason={ap.reason}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
