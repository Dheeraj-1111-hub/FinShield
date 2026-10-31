import asyncio
from app.db.database import get_db
from app.models.workspace import Workspace
from app.models.gate import ApprovalRequest
from sqlalchemy import select

async def main():
    async for db in get_db():
        w = (await db.execute(select(Workspace))).scalars().all()
        print("Workspaces:", [ww.id for ww in w])
        approvals = (await db.execute(select(ApprovalRequest))).scalars().all()
        for a in approvals:
            print(a.id, a.workspace_id)
        break

asyncio.run(main())
