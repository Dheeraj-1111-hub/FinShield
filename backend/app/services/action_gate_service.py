from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.gate import GateDecision, DecisionResult, ActionRiskClass, ApprovalRequest, ApprovalStatus
from app.models.agent import Agent, AgentStatus
from app.models.intent import Intent, IntentStatus
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.risk import RiskAssessment, RiskLevel
from app.services.investigation_service import InvestigationService
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
from app.schemas.investigation import SecurityEventCreate
from app.core.gate_crypto import GateCrypto
from app.schemas.execution_context import SignedGateDecision
import enum

class PolicyAction(str, enum.Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"

class GateEvaluator:
    @staticmethod
    def aggregate_gate_decision(
        agent: Agent,
        intent: Optional[Intent],
        authority: Optional[DelegatedAuthority],
        policy_action: Optional[PolicyAction],
        risk: Optional[RiskAssessment],
        transaction: Optional[Dict[str, Any]] = None,
        workspace_config: Optional[Dict[str, Any]] = None,
        is_revalidation: bool = False,
        alignment_result: Optional[str] = None,
        alignment_signals: Optional[List[Dict[str, Any]]] = None,
        action_type: Optional[str] = None
    ) -> tuple[DecisionResult, List[str], Optional[str]]:
        
        reasons = []
        
        # 1. Hard Blocks
        if agent.status == AgentStatus.REVOKED:
            reasons.append("AGENT_REVOKED")
        elif agent.status == AgentStatus.PAUSED:
            reasons.append("AGENT_PAUSED")
            
        if intent:
            if intent.status == IntentStatus.REVOKED:
                reasons.append("INTENT_REVOKED")
            elif intent.status == IntentStatus.EXPIRED:
                reasons.append("INTENT_EXPIRED")
                
        # ── Currency Resolution ──────────────────────────────────────────────────
        tx_amount = float(transaction["amount"]) if transaction and transaction.get("amount") is not None else None
        tx_currency = (transaction.get("currency") or "").upper() if transaction and transaction.get("currency") else None
        agent_currency = (agent.currency or "").upper() if agent and agent.currency else None
        auth_currency = (authority.currency or "").upper() if authority and authority.currency else None

        if authority:
            if authority.status == AuthorityStatus.REVOKED:
                reasons.append("AUTHORITY_REVOKED")
            elif authority.status == AuthorityStatus.EXPIRED:
                reasons.append("AUTHORITY_EXPIRED")
            
            # Check currency mismatch between transaction and authority
            if tx_currency and auth_currency and tx_currency != auth_currency:
                reasons.append("CURRENCY_MISMATCH")

            # Check transaction limits if authority and transaction exist
            if tx_amount is not None:
                if authority.monetary_limit and (not tx_currency or not auth_currency or tx_currency == auth_currency):
                    if tx_amount > authority.monetary_limit:
                        reasons.append("AUTHORITY_EXCEEDED")

        # Check agent-level maximum transaction amount
        if agent and agent.max_transaction_amount and tx_amount is not None:
            if tx_currency and agent_currency and tx_currency != agent_currency:
                if "CURRENCY_MISMATCH" not in reasons:
                    reasons.append("CURRENCY_MISMATCH")
            elif not tx_currency or not agent_currency or tx_currency == agent_currency:
                if tx_amount > agent.max_transaction_amount:
                    if "AUTHORITY_EXCEEDED" not in reasons:
                        reasons.append("AUTHORITY_EXCEEDED")
                    
        if policy_action == PolicyAction.BLOCK:
            reasons.append("POLICY_BLOCK")
            
        if risk and risk.risk_level == RiskLevel.CRITICAL:
            reasons.append("RISK_CRITICAL")

        # Intent alignment enforcement:
        from app.models.intent import IntentType

        SIDE_EFFECTING_COMMERCE_ACTIONS = {
            "create_cart", "add_to_cart", "checkout", "pay_order",
            "CREATE_CART", "ADD_TO_CART", "ADD_CART_ITEM", "MANAGE_CART",
            "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        }

        any_signal_misaligned = alignment_signals and any(
            s.get("status") == "MISALIGNED" for s in alignment_signals
        )

        if action_type in SIDE_EFFECTING_COMMERCE_ACTIONS:
            # Categorically prohibit purchase side effects if intent is read/search-only
            is_search_only_intent = False
            if intent:
                from app.services.intent_extractor import _is_search_only_or_prohibits_purchase
                if intent.natural_language_request and _is_search_only_or_prohibits_purchase(intent.natural_language_request):
                    is_search_only_intent = True
                elif intent.structured_constraints:
                    is_search_only_intent = bool(
                        intent.structured_constraints.get("search_only") or
                        intent.structured_constraints.get("read_only") or
                        ("create_cart" in (intent.structured_constraints.get("prohibited_actions") or []))
                    )
            if is_search_only_intent:
                reasons.append("INTENT_MISALIGNED_SEARCH_ONLY")
            elif alignment_result is not None:
                # 1. Fail closed on missing intent during authoritative runtime evaluation
                if not intent:
                    reasons.append("INTENT_MISSING")
                # 2. Fail closed on unevaluable intent alignment
                elif alignment_result in ("NOT EVALUATED", "UNKNOWN"):
                    reasons.append("INTENT_NOT_EVALUATED")

        if alignment_result == "MISALIGNED" or any_signal_misaligned:
            if "INTENT_MISALIGNED" not in reasons and "INTENT_MISALIGNED_SEARCH_ONLY" not in reasons:
                reasons.append("INTENT_MISALIGNED")

        if len(reasons) > 0:
            if "INTENT_MISALIGNED_SEARCH_ONLY" in reasons:
                exp = f"Action '{action_type}' is prohibited: Intent is strictly read/search-only and categorically forbids cart creation, cart modification, checkout, order creation, and payment."
            elif "INTENT_MISSING" in reasons:
                exp = f"Action '{action_type}' blocked: Side-effecting commerce actions require authoritative intent, but none was bound."
            elif "INTENT_NOT_EVALUATED" in reasons:
                exp = f"Action '{action_type}' blocked: Intent alignment could not be evaluated. Failing closed."
            elif "INTENT_MISALIGNED" in reasons:
                exp = f"Action '{action_type}' blocked: Action or parameters violate intent constraints."
            else:
                exp = f"Blocked due to hard constraints ({', '.join(reasons)})"
            return DecisionResult.BLOCK, reasons, exp
            
        # 2. Reviews
        if policy_action == PolicyAction.REVIEW:
            reasons.append("POLICY_REVIEW")
            
        if risk and risk.risk_level == RiskLevel.HIGH:
            reasons.append("RISK_HIGH")
            
        # Check approval thresholds from authority, agent, and intent
        # Applies when action is a payment execution action, or if action_type is not specified
        is_payment_action = action_type is None or action_type in ["pay_order", "EXECUTE_PAYMENT", "PAY_ORDER"]
        if is_payment_action and tx_amount is not None:
            # Authority approval threshold
            if authority and authority.approval_threshold and (not tx_currency or not auth_currency or tx_currency == auth_currency):
                if tx_amount > authority.approval_threshold:
                    reasons.append("APPROVAL_THRESHOLD_EXCEEDED")

            # Agent approval threshold
            if agent and agent.approval_threshold and (not tx_currency or not agent_currency or tx_currency == agent_currency):
                if tx_amount > agent.approval_threshold:
                    if "APPROVAL_THRESHOLD_EXCEEDED" not in reasons:
                        reasons.append("APPROVAL_THRESHOLD_EXCEEDED")

            if intent and intent.structured_constraints:
                intent_approval = intent.structured_constraints.get("approval")
                if intent_approval:
                    thresh = intent_approval.get("approval_required_above")
                    if thresh is not None and tx_amount > thresh:
                        if "APPROVAL_THRESHOLD_EXCEEDED" not in reasons:
                            reasons.append("APPROVAL_THRESHOLD_EXCEEDED")
                    elif intent_approval.get("approval_required") and thresh is None:
                        if "APPROVAL_REQUIRED" not in reasons:
                            reasons.append("APPROVAL_REQUIRED")
                
        if len(reasons) > 0:
            # If this is a revalidation (after an approval), we don't return REVIEW again for the same threshold.
            # But wait, revalidation shouldn't flag REVIEW for things that were just approved, unless we pass a flag.
            if is_revalidation:
                # Filter out the reasons that were already approved
                # In a simpler approach, if revalidation hits REVIEW, we consider it ALLOWED (since it was just approved).
                pass
            else:
                return DecisionResult.REVIEW, reasons, "Review required based on risk or thresholds"
            
        # 3. Allow
        return DecisionResult.ALLOW, ["OK"], "Action allowed"


class ActionGateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        workspace_id: str,
        agent_id: str,
        agent_run_id: str,
        agent_action_id: str,
        intent_id: Optional[str] = None,
        authority_id: Optional[str] = None,
        policy_evaluation_id: Optional[str] = None,
        risk_assessment_id: Optional[str] = None,
        transaction: Optional[Dict[str, Any]] = None,
        is_revalidation: bool = False,
        approval_id: Optional[str] = None,
        alignment_result: Optional[str] = None,
        alignment_signals: Optional[List[Dict[str, Any]]] = None,
        action_type: Optional[str] = None,
        supersedes_decision_id: Optional[str] = None
    ) -> GateDecision:
        
        # Resolve entities
        agent = await self.db.get(Agent, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        intent = None
        if intent_id:
            intent = await self.db.get(Intent, intent_id)
            
        authority = None
        if authority_id:
            authority = await self.db.get(DelegatedAuthority, authority_id)
            
        risk = None
        if risk_assessment_id:
            risk = await self.db.get(RiskAssessment, risk_assessment_id)
            
        # Evaluate policies using the policy engine
        policy_action = PolicyAction.ALLOW
        if transaction and transaction.get("amount"):
            from app.schemas.policy import PolicyEvaluationRequest, DecisionType
            from app.services.policy_service import evaluate_policies
            req = PolicyEvaluationRequest(
                agent_id=agent_id,
                amount=transaction["amount"],
                currency=transaction.get("currency") or (authority.currency if authority else "USD"),
                merchant_id=transaction.get("merchant_id"),
                capabilities=agent.capabilities or []
            )
            try:
                pol_resp = await evaluate_policies(self.db, workspace_id, req)
                if pol_resp.decision == DecisionType.BLOCK:
                    policy_action = PolicyAction.BLOCK
                elif pol_resp.decision == DecisionType.REVIEW:
                    policy_action = PolicyAction.REVIEW
            except Exception:
                # Dependency Failure Safety: Fail closed on policy engine failure
                policy_action = PolicyAction.BLOCK
        
        # Aggregate decision deterministically
        decision, reasons, explanation = GateEvaluator.aggregate_gate_decision(
            agent=agent,
            intent=intent,
            authority=authority,
            policy_action=policy_action,
            risk=risk,
            transaction=transaction,
            is_revalidation=is_revalidation,
            alignment_result=alignment_result,
            alignment_signals=alignment_signals,
            action_type=action_type
        )

        # Enforce that revalidation requires a valid, non-rejected, unconsumed approval request
        if is_revalidation and approval_id:
            appr_record = await self.db.get(ApprovalRequest, approval_id)
            if not appr_record or appr_record.status in [ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED, ApprovalStatus.PENDING, ApprovalStatus.CONSUMED, ApprovalStatus.CANCELLED]:
                status_str = appr_record.status.value if appr_record else "NOT_FOUND"
                decision = DecisionResult.BLOCK
                reasons = ["APPROVAL_INVALID_STATE"]
                explanation = f"Approval is not in APPROVED state (current: {status_str}). Cannot issue revalidated decision."
        
        # Create Snapshot
        snapshot = {
            "agent": {"status": agent.status.value},
            "intent": {"status": intent.status.value if intent else None},
            "authority": {"status": authority.status.value if authority else None, "limit": authority.monetary_limit if authority else None},
            "policy": {"decision": policy_action.value},
            "risk": {"level": risk.risk_level.value if risk else None, "score": risk.risk_score if risk else None}
        }
        
        new_decision = GateDecision(
            id=f"gdec_{uuid.uuid4().hex}",
            workspace_id=workspace_id,
            agent_id=agent_id,
            agent_run_id=agent_run_id,
            agent_action_id=agent_action_id,
            intent_id=intent_id,
            intent_version=intent.version if intent else None,
            authority_id=authority_id,
            authority_version=authority.version if authority else None,
            policy_evaluation_id=policy_evaluation_id,
            risk_assessment_id=risk_assessment_id,
            decision=decision,
            reason_codes=reasons,
            explanation=explanation,
            required_approval=(decision == DecisionResult.REVIEW),
            approval_id=approval_id,
            supersedes_decision_id=supersedes_decision_id,
            evaluation_snapshot=snapshot,
            valid_until=datetime.now(timezone.utc) + timedelta(minutes=5),
            nonce=f"n_{uuid.uuid4().hex}"
        )
        
        self.db.add(new_decision)
        
        severity = EventSeverity.INFO
        if decision == DecisionResult.BLOCK:
            severity = EventSeverity.CRITICAL
        elif decision == DecisionResult.REVIEW:
            severity = EventSeverity.HIGH

        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type=f"GATE_DECISION_{decision.value}",
            event_category=EventCategory.GATE,
            severity=severity,
            actor_type=ActorType.AGENT if agent_id else ActorType.SYSTEM,
            actor_id=agent_id,
            agent_id=agent_id,
            agent_run_id=agent_run_id,
            agent_action_id=agent_action_id,
            entity_type="GATE_DECISION",
            entity_id=new_decision.id,
            payload={"reasons": reasons, "explanation": explanation, "is_revalidation": is_revalidation, "action_type": action_type}
        )
        
        if decision == DecisionResult.BLOCK:
            await audit_service.record_event(
                workspace_id=workspace_id,
                event_type="ACTION_BLOCKED",
                event_category=EventCategory.GATE,
                severity=EventSeverity.CRITICAL,
                actor_type=ActorType.AGENT if agent_id else ActorType.SYSTEM,
                actor_id=agent_id,
                agent_id=agent_id,
                agent_run_id=agent_run_id,
                agent_action_id=agent_action_id,
                entity_type="GATE_DECISION",
                entity_id=new_decision.id,
                payload={"action_type": action_type, "reasons": reasons, "explanation": explanation}
            )
        
        # If review is required and it's not a revalidation, create or reuse approval request
        if decision == DecisionResult.REVIEW and not is_revalidation:
            # Check for existing PENDING approval request for this run to prevent duplicates
            stmt_existing = (
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.workspace_id == workspace_id,
                    ApprovalRequest.agent_run_id == agent_run_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING
                )
                .order_by(ApprovalRequest.created_at.desc())
            )
            res_existing = await self.db.execute(stmt_existing)
            existing_approvals = res_existing.scalars().all()
            matched_appr = None
            req_order_id = transaction.get("order_id") if transaction else None
            req_amount = transaction.get("amount") if transaction else None
            req_currency = transaction.get("currency") if transaction else None

            for ea in existing_approvals:
                ea_tx = ea.transaction_data or {}
                # Match by order_id if present
                if req_order_id and ea_tx.get("order_id") == req_order_id:
                    matched_appr = ea
                    break
                # Match by exact action
                if ea.agent_action_id == agent_action_id:
                    matched_appr = ea
                    break
                # Match by run + amount + currency if order_id not set
                if not req_order_id and not ea_tx.get("order_id") and ea.amount == req_amount and ea.currency == req_currency:
                    matched_appr = ea
                    break

            if matched_appr:
                new_decision.approval_id = matched_appr.id
            else:
                approval = ApprovalRequest(
                    id=f"appr_{uuid.uuid4().hex}",
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    agent_run_id=agent_run_id,
                    agent_action_id=agent_action_id,
                    gate_decision_id=new_decision.id,
                    requested_by="SYSTEM_GATE",
                    status=ApprovalStatus.PENDING,
                    reason=explanation,
                    risk_score=risk.risk_score if risk else None,
                    amount=transaction.get("amount") if transaction else None,
                    currency=transaction.get("currency") if transaction else None,
                    transaction_data=transaction,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                )
                self.db.add(approval)
                new_decision.approval_id = approval.id
                
                await audit_service.record_event(
                    workspace_id=workspace_id,
                    event_type="APPROVAL_REQUESTED",
                    event_category=EventCategory.APPROVAL,
                    severity=EventSeverity.NOTICE,
                    actor_type=ActorType.AGENT if agent_id else ActorType.SYSTEM,
                    actor_id=agent_id,
                    agent_id=agent_id,
                    agent_run_id=agent_run_id,
                    agent_action_id=agent_action_id,
                    entity_type="APPROVAL",
                    entity_id=approval.id,
                    payload={"agent_id": agent_id, "gate_decision_id": new_decision.id}
                )
            
        # Trigger Security Event and Investigation if BLOCKED or risk is CRITICAL
        if decision == DecisionResult.BLOCK or (risk and risk.risk_level == RiskLevel.CRITICAL):
            inv_svc = InvestigationService(self.db)
            severity = "CRITICAL" if decision == DecisionResult.BLOCK else "HIGH"
            event_type = "ACTION_BLOCKED" if decision == DecisionResult.BLOCK else "CRITICAL_RISK_DETECTED"
            await inv_svc.create_security_event(SecurityEventCreate(
                workspace_id=workspace_id,
                agent_id=agent_id,
                agent_run_id=agent_run_id,
                agent_action_id=agent_action_id,
                correlation_key=f"gate_{agent_action_id}",
                event_type=event_type,
                severity=severity,
                source_type="ACTION_GATE",
                source_id=new_decision.id,
                payload={
                    "title": f"{event_type} - {agent_id}",
                    "description": explanation,
                    "gate_decision_id": new_decision.id, 
                    "reasons": reasons, 
                    "snapshot": snapshot
                }
            ))

            if decision == DecisionResult.BLOCK:
                await inv_svc.ensure_investigation_for_blocked_action(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    agent_run_id=agent_run_id,
                    agent_action_id=agent_action_id,
                    gate_decision_id=new_decision.id,
                    action_type=action_type,
                    explanation=explanation,
                    reasons=reasons,
                    snapshot=snapshot,
                    intent_id=intent_id,
                    authority_id=authority_id,
                    risk_assessment_id=risk_assessment_id
                )

        await self.db.commit()
        await self.db.refresh(new_decision)
        
        return new_decision

    def issue_token(self, decision: GateDecision, action_type: str, transaction: Optional[Dict[str, Any]] = None) -> str:
        amount = transaction.get("amount") if transaction else None
        currency = transaction.get("currency") if transaction else None
        
        target_identity = None
        if transaction:
            target_identity = transaction.get("product_id") or transaction.get("order_id") or transaction.get("cart_id")
            
        action_params = {k: v for k, v in transaction.items() if k not in ["amount", "currency", "product_id", "order_id", "cart_id"]} if transaction else None
        
        signed_decision = SignedGateDecision(
            decision_id=decision.id,
            workspace_id=decision.workspace_id,
            agent_id=decision.agent_id,
            agent_run_id=decision.agent_run_id,
            agent_action_id=decision.agent_action_id,
            action_type=action_type,
            target_resource=action_type.split("_")[-1] if "_" in action_type else action_type,
            intent_id=decision.intent_id,
            intent_version=decision.intent_version,
            authority_id=decision.authority_id,
            authority_version=decision.authority_version,
            policy_version=None, # TBD if policy version is tracked
            risk_assessment_id=decision.risk_assessment_id,
            amount=amount,
            currency=currency,
            target_identity=target_identity,
            action_parameters=action_params,
            decision=decision.decision.value,
            issued_at=datetime.now(timezone.utc),
            expires_at=decision.valid_until or (datetime.now(timezone.utc) + timedelta(minutes=5)),
            nonce=decision.nonce or f"n_{uuid.uuid4().hex}"
        )
        return GateCrypto.generate_token(signed_decision)

