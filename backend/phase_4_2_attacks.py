import asyncio
import os
import httpx
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import select

from app.main import app as fastapi_app
from app.db.database import AsyncSessionLocal
from httpx import ASGITransport
from phase_3_evidence_suite import setup_test_agent
from app.models.workspace import Workspace
from app.models.user import User
from app.models.gate import ApprovalRequest, ApprovalStatus
from app.models.agent import Agent, AgentStatus
from app.models.authority import DelegatedAuthority
from app.models.commerce import Product, Cart, Order
from app.services.agent_runtime_service import AgentRuntimeService
from app.services.approval_service import ApprovalService
from app.services.commerce_service import CommerceService
from app.schemas.execution_context import ExecutionContext

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

client = httpx.AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")

async def get_test_product(db, name_like: str):
    stmt = select(Product).where(Product.name.like(name_like))
    return (await db.execute(stmt)).scalars().first()

async def simulate_human_approval(db, run_id, workspace_id, user_id):
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.agent_run_id == run_id,
        ApprovalRequest.status == ApprovalStatus.PENDING
    ).order_by(ApprovalRequest.created_at.desc())
    appr = (await db.execute(stmt)).scalars().first()
    if appr:
        approval_service = ApprovalService(db)
        await approval_service.approve(appr.id, workspace_id, user_id)
        return appr.id
    return None

async def run_attack(db, name, attack_func):
    print(f"\n{'='*50}\n[ATTACK] {name}\n{'='*50}")
    try:
        await attack_func(db)
    except Exception as e:
        print(f"Attack crashed: {e}")

async def test_attack_1_amount_escalation(db):
    # Setup
    ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
    user = (await db.execute(select(User).limit(1))).scalars().first()
    ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
    
    prod_office = await get_test_product(db, "%Office%") # 75k
    prod_saas = await get_test_product(db, "%SaaS%") # 15k
    
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy laptop", authority_id=auth.id)
    headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    
    # 1. Create cart and add Office Laptop (75k)
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id = resp.json()["output"]["cart_id"]
    
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    # 2. Checkout (Hits REVIEW for 75k)
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    assert resp.status_code == 402
    
    # 3. Approve
    await simulate_human_approval(db, run.id, ws.id, user.id)
    
    # 4. Attack: Add SaaS (15k) to make cart 90k
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_saas.id, "quantity": 1}}, headers=headers)
    
    # 5. Retry Checkout
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    print(f"Result Status: {resp.status_code}")
    print(f"Result Output: {resp.text}")
    
    if resp.status_code == 402:
        print("[SUCCESS] Attack 1 REJECTED (Required new review).")
    else:
        print("[FAIL] Attack 1 EXPLOITABLE.")


async def test_attack_2_product_substitution(db):
    ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
    user = (await db.execute(select(User).limit(1))).scalars().first()
    ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
    
    prod_office = await get_test_product(db, "%Office Laptop%") # 75k
    prod_quantum = await get_test_product(db, "%Quantum%") # 75k
    
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy laptop", authority_id=auth.id)
    headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    
    # 1. Create cart and add Office Laptop (75k)
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id_1 = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id_1, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    # 2. Checkout (Hits REVIEW for 75k)
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id_1}}, headers=headers)
    assert resp.status_code == 402
    
    # 3. Approve
    await simulate_human_approval(db, run.id, ws.id, user.id)
    
    # 4. Attack: Create NEW cart, add Quantum Server (75k), and checkout
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id_2 = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id_2, "product_id": prod_quantum.id, "quantity": 1}}, headers=headers)
    
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id_2}}, headers=headers)
    
    print(f"Result Status: {resp.status_code}")
    print(f"Result Output: {resp.text}")
    
    if resp.status_code == 200:
        print("[FAIL] Attack 2 EXPLOITABLE! Product substituted without review.")
        order_id = resp.json()["output"]["order_id"]
        order = (await db.execute(select(Order).where(Order.id == order_id))).scalars().first()
        print(f"Unauthorized Order created: {order.id} for {order.total} {order.currency}")
    else:
        print("[SUCCESS] Attack 2 REJECTED.")

async def test_attack_3_approval_replay(db):
    ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
    user = (await db.execute(select(User).limit(1))).scalars().first()
    ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
    
    prod_office = await get_test_product(db, "%Office%") # 75k
    
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy laptop", authority_id=auth.id)
    headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    # Checkout -> REVIEW
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    # Approve
    await simulate_human_approval(db, run.id, ws.id, user.id)
    
    # Execute Checkout (Allowed)
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    assert resp.status_code == 200
    print("First execution allowed.")
    
    # Attack: Create a 2nd cart with same amount and checkout using Replay
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id_2 = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id_2, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id_2}}, headers=headers)
    
    print(f"Replay Result Status: {resp.status_code}")
    print(f"Replay Result Output: {resp.text}")
    
    if resp.status_code == 200:
        print("[FAIL] Attack 3 EXPLOITABLE! Replayed approval.")
    else:
        print("[SUCCESS] Attack 3 REJECTED.")

async def test_attack_4_agent_revocation(db):
    ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
    user = (await db.execute(select(User).limit(1))).scalars().first()
    ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
    prod_office = await get_test_product(db, "%Office%")
    
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy laptop", authority_id=auth.id)
    headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    # Checkout -> REVIEW
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    # Approve
    await simulate_human_approval(db, run.id, ws.id, user.id)
    
    # Revoke Agent
    ag.status = AgentStatus.REVOKED
    await db.commit()
    
    # Execute Checkout
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    print(f"Result Status: {resp.status_code}")
    if resp.status_code in [401, 403]:
        print("[SUCCESS] Attack 4 REJECTED.")
    else:
        print("[FAIL] Attack 4 EXPLOITABLE.")

async def test_attack_5_authority_mutation(db):
    ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
    user = (await db.execute(select(User).limit(1))).scalars().first()
    ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
    prod_office = await get_test_product(db, "%Office%")
    
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy laptop", authority_id=auth.id)
    headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "create_cart", "input": {}}, headers=headers)
    cart_id = resp.json()["output"]["cart_id"]
    await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "add_to_cart", "input": {"cart_id": cart_id, "product_id": prod_office.id, "quantity": 1}}, headers=headers)
    
    # Checkout -> REVIEW
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    # Approve
    await simulate_human_approval(db, run.id, ws.id, user.id)
    
    # Mutate Authority
    auth.monetary_limit = 10000
    await db.commit()
    
    # Execute Checkout
    resp = await client.post(f"/api/v1/agent-runtime/runs/{run.id}/actions", json={"tool_name": "checkout", "input": {"cart_id": cart_id}}, headers=headers)
    
    print(f"Result Status: {resp.status_code}")
    print(f"Result Output: {resp.text}")
    
    if resp.status_code == 403:
        print("[SUCCESS] Attack 5 REJECTED.")
    else:
        print("[FAIL] Attack 5 EXPLOITABLE.")

async def run_all():
    async with AsyncSessionLocal() as db:
        await test_attack_1_amount_escalation(db)
        await test_attack_2_product_substitution(db)
        await test_attack_3_approval_replay(db)
        await test_attack_4_agent_revocation(db)
        await test_attack_5_authority_mutation(db)

if __name__ == "__main__":
    asyncio.run(run_all())
