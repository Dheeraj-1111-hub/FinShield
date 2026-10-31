import asyncio
import json
from app.db.database import AsyncSessionLocal, engine
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.gate import GateDecision, ApprovalRequest
from app.models.commerce import Order, Cart, Product
from app.models.payment import Payment
from app.models.audit import AuditEvent
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def trace():
    async with AsyncSessionLocal() as db:
        print("=== 1. RUN run_0757cd04ba9e4fa4 ===")
        stmt = select(AgentRun).options(selectinload(AgentRun.actions)).where(AgentRun.id == 'run_0757cd04ba9e4fa4')
        run = (await db.execute(stmt)).scalar_one_or_none()
        if run:
            safe_input = (run.input or "").encode("ascii", "replace").decode("ascii")
            safe_output = (run.output or "").encode("ascii", "replace").decode("ascii")
            print(f"Run ID: {run.id}, Status: {run.status}, Agent: {run.agent_id}, Authority: {run.authority_id}")
            print(f"  Input: {safe_input}")
            print(f"  Output: {safe_output}")
            print(f"  CreatedAt: {run.created_at}, CompletedAt: {run.completed_at}")
            for a in run.actions:
                safe_err = (a.error_message or "").encode("ascii", "replace").decode("ascii")
                print(f"  Action: {a.id}, Seq: {a.sequence_number}, Tool: {a.tool_name}, Status: {a.status}")
                print(f"    Input: {a.input}")
                print(f"    Output: {a.output}")
                print(f"    Alignment: {a.alignment_result}, GateDec: {a.gate_decision_id if hasattr(a, 'gate_decision_id') else 'N/A'}, Error: {safe_err}")
        else:
            print("Run run_0757cd04ba9e4fa4 not found!")

        print("\n=== 2. ALL RECENT RUNS ===")
        stmt_runs = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(10)
        runs = (await db.execute(stmt_runs)).scalars().all()
        for r in runs:
            safe_inp = (r.input or "").encode("ascii", "replace").decode("ascii")
            print(f"Run: {r.id}, Status: {r.status}, CreatedAt: {r.created_at}, Input: {safe_inp}")

        print("\n=== 3. ORDERS ===")
        stmt_orders = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc()).limit(10)
        orders = (await db.execute(stmt_orders)).scalars().all()
        for o in orders:
            print(f"Order: {o.id}, Workspace: {o.workspace_id}, Status: {o.status}, Total: {o.total}, Currency: {o.currency}, CartID: {o.cart_id}, CreatedAt: {o.created_at}")
            for item in o.items:
                print(f"  Item: ProductID={item.product_id}, Name={item.product_name_snapshot}, Qty={item.quantity}, UnitPrice={item.unit_price_at_order}, Total={item.total}")

        print("\n=== 4. PAYMENTS ===")
        stmt_payments = select(Payment).order_by(Payment.created_at.desc()).limit(10)
        payments = (await db.execute(stmt_payments)).scalars().all()
        for p in payments:
            print(f"Payment: {p.id}, Workspace: {p.workspace_id}, OrderID: {p.order_id}, Status: {p.status}, Amount: {p.amount}, Currency: {p.currency}, Metadata: {p.metadata_}, CreatedAt: {p.created_at}")

        print("\n=== 5. GATE DECISIONS ===")
        stmt_decisions = select(GateDecision).order_by(GateDecision.created_at.desc()).limit(10)
        decs = (await db.execute(stmt_decisions)).scalars().all()
        for d in decs:
            print(f"GateDecision: {d.id}, Workspace: {d.workspace_id}, RunID: {d.agent_run_id}, ActionID: {d.agent_action_id}, Decision: {d.decision}, RequiredApproval: {d.required_approval}, ApprovalID: {d.approval_id}, CreatedAt: {d.created_at}")
            print(f"  Snapshot: {d.evaluation_snapshot}")
            print(f"  Reasons: {d.reason_codes}, Explanation: {d.explanation}")

        print("\n=== 6. APPROVAL REQUESTS ===")
        stmt_apprs = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(10)
        apprs = (await db.execute(stmt_apprs)).scalars().all()
        for ap in apprs:
            print(f"ApprovalRequest: {ap.id}, Workspace: {ap.workspace_id}, RunID: {ap.agent_run_id}, ActionID: {ap.agent_action_id}, GateDecisionID: {ap.gate_decision_id}, Status: {ap.status}, Amount: {ap.amount}, Currency: {ap.currency}, CreatedAt: {ap.created_at}")

        print("\n=== 7. AUDIT EVENTS ===")
        stmt_audit = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(15)
        audits = (await db.execute(stmt_audit)).scalars().all()
        for au in audits:
            print(f"AuditEvent: {au.id}, Type: {au.event_type}, Cat: {au.event_category}, Entity: {au.entity_type}/{au.entity_id}, CreatedAt: {au.created_at}")
            print(f"  Payload: {au.payload}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(trace())
