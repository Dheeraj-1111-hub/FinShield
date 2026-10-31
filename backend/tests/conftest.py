import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport
import os
import sys
import uuid

# MUST set this before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_finshield.db"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import get_db, Base
# Import all models to ensure they are registered with Base
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.models.auth_token import AuthToken
from app.models.auth_event import AuthEvent
from app.models.agent import Agent, AgentCredential
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.commerce import Merchant, Product, Cart, CartItem, Order, OrderItem
from app.models.payment import Payment
from app.models.gate import GateDecision, ApprovalRequest
from app.models.risk import RiskAssessment
from app.models.authority import DelegatedAuthority
from app.models.intent import Intent
from app.core.rate_limit import limiter

# Disable rate limiting for tests
limiter.enabled = False

# Use an isolated test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_finshield.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Setup test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c
    
    app.dependency_overrides.clear()
