import os
import json
import logging
import asyncio
from typing import TypedDict, Any, List, Optional
from groq import AsyncGroq
from langgraph.graph import StateGraph, END, START
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_runtime_service import AgentRuntimeService
from app.services.commerce_service import CommerceService
from app.schemas.execution_context import ExecutionContext
from app.schemas.commerce import CartCreate, CartItemCreate, OrderCreate

logger = logging.getLogger(__name__)

class BenchmarkAgentState(TypedDict):
    messages: list[dict]
    workspace_id: str
    run_id: str
    is_baseline: bool
    agent_id: str
    user_id: str
    
class BenchmarkAgent:
    """
    Real LangGraph-based LLM agent for executing benchmark trials.
    Supports running with or without FINSHIELD protection.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        
        self.tools = [
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
                    "description": "Create a new empty shopping cart.",
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
                    "description": "Add a product to an existing cart.",
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
                    "description": "Pay for an order.",
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
        
        workflow = StateGraph(BenchmarkAgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)
        self.graph = workflow.compile()

    async def _execute_tool(self, tool_name: str, args: dict, state: BenchmarkAgentState) -> Any:
        try:
            if state["is_baseline"]:
                # Unprotected execution - bypass FINSHIELD Gate entirely
                # Provide a developer/human context to skip agent authorization checks
                ctx = ExecutionContext(
                    is_human=True, 
                    user_id=state["user_id"], 
                    is_agent=False, 
                    is_agent_runtime=False
                )
                
                if tool_name == "search_products":
                    products = await CommerceService.list_products(self.db, state["workspace_id"], limit=10, category=args.get("category"))
                    # Format products to dicts and apply python filtering for query/price to match AgentRuntimeService
                    results = []
                    query = args.get("query", "").lower()
                    min_price = args.get("min_price")
                    max_price = args.get("max_price")
                    for p in products:
                        if query and query not in p.name.lower() and query not in p.description.lower():
                            continue
                        if min_price is not None and p.price < min_price:
                            continue
                        if max_price is not None and p.price > max_price:
                            continue
                        results.append({"id": p.id, "name": p.name, "price": p.price, "currency": p.currency, "inventory": p.inventory})
                    return {"results": results}
                elif tool_name == "create_cart":
                    cart = await CommerceService.create_cart(self.db, state["workspace_id"], CartCreate(currency="INR"), ctx)
                    return {"cart_id": cart.id}
                elif tool_name == "add_to_cart":
                    item = await CommerceService.add_cart_item(self.db, state["workspace_id"], args["cart_id"], CartItemCreate(product_id=args["product_id"], quantity=args.get("quantity", 1)), ctx)
                    return {"cart_id": args["cart_id"], "item_id": item.id}
                elif tool_name == "checkout":
                    cart = await CommerceService.get_cart(self.db, state["workspace_id"], args["cart_id"])
                    merchant_id = cart.items[0].product.merchant_id if cart.items else "mock"
                    order = await CommerceService.create_order(self.db, state["workspace_id"], OrderCreate(cart_id=args["cart_id"], merchant_id=merchant_id), ctx)
                    return {"order_id": order.id, "status": order.status}
                elif tool_name == "pay_order":
                    return {"transaction_id": "tx_mock", "status": "COMPLETED"}
            else:
                # Protected execution - Route through FINSHIELD AgentRuntime
                action = await AgentRuntimeService.execute_action(self.db, state["workspace_id"], state["run_id"], tool_name, args)
                if action.status == "REVIEW_REQUIRED":
                    return "REVIEW REQUIRED: This action requires human approval."
                elif action.status == "FAILED":
                    return f"ERROR: {action.error}"
                return action.output
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing {tool_name}: {str(e)}"
            
        return "Unknown tool"

    async def _agent_node(self, state: BenchmarkAgentState):
        messages = state["messages"].copy()
        
        max_iterations = 12
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                temperature=0.0,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_unset=True))
            
            if message.content:
                logger.info(f"AGENT: {message.content}")
            
            if not message.tool_calls:
                break
                
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception:
                    args = {}
                    
                logger.info(f"ACTION: {tool_name} -> {args}")
                result = await self._execute_tool(tool_name, args, state)
                logger.info(f"FINSHIELD: {result}")
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(result)
                })
                
        return {"messages": messages}
        
    async def run_trial(self, workspace_id: str, agent_id: str, user_id: str, run_id: str, initial_prompt: str, is_baseline: bool) -> dict:
        """Executes a benchmark trial for the given agent run."""
        inputs = {
            "messages": [{"role": "user", "content": initial_prompt}],
            "workspace_id": workspace_id,
            "run_id": run_id,
            "is_baseline": is_baseline,
            "agent_id": agent_id,
            "user_id": user_id
        }
        
        final_state = await self.graph.ainvoke(inputs)
        return final_state
