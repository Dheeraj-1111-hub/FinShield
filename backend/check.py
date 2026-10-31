import asyncio
import traceback
from app.db.database import get_db
from app.models.gate import ApprovalRequest
from sqlalchemy import select

async def main():
    try:
        async for db in get_db():
            res = (await db.execute(select(ApprovalRequest))).scalars().all()
            for r in res:
                print(r.id, r.workspace_id, r.status)
            print(f"Total: {len(res)}")
            break
    except Exception as e:
        traceback.print_exc()

asyncio.run(main())
