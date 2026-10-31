import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
import json
from app.models.intent import Intent

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///./finshield.db')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        # Get the intent
        from sqlalchemy import select
        stmt = select(Intent).where(Intent.id == 'int_dccc14a8ba484830')
        result = await db.execute(stmt)
        intent = result.scalar_one_or_none()
        if intent:
            constraints = intent.structured_constraints
            constraints['product']['category'] = 'laptop'
            await db.execute(update(Intent).where(Intent.id == 'int_dccc14a8ba484830').values(structured_constraints=constraints))
            await db.commit()
            print('Intent updated to laptop category')
        else:
            print('Intent not found')

asyncio.run(main())