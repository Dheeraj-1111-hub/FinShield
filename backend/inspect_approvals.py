import asyncio
from sqlalchemy import select
from app.db.database import get_db
from app.models.gate import ApprovalRequest, GateDecision
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.commerce import Order, Cart, CartItem
from app.models.payment import Payment

async def inspect_approvals():
    async for db in get_db():
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.amount == 150)
            .order_by(ApprovalRequest.created_at.desc())
        )
        res = await db.execute(stmt)
        approvals = res.scalars().all()
        print(f"Total matching 150 approvals found: {len(approvals)}")
        for a in approvals:
            print("="*60)
            print(f"Approval ID: {a.id}")
            print(f"Status: {a.status}")
            print(f"Amount: {a.amount} {a.currency}")
            print(f"Reason: {a.reason}")
            print(f"Agent ID: {a.agent_id}")
            print(f"Run ID: {a.agent_run_id}")
            print(f"Action ID: {a.agent_action_id}")
            print(f"Gate Decision ID: {a.gate_decision_id}")
            print(f"Created At: {a.created_at}")
            print(f"Transaction Data: {a.transaction_data}")

            # Check action
            if a.agent_action_id:
                action = await db.get(AgentAction, a.agent_action_id)
                if action:
                    print(f"Action Tool: {action.tool_name}, Status: {action.status}, Input: {action.input}")
            
            # Check run
            if a.agent_run_id:
                run = await db.get(AgentRun, a.agent_run_id)
                if run:
                    print(f"Run Input: {run.input}, Status: {run.status}, Created At: {run.created_at}")
                    # All actions for this run
                    stmt_acts = select(AgentAction).where(AgentAction.run_id == run.id).order_by(AgentAction.sequence_number.asc())
                    res_acts = await db.execute(stmt_acts)
                    acts = res_acts.scalars().all()
                    print(f"Run Action Sequence ({len(acts)} actions):")
                    for act in acts:
                        print(f"   - seq={act.sequence_number} tool={act.tool_name} status={act.status} in={act.input}")

            # Check orders
            if a.transaction_data and "order_id" in a.transaction_data:
                order_id = a.transaction_data["order_id"]
                order = await db.get(Order, order_id)
                if order:
                    print(f"Order: {order.id}, Status: {order.status}, Total: {order.total}, Cart ID: {order.cart_id}")

            # Check payments
            stmt_p = select(Payment).where(Payment.agent_id == a.agent_id)
            res_p = await db.execute(stmt_p)
            payments = res_p.scalars().all()
            print(f"Payments count for this agent: {len(payments)}")
            for p in payments:
                print(f"   Payment: id={p.id} order={p.order_id} amount={p.amount} status={p.status}")
        break

if __name__ == "__main__":
    asyncio.run(inspect_approvals())
