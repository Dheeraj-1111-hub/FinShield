import uuid
import json
import base64
import hmac
import hashlib
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.models.gate import GateDecision, DecisionResult

@dataclass
class ScenarioResult:
    scenario_id: str
    attack_class: str
    input_summary: str
    runtime_path: str
    expected_result: int
    observed_result: int
    gate_decision: Optional[str]
    order_created: bool
    payment_created: bool
    audit_event_id: Optional[str]
    duration_ms: float
    passed: bool

class SecurityExecutor:
    def __init__(self, db: AsyncSession, client: AsyncClient, workspace_id: str, agent_id: str):
        self.db = db
        self.client = client
        self.workspace_id = workspace_id
        self.agent_id = agent_id

    def forge_token(self, payload: dict, secret: str = settings.ENCRYPTION_KEY) -> str:
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        return f"{payload_b64}.{signature}"

    async def verify_db_state(self, order_id: str) -> tuple:
        """Verify no new payments or orders were created unexpectedly."""
        res = await self.db.execute(text("SELECT COUNT(*) FROM orders"))
        order_count = res.scalar()
        res = await self.db.execute(text("SELECT COUNT(*) FROM payments"))
        payment_count = res.scalar()
        return order_count, payment_count
    
    async def get_latest_audit(self, agent_id: str) -> Optional[str]:
        res = await self.db.execute(text("SELECT id FROM audit_events WHERE agent_id = :aid ORDER BY created_at DESC LIMIT 1"), {"aid": agent_id})
        return res.scalar()

    async def execute_scenario(
        self,
        scenario_id: str,
        attack_class: str,
        input_summary: str,
        endpoint: str,
        method: str,
        payload: dict,
        expected_status: int,
        headers: dict = None
    ) -> ScenarioResult:
        import time
        start = time.time()
        
        # Get baseline DB state
        orders_before, payments_before = await self.verify_db_state("")
        
        if method.upper() == "POST":
            response = await self.client.request(
                method,
                endpoint,
                json=payload,
                headers=headers
            )
            if response.status_code >= 400:
                print(f"\nDEBUG: Execution resulted in error: {response.status_code} - {response.text}")
        elif method.upper() == "GET":
            response = await self.client.get(endpoint, headers=headers)
            
        duration_ms = (time.time() - start) * 1000
        
        # Verify DB hasn't mutated improperly if it was supposed to fail
        orders_after, payments_after = await self.verify_db_state("")
        
        db_mutated = False
        if expected_status >= 400:
            if orders_after > orders_before or payments_after > payments_before:
                db_mutated = True
                
        audit_id = await self.get_latest_audit(self.agent_id)
        
        passed = (response.status_code == expected_status) and not db_mutated

        return ScenarioResult(
            scenario_id=scenario_id,
            attack_class=attack_class,
            input_summary=input_summary,
            runtime_path=endpoint,
            expected_result=expected_status,
            observed_result=response.status_code,
            gate_decision=None,
            order_created=(orders_after > orders_before),
            payment_created=(payments_after > payments_before),
            audit_event_id=audit_id,
            duration_ms=duration_ms,
            passed=passed
        )
