import pytest
import uuid
import json
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.models.agent import Agent
from app.models.commerce import Product, Cart, CartItem, Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.services.agent_runtime_service import AgentRuntimeService

def forge_token(payload: dict, secret: str) -> str:
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return f"{payload_b64}.{signature}"

@pytest.fixture
async def setup_adversarial_data(db_session: AsyncSession):
    from app.models.user import User, UserStatus
    from app.models.workspace import Workspace
    
    user_id = f"usr_{uuid.uuid4().hex}"
    user = User(
        id=user_id, 
        email=f"{uuid.uuid4().hex}@test.com", 
        password_hash="hash", 
        full_name="Test",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    
    workspace_id = f"ws_{uuid.uuid4().hex}"
    workspace = Workspace(
        id=workspace_id, 
        name="Test Workspace", 
        slug=f"test-ws-{uuid.uuid4().hex[:8]}", 
        owner_id=user.id
    )
    db_session.add(workspace)

    from app.models.agent import Agent, AgentType, AgentStatus
    agent_id = f"agt_{uuid.uuid4().hex}"
    agent = Agent(
        id=agent_id, 
        workspace_id=workspace_id, 
        name="Attacker Agent", 
        type=AgentType.SHOPPING, 
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)
    
    from app.models.commerce import Merchant
    merchant_id = f"mer_{uuid.uuid4().hex}"
    merchant = Merchant(
        id=merchant_id,
        workspace_id=workspace_id,
        name="Test Merchant"
    )
    db_session.add(merchant)
    
    product = Product(
        id=f"prd_{uuid.uuid4().hex}",
        merchant_id=merchant_id,
        name="Laptop",
        price=500000,
        currency="USD"
    )
    db_session.add(product)
    
    order_id = f"ord_{uuid.uuid4().hex}"
    order = Order(
        id=order_id,
        workspace_id=workspace_id,
        merchant_id=merchant_id,
        cart_id=f"crt_{uuid.uuid4().hex}",
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=product.price,
        total=product.price,
        currency="USD",
        agent_id=agent_id
    )
    db_session.add(order)
    await db_session.commit()
    
    base_payload = {
        "decision_id": f"dec_{uuid.uuid4().hex}",
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "agent_run_id": f"run_{uuid.uuid4().hex}",
        "agent_action_id": f"act_{uuid.uuid4().hex}",
        "action_type": "pay_order",
        "decision": "ALLOW",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "nonce": uuid.uuid4().hex,
        "target_identity": order_id,
        "amount": 500000,
        "currency": "USD"
    }
    
    return {
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "order_id": order_id,
        "base_payload": base_payload
    }

class FakeInput:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    # We need dict conversion for AgentRuntimeService
    def dict(self, **kwargs):
        return self.__dict__

@pytest.mark.asyncio
async def test_adversarial_tampered_amount(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to pay with a token that has a tampered amount, but original signature"""
    data = setup_adversarial_data
    
    tampered_payload = data["base_payload"].copy()
    original_token = forge_token(tampered_payload, settings.ENCRYPTION_KEY)
    
    tampered_payload["amount"] = 100
    payload_b64 = base64.urlsafe_b64encode(json.dumps(tampered_payload).encode("utf-8")).decode("utf-8")
    original_sig = original_token.split(".")[1]
    tampered_token = f"{payload_b64}.{original_sig}"
    
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token=tampered_token
        )
    assert "Invalid token signature" in str(exc.value) or "403" in str(exc.value)

@pytest.mark.asyncio
async def test_adversarial_forged_signature(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to pay with a completely forged token"""
    data = setup_adversarial_data
    forged_token = forge_token(data["base_payload"], "wrong_secret_key_12345")
    
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token=forged_token
        )
    assert "Invalid token signature" in str(exc.value) or "403" in str(exc.value)

@pytest.mark.asyncio
async def test_adversarial_truncated_token(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to pay with an invalid/truncated token format"""
    data = setup_adversarial_data
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token="invalid.token"
        )
    # Could be ValueError or HTTPException
    assert True

@pytest.mark.asyncio
async def test_adversarial_expired_token(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to use an expired token"""
    data = setup_adversarial_data
    expired_payload = data["base_payload"].copy()
    expired_payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    expired_token = forge_token(expired_payload, settings.ENCRYPTION_KEY)
    
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token=expired_token
        )
    assert "expired" in str(exc.value).lower() or "403" in str(exc.value)

@pytest.mark.asyncio
async def test_adversarial_target_mismatch(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to use a valid token but bound to a different target (TOCTOU)"""
    data = setup_adversarial_data
    
    # Token is bound to order A, but we use it for order B
    token = forge_token(data["base_payload"], settings.ENCRYPTION_KEY)
    
    # Create order B
    order_b_id = f"ord_{uuid.uuid4().hex}"
    order_b = Order(
        id=order_b_id,
        workspace_id=data["workspace_id"],
        merchant_id=f"mer_{uuid.uuid4().hex}",
        cart_id=f"crt_{uuid.uuid4().hex}",
        status=OrderStatus.PENDING_PAYMENT,
        subtotal=500000,
        total=500000,
        currency="USD",
        agent_id=data["agent_id"]
    )
    db_session.add(order_b)
    await db_session.commit()
    
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=order_b_id), 
            raw_input={"order_id": order_b_id}, signed_decision_token=token
        )
    assert "target mismatch" in str(exc.value).lower() or "403" in str(exc.value)

@pytest.mark.asyncio
async def test_adversarial_replay_attack(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to reuse the same successfully consumed token (nonce check)"""
    data = setup_adversarial_data
    token = forge_token(data["base_payload"], settings.ENCRYPTION_KEY)
    from app.models.gate import GateDecision, DecisionResult
    decision_record = GateDecision(
        id=f"gde_{uuid.uuid4().hex}",
        workspace_id=data["workspace_id"],
        agent_id=data["agent_id"],
        agent_run_id=data["base_payload"]["agent_run_id"],
        agent_action_id=data["base_payload"]["agent_action_id"],
        decision=DecisionResult.ALLOW,
        evaluation_snapshot={"action_type": "pay_order"},
        nonce=data["base_payload"]["nonce"]
    )
    db_session.add(decision_record)
    await db_session.commit()
    
    # First attempt - should succeed
    res = await AgentRuntimeService._execute_tool_logic(
        db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
        tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
        raw_input={"order_id": data["order_id"]}, signed_decision_token=token
    )
    assert res is not None
    
    # Reset order state to allow it to be paid again (bypassing business idempotency)
    # We want to explicitly test the Gate idempotency (nonce)
    await db_session.execute(text("UPDATE orders SET status = 'PENDING_PAYMENT' WHERE id = :oid"), {"oid": data["order_id"]})
    await db_session.commit()
    
    # Second attempt - should fail because nonce is consumed
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token=token
        )
    assert "nonce" in str(exc.value).lower() or "403" in str(exc.value)

@pytest.mark.asyncio
async def test_adversarial_capability_escalation(db_session: AsyncSession, setup_adversarial_data):
    """Attempt to use a token approved for search_products to pay for an order"""
    data = setup_adversarial_data
    
    payload = data["base_payload"].copy()
    payload["action_type"] = "search_products" # Token was only for searching
    token = forge_token(payload, settings.ENCRYPTION_KEY)
    
    with pytest.raises(Exception) as exc:
        await AgentRuntimeService._execute_tool_logic(
            db=db_session, workspace_id=data["workspace_id"], agent_id=data["agent_id"], 
            tool_name="pay_order", input_data=FakeInput(order_id=data["order_id"]), 
            raw_input={"order_id": data["order_id"]}, signed_decision_token=token
        )
    assert "403" in str(exc.value)
