import asyncio
from app.db.database import Base, engine
# Import all models so they are registered with Base
from app.models import (
    user, workspace, agent, agent_runtime, authority,
    intent, payment, commerce, gate, audit, risk, policy
)

async def reset_db():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        ws = workspace.Workspace(id="wksp_default", name="Default Workspace", slug="default", owner_id="usr_default")
        u = user.User(id="usr_default", email="admin@finshield.com", password_hash="dummy", full_name="Admin")
        session.add(ws)
        session.add(u)
        await session.commit()
    print("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_db())
