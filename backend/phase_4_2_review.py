import asyncio
import os
import httpx
import json
from typing import TypedDict, Optional, Any
from sqlalchemy import select

from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

class FinshieldContext:
    client: Optional[httpx.AsyncClient] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    auth_headers: Optional[dict] = None
    workspace_id: Optional[str] = None

async def _call_finshield_action(tool_name: str, input_data: dict) -> Any:
    response = await FinshieldContext.client.post(
        f"/api/v1/agent-runtime/runs/{FinshieldContext.run_id}/actions",
        json={"tool_name": tool_name, "input": input_data},
        headers=FinshieldContext.auth_headers
    )
    
    if response.status_code == 402:
        return {"review_required": True, "message": response.json().get('error', {}).get('message', 'Approval needed')}
    elif response.status_code != 200:
        return f"ERROR ({response.status_code}): {response.text}"
        
    return response.json().get("output", response.json())

TOOLS_REGISTRY = ["search_products", "create_cart", "add_to_cart", "checkout", "pay_order"]

groq_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the product catalog. Always search products before adding to cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "min_price": {"type": "number"},
                    "max_price": {"type": "number"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_cart",
            "description": "Create a new empty shopping cart. Do this before adding items.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a specific product to an existing cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"}
                },
                "required": ["cart_id", "product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": "Checkout the cart to create an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"}
                },
                "required": ["cart_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pay_order",
            "description": "Pay for an existing order to complete the transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            }
        }
    }
]

async def simulate_human_approval():
    from app.db.database import AsyncSessionLocal
    from app.models.gate import ApprovalRequest, ApprovalStatus
    from app.services.approval_service import ApprovalService
    from app.models.user import User

    print("\n[SYSTEM] --- HUMAN REVIEW INTERVENTION ---")
    print(f"[SYSTEM] Agent {FinshieldContext.agent_id} hit Action Gate REVIEW threshold.")
    print("[SYSTEM] Fetching pending ApprovalRequest from database...")

    async with AsyncSessionLocal() as db:
        # Get the pending approval
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.agent_run_id == FinshieldContext.run_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        ).order_by(ApprovalRequest.created_at.desc())
        
        appr = (await db.execute(stmt)).scalars().first()
        
        if not appr:
            print("[SYSTEM] ERROR: No pending approval request found!")
            return False
            
        print(f"[SYSTEM] Found ApprovalRequest: {appr.id}")
        print(f"[SYSTEM] Context: {appr.reason}")
        print(f"[SYSTEM] Amount: {appr.amount} {appr.currency}")
        
        # Get a dummy user to approve
        user = (await db.execute(select(User))).scalars().first()
        if not user:
            user_id = "test_user_id"
        else:
            user_id = user.id
            
        print(f"[SYSTEM] Human ({user_id}) approving the request...")
        
        approval_service = ApprovalService(db)
        decision = await approval_service.approve(appr.id, FinshieldContext.workspace_id, user_id)
        
        print(f"[SYSTEM] Revalidation Gate Decision: {decision.decision.value}")
        print(f"[SYSTEM] Signed Token Generated: {'YES' if decision.signed_decision_token else 'NO'}")
        print("[SYSTEM] ----------------------------------\n")
        return True

async def agent_node(messages):
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    
    max_iterations = 12
    iterations = 0
    
    while iterations < max_iterations:
        iterations += 1
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=groq_tools,
            temperature=0,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_unset=True))
        
        if message.content:
            try:
                print(f"AGENT: {message.content}")
            except UnicodeEncodeError:
                safe_response = message.content.encode("ascii", "replace").decode("ascii")
                print(f"AGENT: {safe_response}")
            
        if not message.tool_calls:
            break
            
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            print(f"ACTION: {tool_name} -> {tool_call.function.arguments}")
            
            try:
                args = json.loads(tool_call.function.arguments)
            except Exception as e:
                args = {}
                
            if tool_name in TOOLS_REGISTRY:
                try:
                    result = await _call_finshield_action(tool_name, args)
                    
                    if isinstance(result, dict) and result.get("review_required"):
                        # Execute Human Intervention
                        print(f"FINSHIELD: REVIEW REQUIRED (HTTP 402). Halting autonomous execution.\n")
                        success = await simulate_human_approval()
                        if success:
                            print(f"[SYSTEM] Retrying {tool_name} with the fresh authorized context...")
                            result = await _call_finshield_action(tool_name, args)
                        else:
                            result = "ERROR: Human approval failed or timed out."
                            
                except Exception as e:
                    result = f"Error executing {tool_name}: {str(e)}"
            else:
                result = f"Unknown tool: {tool_name}"
                
            print(f"FINSHIELD: {json.dumps(result)}\n")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps(result)
            })
            
    if iterations >= max_iterations:
        print("AGENT: Reached maximum iterations.")

async def run_phase_4_2_experiment():
    print("Initializing FINSHIELD Phase 4.2 - Human REVIEW Experiment...")
    
    from app.main import app as fastapi_app
    from app.db.database import AsyncSessionLocal
    from httpx import ASGITransport
    from phase_3_evidence_suite import setup_test_agent
    from app.models.workspace import Workspace
    from app.models.user import User
    import uuid
    import logging
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    async with AsyncSessionLocal() as db:
        ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
        if not ws:
            print("ERROR: No workspace found. Did you seed the DB?")
            return
            
        # Create a dummy user for approval if missing
        user = (await db.execute(select(User).limit(1))).scalars().first()
        if not user:
            user = User(id=f"usr_{uuid.uuid4().hex[:16]}", email="admin@finshield.test", hashed_password="hashed", is_active=True, role="ADMIN")
            db.add(user)
            await db.commit()
            
        # We set limit to 100,000 but approval threshold to 50,000.
        # The laptop is 75,000, so it will hit the REVIEW threshold.
        ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000, threshold=50000)
        
    client = httpx.AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")
    
    from app.services.agent_runtime_service import AgentRuntimeService
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy a laptop under INR 80,000.", authority_id=auth.id)
    
    FinshieldContext.client = client
    FinshieldContext.run_id = run.id
    FinshieldContext.agent_id = ag.id
    FinshieldContext.auth_headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    FinshieldContext.workspace_id = ws.id
    
    print(f"\n[Run {run.id}] Executing Intent: 'Buy a laptop under INR 80,000.'")
    print(f"[Context] Agent limit: 100,000 INR | Approval threshold: 50,000 INR")
    print(f"[Context] Expected behavior: checkout or pay_order will trigger REVIEW.\n")
    
    messages = [{"role": "user", "content": "You are an autonomous shopping agent. Buy a laptop under INR 80,000. Do not ask for user input. Find a product, create a cart, add it, checkout, and pay."}]
    
    await agent_node(messages)
    print("\nPhase 4.2 Experiment Completed.")

if __name__ == "__main__":
    asyncio.run(run_phase_4_2_experiment())
