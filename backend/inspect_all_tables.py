import asyncio
from app.db.database import AsyncSessionLocal, engine
from sqlalchemy import text

async def find_all():
    async with AsyncSessionLocal() as db:
        # Get all table names
        res = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [r[0] for r in res.fetchall() if not r[0].startswith("sqlite_")]
        
        for table in tables:
            # Check if created_at column exists
            col_res = await db.execute(text(f"PRAGMA table_info({table});"))
            cols = [c[1] for c in col_res.fetchall()]
            date_col = next((c for c in cols if 'created' in c or 'time' in c), None)
            if date_col:
                q = f"SELECT * FROM {table} WHERE {date_col} LIKE '2026-10-11 13:28%' OR {date_col} LIKE '2026-10-11 13:29%';"
                try:
                    r = await db.execute(text(q))
                    rows = r.fetchall()
                    if rows:
                        print(f"=== Table {table} ({len(rows)} rows) ===")
                        for row in rows:
                            print(f"  {row}")
                except Exception as e:
                    pass

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(find_all())
