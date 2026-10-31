import asyncio
from app.db.database import AsyncSessionLocal, engine
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.commerce import Cart, Order
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.get(AgentRun, 'run_0d6e4fd468b044d6')
        if r:
            print(f'Run 0d6e4fd468b044d6: status={r.status}, created={r.created_at}')
            stmt_a = select(AgentAction).where(AgentAction.run_id == r.id).order_by(AgentAction.sequence_number.asc())
            acts = (await db.execute(stmt_a)).scalars().all()
            for a in acts:
                print(f'  act [{a.sequence_number}]: tool={a.tool_name}, in={a.input}, out={a.output}, status={a.status}')
        from app.models.authority import DelegatedAuthority
        auth = await db.get(DelegatedAuthority, 'auth_70cfdb7c5077')
        if auth:
            print(f'Authority: limit={auth.monetary_limit}, approval_threshold={auth.approval_threshold}, currency={auth.currency}')

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
