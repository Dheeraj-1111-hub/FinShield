import asyncio
import json
from app.db.database import AsyncSessionLocal, engine
from app.models.audit import AuditEvent
from sqlalchemy import select

def safe(val):
    if val is None:
        return "None"
    return str(val).encode("ascii", "replace").decode("ascii")

async def inspect():
    async with AsyncSessionLocal() as db:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.workspace_id == 'wksp_6b59281eac51')
            .order_by(AuditEvent.created_at.asc())
        )
        audits = (await db.execute(stmt)).scalars().all()
        print(f"Total audit events in workspace: {len(audits)}")
        for a in audits:
            if "2026-10-11 13:28" in str(a.created_at) or "2026-10-11 13:29" in str(a.created_at):
                print(f"[{a.created_at}] type={a.event_type} cat={a.event_category} actor={a.actor_type}/{a.actor_id} entity={a.entity_type}/{a.entity_id}")
                print(f"    payload={json.dumps(a.payload, default=str)}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
