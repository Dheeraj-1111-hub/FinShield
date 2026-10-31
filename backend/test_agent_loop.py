import asyncio
from app.db.database import get_db
from sqlalchemy import select
from app.models.agent import Agent
from app.models.workspace import Workspace
from app.services.agent_runtime_service import AgentRuntimeService
from app.api.routes.agent_runtime import run_deterministic_agent
from app.models.agent_runtime import AgentRun

async def test_trace():
    print("Finding a workspace and agent...")
    async for db in get_db():
        workspace = (await db.execute(select(Workspace).limit(1))).scalar_one_or_none()
        if not workspace:
            print("No workspace found.")
            return
            
        agent = (await db.execute(select(Agent).where(Agent.workspace_id == workspace.id).limit(1))).scalar_one_or_none()
        if not agent:
            print("No agent found.")
            return
        
        print(f"Creating a new run for agent {agent.id} in workspace {workspace.id}...")
        
        run = await AgentRuntimeService.create_run(
            db=db,
            workspace_id=workspace.id,
            agent_id=agent.id,
            input_text="Find me a laptop under ₹40,000.",
            trigger_type="API"
        )
        
        print(f"Testing on new Run ID: {run.id}")
        await run_deterministic_agent(run.id, run.workspace_id)
        break

if __name__ == "__main__":
    asyncio.run(test_trace())
