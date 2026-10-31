import asyncio
from sqlalchemy import update
from app.db.database import get_db
from app.models.agent import Agent

async def reset():
    async for db in get_db():
        await db.execute(update(Agent).values(status='ACTIVE'))
        await db.commit()
        print('Agent status reset to ACTIVE')
        break

if __name__ == "__main__":
    asyncio.run(reset())
