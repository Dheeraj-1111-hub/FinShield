import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8")
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.authority import DelegatedAuthority
from app.models.intent import Intent
from app.models.commerce import Product, Merchant

async def main():
    async with AsyncSessionLocal() as session:
        ws_id = "wksp_6b59281eac51"
        print("=== PRODUCTS IN WORKSPACE ===")
        products = (await session.execute(select(Product).join(Merchant).where(Merchant.workspace_id == ws_id))).scalars().all()
        for p in products:
            print(f"Product {p.id}: name='{p.name}', category='{p.category}', price={p.price}, curr={p.currency}, inv={p.inventory}")
            
        print("\n=== ALL AUTHORITIES IN WORKSPACE ===")
        auths = (await session.execute(select(DelegatedAuthority).where(DelegatedAuthority.workspace_id == ws_id))).scalars().all()
        for a in auths:
            print(f"Auth {a.id}: agent_id={a.agent_id}, status={a.status}, caps={a.allowed_capabilities}, curr={a.currency}, limit={a.monetary_limit}, appr={a.approval_threshold}, intent_id={a.intent_id}")
            
        print("\n=== ALL INTENTS IN WORKSPACE ===")
        intents = (await session.execute(select(Intent).where(Intent.workspace_id == ws_id))).scalars().all()
        for i in intents:
            print(f"Intent {i.id}: agent_id={i.agent_id}, status={i.status}, req='{i.natural_language_request}', constraints={i.structured_constraints}")
            
        print("\n=== ALL AGENTS IN WORKSPACE ===")
        agents = (await session.execute(select(Agent).where(Agent.workspace_id == ws_id))).scalars().all()
        for ag in agents:
            print(f"Agent {ag.id}: name='{ag.name}', status={ag.status}, curr={ag.currency}")

asyncio.run(main())
