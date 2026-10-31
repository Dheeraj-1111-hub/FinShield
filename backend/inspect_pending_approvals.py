import asyncio
import json
from sqlalchemy import select
from app.db.database import get_db
from app.models.gate import ApprovalRequest
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.commerce import Order, Cart, CartItem
from app.models.payment import Payment

def clean(s):
    return str(s).encode('ascii', 'replace').decode('ascii')

async def main():
    async for db in get_db():
        # Specifically look for pending approvals for agent e668604c-0648-4cf2-a514-8cef005c20e0 (or status == PENDING)
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == "PENDING")
            .order_by(ApprovalRequest.created_at.desc())
        )
        res = await db.execute(stmt)
        approvals = res.scalars().all()
        print(f"Total PENDING approvals: {len(approvals)}")
        
        for a in approvals:
            print("="*70)
            print(f"APPROVAL ID: {a.id}")
            print(f"Status: {a.status}")
            print(f"Amount: {a.amount} {a.currency}")
            print(f"Created At: {a.created_at}")
            print(f"Agent ID: {a.agent_id}")
            print(f"Run ID: {a.agent_run_id}")
            print(f"Action ID: {a.agent_action_id}")
            print(f"Gate Decision ID: {a.gate_decision_id}")
            print(f"Tx Data: {a.transaction_data}")

            order_id = a.transaction_data.get("order_id") if a.transaction_data else None
            if order_id:
                order = await db.get(Order, order_id)
                if order:
                    print(f"ORDER: {order.id} | status={order.status} | total={order.total} | cart_id={order.cart_id} | created_at={order.created_at}")
                    cart = await db.get(Cart, order.cart_id)
                    if cart:
                        print(f"CART: {cart.id} | status={cart.status} | currency={cart.currency}")
                        stmt_ci = select(CartItem).where(CartItem.cart_id == cart.id)
                        res_ci = await db.execute(stmt_ci)
                        items = res_ci.scalars().all()
                        for item in items:
                            print(f"   CartItem: prod={item.product_id} qty={item.quantity}")

            # Check payment
            stmt_p = select(Payment).where(Payment.order_id == order_id)
            res_p = await db.execute(stmt_p)
            payments = res_p.scalars().all()
            print(f"PAYMENTS for order {order_id}: {len(payments)}")
            for p in payments:
                print(f"   Payment: id={p.id} status={p.status} amount={p.amount}")

            # Check run and its actions
            if a.agent_run_id:
                run = await db.get(AgentRun, a.agent_run_id)
                if run:
                    print(f"RUN: {run.id} | status={run.status} | input={clean(run.input)} | session={run.session_id} | created_at={run.created_at}")
                    stmt_acts = select(AgentAction).where(AgentAction.run_id == run.id).order_by(AgentAction.sequence_number.asc())
                    res_acts = await db.execute(stmt_acts)
                    actions = res_acts.scalars().all()
                    print(f"Actions in run ({len(actions)}):")
                    for act in actions:
                        print(f"   [{act.sequence_number}] id={act.id} tool={act.tool_name} status={act.status} in={clean(act.input)} err={clean(act.error_message)}")
        break

if __name__ == "__main__":
    asyncio.run(main())
