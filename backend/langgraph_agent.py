import asyncio
import os
import httpx
import json
from typing import TypedDict, Optional, Any

from groq import AsyncGroq

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Agent State
class AgentState(TypedDict):
    messages: list[dict]

# FINSHIELD API Client Context
class FinshieldContext:
    client: Optional[httpx.AsyncClient] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    auth_headers: Optional[dict] = None

# FINSHIELD Tools
async def _call_finshield_action(tool_name: str, input_data: dict) -> Any:
    """Helper to dispatch the tool call to FINSHIELD Agent Runtime."""
    if not FinshieldContext.client or not FinshieldContext.run_id:
        raise RuntimeError("FINSHIELD context not initialized.")
        
    response = await FinshieldContext.client.post(
        f"/api/v1/agent-runtime/runs/{FinshieldContext.run_id}/actions",
        json={"tool_name": tool_name, "input": input_data},
        headers=FinshieldContext.auth_headers
    )
    
    if response.status_code == 402:
        return f"REVIEW REQUIRED: {response.json().get('error', {}).get('message', 'Approval needed')}"
    elif response.status_code != 200:
        return f"ERROR ({response.status_code}): {response.text}"
        
    return response.json().get("output", response.json())

# Tool mappings
TOOLS_REGISTRY = {
    "search_products": _call_finshield_action,
    "create_cart": _call_finshield_action,
    "add_to_cart": _call_finshield_action,
    "checkout": _call_finshield_action,
    "pay_order": _call_finshield_action
}

# Groq tool schema
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

from langgraph.graph import StateGraph, END, START

async def agent_node(state: AgentState):
    """The reasoning node where the LLM decides what to do next."""
    messages = state["messages"].copy()
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
        # Groq SDK returns a pydantic model, model_dump converts it safely
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
                    if tool_name == "create_cart":
                        result = await _call_finshield_action(tool_name, {})
                    else:
                        result = await _call_finshield_action(tool_name, args)
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
        
    return {"messages": messages}

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)
app_graph = workflow.compile()

async def run_sandbox_purchase():
    print("Initializing FINSHIELD LangGraph Agent...")
    
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY environment variable is required.")
        return
        
    from app.main import app as fastapi_app
    from app.db.database import AsyncSessionLocal
    from httpx import ASGITransport
    from phase_3_evidence_suite import setup_test_agent
    from app.models.workspace import Workspace
    from sqlalchemy import select
    
    import logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    async with AsyncSessionLocal() as db:
        ws = (await db.execute(select(Workspace).limit(1))).scalars().first()
        if not ws:
            print("ERROR: No workspace found. Did you seed the DB?")
            return
            
        ag, cred, intt, auth, secret = await setup_test_agent(db, ws, limit=100000)
        
    client = httpx.AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")
    
    from app.services.agent_runtime_service import AgentRuntimeService
    run = await AgentRuntimeService.create_run(db, ws.id, ag.id, "Buy a laptop under INR 80,000.", authority_id=auth.id)
    run_id = run.id
    
    auth_headers = {"Authorization": f"Bearer {cred.client_id}:{secret}"}
    FinshieldContext.client = client
    FinshieldContext.run_id = run_id
    FinshieldContext.agent_id = ag.id
    FinshieldContext.auth_headers = auth_headers
    
    print(f"\n[Run {run_id}] Executing Intent: 'Buy a laptop under INR 80,000.'\n")
    
    inputs = {"messages": [{"role": "user", "content": "You are an autonomous shopping agent. Buy a laptop under INR 80,000. Do not ask for user input. Find a product, create a cart, add it, checkout, and pay."}]}
    
    await app_graph.ainvoke(inputs)
    print("\nLangGraph Execution Completed.")

if __name__ == "__main__":
    asyncio.run(run_sandbox_purchase())
