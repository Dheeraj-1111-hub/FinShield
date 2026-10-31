import asyncio
from app.db.database import Base, engine, AsyncSessionLocal
from app.models.user import User, UserStatus
from app.models.commerce import Merchant, Product, MerchantStatus, ProductStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.agent import Agent, AgentStatus, AgentType
from app.models.intent import Intent, IntentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.services.commerce_init_service import initialize_sandbox_catalog
from app.core.security import get_password_hash
import uuid

async def seed():
    async with AsyncSessionLocal() as session:
        ws_id = "wksp_test"
        u_id = "usr_test"
        ag_id = "ag_test"
        int_id = "int_test"
        auth_id = "auth_test"

        # Create workspace
        ws = Workspace(id=ws_id, name="Test Workspace", slug="test", owner_id=u_id)
        session.add(ws)

        # Create user
        u = User(
            id=u_id,
            email="tester@finshield.dev",
            password_hash=get_password_hash("password123A"),
            full_name="Tester",
            status=UserStatus.ACTIVE
        )
        session.add(u)

        # Create member
        wm = WorkspaceMember(id=uuid.uuid4().hex, workspace_id=ws_id, user_id=u_id, role=WorkspaceRole.OWNER)
        session.add(wm)

    # Initialize sandbox catalog for the test workspace
    await initialize_sandbox_catalog(session, ws_id)


        # Create agent
        a = Agent(
            id=ag_id,
            workspace_id=ws_id,
            name="Shopping Agent",
            description="Agent for testing",
            type=AgentType.SHOPPING,
            status=AgentStatus.ACTIVE
        )
        session.add(a)

        # Create intent
        from app.models.intent import IntentType
        i = Intent(
            id=int_id,
            workspace_id=ws_id,
            title="Buy Laptops",
            natural_language_request="You are an autonomous shopping agent. Buy a laptop under INR 80,000.",
            intent_type=IntentType.PURCHASE,
            status=IntentStatus.ACTIVE,
            version=1
        )
        session.add(i)

        # Create authority
        auth = DelegatedAuthority(
            id=auth_id,
            workspace_id=ws_id,
            agent_id=ag_id,
            intent_id=int_id,
            name="Test Authority",
            budget_amount=100000,
            budget_currency="INR",
            status=AuthorityStatus.ACTIVE,
            version=1
        )
        session.add(auth)

        await session.commit()
        print("Test data seeded!")

if __name__ == "__main__":
    asyncio.run(seed())
