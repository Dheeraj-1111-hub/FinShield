from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from app.models.gate import ApprovalRequest, ApprovalStatus, GateDecision, DecisionResult
from app.services.action_gate_service import ActionGateService
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService

class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_approval(self, approval_id: str, workspace_id: str) -> ApprovalRequest:
        result = await self.db.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.workspace_id == workspace_id
            )
        )
        approval = result.scalars().first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")
        return approval

    async def approve(
        self,
        approval_id: str,
        workspace_id: str,
        user_id: str,
        expected_order_id: Optional[str] = None,
        expected_amount: Optional[float] = None,
        expected_currency: Optional[str] = None,
        expected_agent_id: Optional[str] = None,
        expected_workspace_id: Optional[str] = None,
    ) -> GateDecision:
        approval = await self.get_approval(approval_id, workspace_id)

        # 1. Workspace binding check
        if expected_workspace_id and expected_workspace_id != approval.workspace_id:
            raise HTTPException(status_code=400, detail="Workspace ID mismatch")
        
        # 2. Status check (reject duplicate / replay)
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")
            
        # 3. Expiration check
        if approval.expires_at and approval.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            approval.status = ApprovalStatus.EXPIRED
            await self.db.commit()
            raise HTTPException(status_code=400, detail="Approval has expired")

        # 4. Pending GateDecision verification
        gate_decision = await self.db.get(GateDecision, approval.gate_decision_id)
        if not gate_decision:
            raise HTTPException(status_code=404, detail="Original gate decision not found")
        if gate_decision.decision != DecisionResult.REVIEW or not gate_decision.required_approval:
            raise HTTPException(status_code=400, detail="Gate decision does not require approval")
        if gate_decision.consumed_at is not None:
            raise HTTPException(status_code=400, detail="Gate decision has already been consumed")
        if gate_decision.workspace_id != approval.workspace_id:
            raise HTTPException(status_code=400, detail="Gate decision workspace mismatch")
        if gate_decision.agent_id != approval.agent_id:
            raise HTTPException(status_code=400, detail="Gate decision agent mismatch")

        # 5. Agent binding check
        if expected_agent_id and expected_agent_id != approval.agent_id:
            raise HTTPException(status_code=400, detail="Agent ID mismatch")

        # 6. Amount & currency binding check
        if expected_amount is not None and approval.amount is not None:
            if abs(float(expected_amount) - float(approval.amount)) > 0.01:
                raise HTTPException(status_code=400, detail=f"Amount mismatch: expected {approval.amount}, got {expected_amount}")
        if expected_currency and approval.currency:
            if expected_currency.strip().upper() != approval.currency.strip().upper():
                raise HTTPException(status_code=400, detail="Currency mismatch")

        # 7. Bound Order verification
        tx_data = approval.transaction_data if isinstance(approval.transaction_data, dict) else {}
        bound_order_id = tx_data.get("order_id")
        if expected_order_id and bound_order_id and expected_order_id != bound_order_id:
            raise HTTPException(status_code=400, detail=f"Order ID mismatch: bound to {bound_order_id}, got {expected_order_id}")
        
        if bound_order_id:
            from app.models.commerce import Order, OrderStatus
            order = await self.db.get(Order, bound_order_id)
            if not order:
                raise HTTPException(status_code=404, detail="Bound order not found")
            if order.workspace_id != approval.workspace_id:
                raise HTTPException(status_code=400, detail="Bound order workspace mismatch")
            if order.agent_id and order.agent_id != approval.agent_id:
                raise HTTPException(status_code=400, detail="Bound order agent mismatch")
            if order.status == OrderStatus.PAID:
                raise HTTPException(status_code=400, detail="Bound order is already paid")
            if order.status == OrderStatus.CANCELLED:
                raise HTTPException(status_code=400, detail="Bound order has been cancelled")
            if approval.amount is not None and abs(float(order.total) - float(approval.amount)) > 0.01:
                raise HTTPException(status_code=400, detail=f"Approval amount mismatch with order: order {order.total}, approval {approval.amount}")
            if approval.currency and order.currency != approval.currency:
                raise HTTPException(status_code=400, detail="Approval currency mismatch with order")
            if tx_data.get("merchant_id") and order.merchant_id != tx_data["merchant_id"]:
                raise HTTPException(status_code=400, detail="Approval merchant mismatch with bound order")

        # 8. Linked AgentRun verification & Intent Contradiction check
        intent_to_check = None
        if approval.agent_run_id:
            from app.models.agent_runtime import AgentRun, RunStatus
            run = await self.db.get(AgentRun, approval.agent_run_id)
            if run:
                if run.workspace_id != approval.workspace_id:
                    raise HTTPException(status_code=400, detail="Run workspace mismatch")
                if run.agent_id != approval.agent_id:
                    raise HTTPException(status_code=400, detail="Run agent mismatch")
                if run.status in [RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.BLOCKED]:
                    raise HTTPException(status_code=400, detail=f"Cannot approve for run in {run.status.value} state")

                from app.services.intent_extractor import _is_search_only_or_prohibits_purchase
                if run.input and _is_search_only_or_prohibits_purchase(run.input.strip()):
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot approve action: Original user intent is strictly search-only and forbids purchases."
                    )
                if run.intent_id:
                    from app.models.intent import Intent
                    intent_to_check = await self.db.get(Intent, run.intent_id)

        if not intent_to_check and gate_decision.intent_id:
            from app.models.intent import Intent
            intent_to_check = await self.db.get(Intent, gate_decision.intent_id)

        if intent_to_check:
            from app.services.intent_extractor import _is_search_only_or_prohibits_purchase
            if intent_to_check.natural_language_request and _is_search_only_or_prohibits_purchase(intent_to_check.natural_language_request):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot approve action: Original user intent is strictly search-only and forbids purchases."
                )
            if intent_to_check.structured_constraints:
                sc = intent_to_check.structured_constraints
                if sc.get("search_only") or sc.get("read_only"):
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot approve action: Original user intent is strictly search-only and forbids purchases."
                    )
                prohibited = sc.get("prohibited_actions", [])
                action_name = None
                if approval.agent_action_id:
                    from app.models.agent_runtime import AgentAction
                    action_rec = await self.db.get(AgentAction, approval.agent_action_id)
                    if action_rec:
                        action_name = action_rec.tool_name
                if action_name and any(p.lower() == action_name.lower() for p in prohibited):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Cannot approve action: Action '{action_name}' is explicitly prohibited by original user intent."
                    )

        # 9. Mark approval as APPROVED
        # Crucial: Approval does NOT capture payment by itself, and does NOT set run to RUNNING.
        # Run remains in WAITING_FOR_APPROVAL until authoritative resume_run revalidates and executes the action.
        approval.status = ApprovalStatus.APPROVED
        approval.approved_by = user_id
        approval.approved_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="APPROVAL_APPROVED",
            event_category=EventCategory.APPROVAL,
            severity=EventSeverity.INFO,
            actor_type=ActorType.USER,
            actor_id=user_id,
            entity_type="APPROVAL",
            entity_id=approval.id,
            payload={"agent_id": approval.agent_id}
        )
        
        # Trigger revalidation using the ActionGateService to produce authoritative ALLOW decision
        gate_service = ActionGateService(self.db)
        transaction = approval.transaction_data or None
        if not transaction and approval.amount:
            transaction = {"amount": approval.amount, "currency": approval.currency}
            
        new_decision = await gate_service.evaluate(
            workspace_id=workspace_id,
            agent_id=approval.agent_id,
            agent_run_id=approval.agent_run_id,
            agent_action_id=approval.agent_action_id,
            intent_id=gate_decision.intent_id,
            authority_id=gate_decision.authority_id,
            policy_evaluation_id=gate_decision.policy_evaluation_id,
            risk_assessment_id=gate_decision.risk_assessment_id,
            transaction=transaction,
            is_revalidation=True,
            approval_id=approval.id,
            supersedes_decision_id=gate_decision.id
        )

        if new_decision.decision != DecisionResult.ALLOW:
            approval.status = ApprovalStatus.PENDING
            approval.approved_by = None
            approval.approved_at = None
            await self.db.commit()
            await audit_service.record_event(
                workspace_id=workspace_id,
                event_type="APPROVAL_REVALIDATION_FAILED",
                event_category=EventCategory.APPROVAL,
                severity=EventSeverity.WARNING,
                actor_type=ActorType.USER,
                actor_id=user_id,
                entity_type="APPROVAL",
                entity_id=approval.id,
                payload={
                    "agent_id": approval.agent_id,
                    "reverted_to": ApprovalStatus.PENDING.value,
                    "reason": new_decision.explanation,
                    "reason_codes": new_decision.reason_codes or []
                }
            )
            await self.db.commit()
            raise HTTPException(
                status_code=403,
                detail=f"Action authorization failed gate revalidation: {new_decision.explanation}"
            )
        
        return new_decision

    async def reject(
        self,
        approval_id: str,
        workspace_id: str,
        user_id: str,
        expected_order_id: Optional[str] = None,
        expected_amount: Optional[float] = None,
        expected_currency: Optional[str] = None,
        expected_agent_id: Optional[str] = None,
        expected_workspace_id: Optional[str] = None,
    ) -> ApprovalRequest:
        import json
        from app.models.commerce import OrderStatus
        from app.services.commerce_service import CommerceService
        from app.schemas.execution_context import ExecutionContext

        approval = await self.get_approval(approval_id, workspace_id)

        # 1. Workspace check
        if expected_workspace_id and expected_workspace_id != approval.workspace_id:
            raise HTTPException(status_code=400, detail="Workspace ID mismatch")
        
        # 2. Status check
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

        # 3. Expiration check
        if approval.expires_at and approval.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            approval.status = ApprovalStatus.EXPIRED
            await self.db.commit()
            raise HTTPException(status_code=400, detail="Approval has expired")

        # 4. Context check
        if expected_agent_id and expected_agent_id != approval.agent_id:
            raise HTTPException(status_code=400, detail="Agent ID mismatch")
        if expected_amount is not None and approval.amount is not None:
            if abs(float(expected_amount) - float(approval.amount)) > 0.01:
                raise HTTPException(status_code=400, detail=f"Amount mismatch: expected {approval.amount}, got {expected_amount}")
        if expected_currency and approval.currency:
            if expected_currency.strip().upper() != approval.currency.strip().upper():
                raise HTTPException(status_code=400, detail="Currency mismatch")
            
        approval.status = ApprovalStatus.REJECTED
        approval.rejected_by = user_id
        approval.rejected_at = datetime.now(timezone.utc)

        # ── Approval Rejection Lifecycle: Order cleanup & inventory release ──
        # Extract associated order ID from transaction_data or linked agent action
        order_id = None
        tx_data = approval.transaction_data
        if isinstance(tx_data, str):
            try:
                tx_data = json.loads(tx_data)
            except Exception:
                tx_data = {}
        elif not isinstance(tx_data, dict):
            tx_data = {}

        bound_order_id = tx_data.get("order_id")
        if expected_order_id and bound_order_id and expected_order_id != bound_order_id:
            raise HTTPException(status_code=400, detail=f"Order ID mismatch: bound to {bound_order_id}, got {expected_order_id}")

        order_id = bound_order_id
        if not order_id and approval.agent_action_id:
            from app.models.agent_runtime import AgentAction
            act = await self.db.get(AgentAction, approval.agent_action_id)
            if act and isinstance(act.input, dict):
                order_id = act.input.get("order_id")

        if order_id:
            order = await CommerceService.get_order(self.db, workspace_id, order_id)
            if order:
                # Never cancel an already-paid order
                if order.status != OrderStatus.PAID and order.status in (OrderStatus.DRAFT, OrderStatus.PENDING_PAYMENT):
                    await CommerceService.cancel_order(
                        self.db,
                        workspace_id,
                        order.id,
                        ExecutionContext(is_human=True, is_agent=False, user_id=user_id)
                    )

        # Update linked agent run and action status
        if approval.agent_run_id:
            from app.models.agent_runtime import AgentRun, RunStatus
            run = await self.db.get(AgentRun, approval.agent_run_id)
            if run and run.status == RunStatus.WAITING_FOR_APPROVAL:
                run.status = RunStatus.BLOCKED

        if approval.agent_action_id:
            from app.models.agent_runtime import AgentAction, ActionStatus
            action = await self.db.get(AgentAction, approval.agent_action_id)
            if action and action.status == ActionStatus.PENDING_APPROVAL:
                action.status = ActionStatus.DENIED
                action.error_message = "Action was rejected by approver."
                action.completed_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(approval)
        
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="APPROVAL_REJECTED",
            event_category=EventCategory.APPROVAL,
            severity=EventSeverity.WARNING,
            actor_type=ActorType.USER,
            actor_id=user_id,
            entity_type="APPROVAL",
            entity_id=approval.id,
            payload={"agent_id": approval.agent_id}
        )
        await self.db.commit()
        
        return approval
