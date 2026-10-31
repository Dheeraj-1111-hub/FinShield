import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from app.models.commerce import Product

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///./finshield.db')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        ids = ['prod_8cf0dc5aa42a4ac4', 'prod_a3ab8041f8f9419b', 'prod_c1d43ed7f2ac45c5', 'prod_a98f7364ad214e2a']
        for pid in ids:
            await db.execute(update(Product).where(Product.id == pid).values(category='laptop'))
        await db.commit()
        print('Products updated to laptop category')

asyncio.run(main())