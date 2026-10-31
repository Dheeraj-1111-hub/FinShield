import sys; sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.commerce import Cart, Order

async def check():
    engine = create_async_engine(
        "sqlite+aiosqlite:///test_finshield.db",
        connect_args={"check_same_thread": False}
    )
    async with AsyncSession(engine) as db:
        stmt = select(AgentRun).options(selectinload(AgentRun.actions)).order_by(AgentRun.created_at.desc()).limit(10)
        res = await db.execute(stmt)
        runs = res.scalars().all()
        for run in runs:
            print(f'\n---')
            print(f'Run ID: {run.id}, Workspace: {run.workspace_id}, Status: {run.status.value}, Input: {run.input}')
            print('Actions:')
            for a in sorted(run.actions, key=lambda x: x.sequence_number):
                print(f'  - {a.tool_name}: {a.status.value}')
            
            carts_res = await db.execute(select(Cart).where(Cart.workspace_id == run.workspace_id))
            orders_res = await db.execute(select(Order).where(Order.workspace_id == run.workspace_id))
            
            carts = carts_res.scalars().all()
            orders = orders_res.scalars().all()
            print(f'Carts in this workspace: {len(carts)}')
            print(f'Orders in this workspace: {len(orders)}')

asyncio.run(check())
