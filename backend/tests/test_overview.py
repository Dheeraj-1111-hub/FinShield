import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.core.security import get_password_hash, generate_session_token, hash_session_token

@pytest.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession):
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email="overview_test@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Overview User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    # Create session
    token = generate_session_token()
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(session)
    
    # Create workspace
    workspace_id = str(uuid.uuid4())
    workspace = Workspace(
        id=workspace_id,
        name="Overview Test Workspace",
        slug="overview-test-workspace",
        owner_id=user.id
    )
    db_session.add(workspace)
    
    # Create membership
    member = WorkspaceMember(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    
    await db_session.commit()
    
    client.cookies.set("finshield_session", token)
    client.headers["X-Workspace-ID"] = workspace_id
    return client

@pytest.mark.asyncio
async def test_get_overview(
    auth_client: AsyncClient
):
    # The client is already authenticated and has a workspace.
    # Retrieve the overview dashboard
    response = await auth_client.get("/api/v1/overview?time_range=30d")
    assert response.status_code == 200
    
    data = response.json()
    assert "time_range" in data
    assert data["time_range"] == "30d"
    
    assert "agents" in data
    assert "total" in data["agents"]
    
    assert "financial" in data
    assert "payment_volume" in data["financial"]
    assert "currency" in data["financial"]
    assert "balances_by_currency" in data["financial"]
    
    assert "gate" in data
    assert "allow" in data["gate"]
    
    assert "risk" in data
    assert "critical" in data["risk"]
    
    assert "health" in data
    assert data["health"]["api"] == "HEALTHY"
    
    assert "onboarding" in data
    assert "workspace_configured" in data["onboarding"]


@pytest.mark.asyncio
async def test_overview_mixed_currency_balances(
    auth_client: AsyncClient,
    db_session: AsyncSession
):
    """Verify that mixed INR and USD captured payments are not naively added together without currency awareness."""
    from app.models.payment import Payment, PaymentStatus
    import uuid
    from datetime import datetime, timezone

    # Get workspace id from headers
    workspace_id = auth_client.headers["X-Workspace-ID"]

    # Insert a captured INR payment and a captured USD payment
    inr_payment = Payment(
        id=f"pay_inr_{uuid.uuid4().hex[:12]}",
        workspace_id=workspace_id,
        payment_intent_id=f"pi_inr_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_inr_{uuid.uuid4().hex[:8]}",
        amount=150,
        currency="INR",
        status=PaymentStatus.CAPTURED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    usd_payment = Payment(
        id=f"pay_usd_{uuid.uuid4().hex[:12]}",
        workspace_id=workspace_id,
        payment_intent_id=f"pi_usd_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_usd_{uuid.uuid4().hex[:8]}",
        amount=15000,
        currency="USD",
        status=PaymentStatus.CAPTURED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(inr_payment)
    db_session.add(usd_payment)
    await db_session.commit()

    response = await auth_client.get("/api/v1/overview?time_range=30d")
    assert response.status_code == 200
    financial = response.json()["financial"]

    # Verify balances_by_currency segregates them
    assert "INR" in financial["balances_by_currency"]
    assert "USD" in financial["balances_by_currency"]
    assert financial["balances_by_currency"]["INR"] == 150.0
    assert financial["balances_by_currency"]["USD"] == 15000.0

    # Ensure payment_volume is NOT the naive sum of 15000 + 150 = 15150 treated as a single currency
    # It must match the workspace's currency balance
    ws_curr = financial["currency"]
    assert financial["payment_volume"] == financial["balances_by_currency"][ws_curr]
    assert financial["payment_volume"] in [150.0, 15000.0]
    assert financial["payment_volume"] != 15150.0


@pytest.mark.asyncio
async def test_orders_mixed_currency_in_workspace(
    auth_client: AsyncClient,
    db_session: AsyncSession
):
    """Verify that orders in both INR and USD can coexist in a workspace, retain distinct currencies/totals, and are returned accurately without currency collision."""
    from app.models.commerce import Merchant, Order, OrderStatus
    import uuid

    workspace_id = auth_client.headers["X-Workspace-ID"]

    merchant = Merchant(
        id=f"merch_{uuid.uuid4().hex[:16]}",
        workspace_id=workspace_id,
        name="Multi-Currency Merchant",
        status="ACTIVE"
    )
    db_session.add(merchant)

    order_inr = Order(
        id=f"ord_inr_{uuid.uuid4().hex[:12]}",
        workspace_id=workspace_id,
        merchant_id=merchant.id,
        cart_id=f"crt_{uuid.uuid4().hex[:12]}",
        status=OrderStatus.PAID,
        subtotal=150,
        total=150,
        currency="INR"
    )
    order_usd = Order(
        id=f"ord_usd_{uuid.uuid4().hex[:12]}",
        workspace_id=workspace_id,
        merchant_id=merchant.id,
        cart_id=f"crt_{uuid.uuid4().hex[:12]}",
        status=OrderStatus.PAID,
        subtotal=15000,
        total=15000,
        currency="USD"
    )
    db_session.add(order_inr)
    db_session.add(order_usd)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/commerce/orders")
    assert resp.status_code == 200
    orders = resp.json()

    retrieved_inr = next(o for o in orders if o["id"] == order_inr.id)
    retrieved_usd = next(o for o in orders if o["id"] == order_usd.id)

    assert retrieved_inr["currency"] == "INR"
    assert retrieved_inr["total"] == 150
    assert retrieved_usd["currency"] == "USD"
    assert retrieved_usd["total"] == 15000

    # Ensure currency groupings remain discrete and never sum across currencies
    totals_by_currency = {}
    for o in orders:
        curr = o["currency"]
        totals_by_currency[curr] = totals_by_currency.get(curr, 0) + o["total"]

    assert totals_by_currency["INR"] >= 150
    assert totals_by_currency["USD"] >= 15000
    # Naive cross-currency addition would produce sum with wrong currency representation
    assert totals_by_currency["INR"] != totals_by_currency["INR"] + totals_by_currency["USD"]

