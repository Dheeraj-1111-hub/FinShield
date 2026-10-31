import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.commerce_service import CommerceService
from app.schemas.execution_context import ExecutionContext
from app.schemas.commerce import CartCreate

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///backend/finshield.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Test 1: Human Context (Should Work)
        print("Testing human context...")
        ctx_human = ExecutionContext(
            is_human=True,
            user_id="user_123",
            is_agent=False,
            is_agent_runtime=False
        )
        try:
            cart = await CommerceService.create_cart(
                db, 
                "ws_123", 
                CartCreate(currency="USD"), 
                ctx_human
            )
            print("Human success.")
        except Exception as e:
            print(f"Human failed (maybe expected if DB is empty): {e}")

        # Test 2: Malicious Agent Bypass (Should Fail)
        print("Testing malicious agent context...")
        ctx_malicious = ExecutionContext(
            is_human=False,
            is_agent=True,
            agent_id="agt_123",
            is_agent_runtime=False  # Try to bypass runtime
        )
        try:
            cart = await CommerceService.create_cart(
                db, 
                "ws_123", 
                CartCreate(currency="USD"), 
                ctx_malicious
            )
            print("Malicious agent bypass SUCCEEDED! (DANGER)")
        except Exception as e:
            print(f"Malicious agent bypass BLOCKED: {e}")
            
        # Test 3: Agent Runtime (Should Work, pending gate decision)
        print("Testing legitimate agent context...")
        ctx_runtime = ExecutionContext(
            is_human=False,
            is_agent=True,
            agent_id="agt_123",
            is_agent_runtime=True,
            gate_decision="ALLOW"
        )
        try:
            cart = await CommerceService.create_cart(
                db, 
                "ws_123", 
                CartCreate(currency="USD"), 
                ctx_runtime
            )
            print("Legitimate agent success.")
        except Exception as e:
            print(f"Legitimate agent failed: {e}")
            
        # Test 4: Agent Runtime Denied by Gate (Should Fail)
        print("Testing denied agent context...")
        ctx_denied = ExecutionContext(
            is_human=False,
            is_agent=True,
            agent_id="agt_123",
            is_agent_runtime=True,
            gate_decision="BLOCK"
        )
        try:
            cart = await CommerceService.create_cart(
                db, 
                "ws_123", 
                CartCreate(currency="USD"), 
                ctx_denied
            )
            print("Denied agent bypass SUCCEEDED! (DANGER)")
        except Exception as e:
            print(f"Denied agent BLOCKED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
