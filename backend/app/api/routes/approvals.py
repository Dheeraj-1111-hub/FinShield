from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, or_
from pydantic import BaseModel

from app.db.database import get_db
from app.core.dependencies import get_current_workspace, get_current_user, RequireWorkspaceRole
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.schemas.gate import ApprovalRequestResponse, GateDecisionResponse
from app.services.approval_service import ApprovalService
from app.models.gate import ApprovalRequest

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    reason: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    agent_id: Optional[str] = None
    workspace_id: Optional[str] = None


# ── Clean, auth-context-aware decision endpoint (used by agent runtime & tests) ─
@router.post("/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    if body.workspace_id and body.workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="Workspace mismatch")
    service = ApprovalService(db)
    decision_clean = body.decision.strip().upper() if body.decision else ""
    if decision_clean == "APPROVED":
        gate_decision = await service.approve(
            approval_id=approval_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_order_id=body.order_id,
            expected_amount=body.amount,
            expected_currency=body.currency,
            expected_agent_id=body.agent_id,
            expected_workspace_id=body.workspace_id,
        )
        return {
            "id": gate_decision.id,
            "approval_id": approval_id,
            "decision": gate_decision.decision.value if hasattr(gate_decision.decision, "value") else str(gate_decision.decision),
            "status": "APPROVED",
            "agent_run_id": gate_decision.agent_run_id,
            "agent_action_id": gate_decision.agent_action_id,
            "nonce": gate_decision.nonce,
            "reason_codes": gate_decision.reason_codes or [],
            "explanation": gate_decision.explanation,
            "consumed_at": str(gate_decision.consumed_at) if gate_decision.consumed_at else None,
            "intent_id": gate_decision.intent_id,
            "authority_id": gate_decision.authority_id,
            "policy_evaluation_id": gate_decision.policy_evaluation_id,
            "risk_assessment_id": gate_decision.risk_assessment_id,
            "created_at": gate_decision.created_at.isoformat() if gate_decision.created_at else None,
        }
    elif decision_clean == "REJECTED":
        approval = await service.reject(
            approval_id=approval_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_order_id=body.order_id,
            expected_amount=body.amount,
            expected_currency=body.currency,
            expected_agent_id=body.agent_id,
            expected_workspace_id=body.workspace_id,
        )
        return {
            "id": approval.id,
            "approval_id": approval.id,
            "decision": "REJECTED",
            "status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
            "agent_run_id": approval.agent_run_id,
            "agent_action_id": approval.agent_action_id,
            "nonce": None,
            "reason_codes": ["APPROVAL_REJECTED"],
            "explanation": "Approval rejected by approver",
            "consumed_at": None,
            "intent_id": None,
            "authority_id": None,
            "policy_evaluation_id": None,
            "risk_assessment_id": None,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
        }
    else:
        raise HTTPException(status_code=400, detail="decision must be 'APPROVED' or 'REJECTED'")


# ── Legacy workspace-path endpoints (kept for backwards compatibility) ──────────
@router.get("/{workspace_id}/approvals", response_model=List[ApprovalRequestResponse])
async def list_approvals(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
):
    if workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="Workspace mismatch")
    result = await db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.workspace_id == workspace.id)
        .order_by(ApprovalRequest.created_at.desc())
    )
    return list(result.scalars().all())

@router.get("/{workspace_id}/approvals/{approval_id}", response_model=ApprovalRequestResponse)
async def get_approval(
    workspace_id: str,
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
):
    if workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="Workspace mismatch")
    service = ApprovalService(db)
    return await service.get_approval(approval_id, workspace.id)

@router.post("/{workspace_id}/approvals/{approval_id}/approve", response_model=GateDecisionResponse)
async def approve_request(
    workspace_id: str,
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    if workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="Workspace mismatch")
    service = ApprovalService(db)
    return await service.approve(approval_id, workspace.id, current_user.id)

@router.post("/{workspace_id}/approvals/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    workspace_id: str,
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
):
    if workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="Workspace mismatch")
    service = ApprovalService(db)
    return await service.reject(approval_id, workspace.id, current_user.id)


# ── Action Gate Decision Detail & Evidence Inspection Endpoints ────────────────
from app.models.gate import GateDecision, DecisionResult
from app.models.agent import Agent
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.intent import Intent
from app.models.authority import DelegatedAuthority
from app.models.risk import RiskAssessment
from app.models.policy import Policy
from app.models.commerce import Order, OrderItem
from app.models.payment import Payment
from app.schemas.gate import GateDecisionDetailResponse, GateDecisionListItem
from fastapi import HTTPException


def _is_expired(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    if dt.tzinfo is not None:
        return dt < datetime.now(timezone.utc)
    return dt < datetime.now(timezone.utc).replace(tzinfo=None)


async def _build_gate_decision_details(
    db: AsyncSession,
    gd: GateDecision,
    workspace_id: str
) -> GateDecisionDetailResponse:
    # 1. Agent
    agent = None
    if gd.agent_id:
        agent_record = await db.get(Agent, gd.agent_id)
        if agent_record and agent_record.workspace_id == workspace_id:
            agent = {
                "id": agent_record.id,
                "name": agent_record.name,
                "type": agent_record.type.value if hasattr(agent_record.type, "value") else str(agent_record.type),
                "status": agent_record.status.value if hasattr(agent_record.status, "value") else str(agent_record.status),
                "capabilities": agent_record.capabilities or [],
                "created_at": agent_record.created_at.isoformat() if agent_record.created_at else None,
            }

    # 2. Agent Run
    agent_run = None
    if gd.agent_run_id:
        run_record = await db.get(AgentRun, gd.agent_run_id)
        if run_record and run_record.workspace_id == workspace_id:
            agent_run = {
                "id": run_record.id,
                "status": run_record.status.value if hasattr(run_record.status, "value") else str(run_record.status),
                "trigger_type": run_record.trigger_type,
                "input": run_record.input,
                "output": run_record.output,
                "error_code": run_record.error_code,
                "error_message": run_record.error_message,
                "started_at": run_record.started_at.isoformat() if run_record.started_at else None,
                "completed_at": run_record.completed_at.isoformat() if run_record.completed_at else None,
                "created_at": run_record.created_at.isoformat() if run_record.created_at else None,
            }

    # 3. Agent Action
    agent_action = None
    if gd.agent_action_id:
        act_record = await db.get(AgentAction, gd.agent_action_id)
        if act_record:
            agent_action = {
                "id": act_record.id,
                "tool_name": act_record.tool_name,
                "sequence_number": act_record.sequence_number,
                "status": act_record.status.value if hasattr(act_record.status, "value") else str(act_record.status),
                "input": act_record.input,
                "output": act_record.output,
                "alignment_result": act_record.alignment_result,
                "alignment_signals": act_record.alignment_signals,
                "error_code": act_record.error_code,
                "error_message": act_record.error_message,
                "created_at": act_record.created_at.isoformat() if act_record.created_at else None,
            }

    # 4. Approval Request
    approval = None
    appr_record = None
    if gd.approval_id:
        appr_record = await db.get(ApprovalRequest, gd.approval_id)
        if appr_record and appr_record.workspace_id != workspace_id:
            appr_record = None
    if not appr_record:
        # Search by gate_decision_id
        res = await db.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.gate_decision_id == gd.id,
                ApprovalRequest.workspace_id == workspace_id
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        appr_record = res.scalars().first()
    if not appr_record and gd.supersedes_decision_id:
        # Check parent decision's approval
        res = await db.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.gate_decision_id == gd.supersedes_decision_id,
                ApprovalRequest.workspace_id == workspace_id
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        appr_record = res.scalars().first()

    if appr_record:
        approval = {
            "id": appr_record.id,
            "status": appr_record.status.value if hasattr(appr_record.status, "value") else str(appr_record.status),
            "requested_by": appr_record.requested_by,
            "reason": appr_record.reason,
            "risk_score": appr_record.risk_score,
            "amount": appr_record.amount,
            "currency": appr_record.currency,
            "transaction_data": appr_record.transaction_data or {},
            "expires_at": appr_record.expires_at.isoformat() if appr_record.expires_at else None,
            "approved_by": appr_record.approved_by,
            "approved_at": appr_record.approved_at.isoformat() if appr_record.approved_at else None,
            "rejected_by": appr_record.rejected_by,
            "rejected_at": appr_record.rejected_at.isoformat() if appr_record.rejected_at else None,
            "created_at": appr_record.created_at.isoformat() if appr_record.created_at else None,
        }

    # 5. Intent
    intent = None
    intent_id_to_check = gd.intent_id
    if not intent_id_to_check and agent_run:
        # Check run record
        run_obj = await db.get(AgentRun, gd.agent_run_id)
        if run_obj and run_obj.intent_id:
            intent_id_to_check = run_obj.intent_id
    if not intent_id_to_check and agent_action:
        act_obj = await db.get(AgentAction, gd.agent_action_id)
        if act_obj and act_obj.intent_id:
            intent_id_to_check = act_obj.intent_id

    if intent_id_to_check:
        intent_record = await db.get(Intent, intent_id_to_check)
        if intent_record and intent_record.workspace_id == workspace_id:
            intent = {
                "id": intent_record.id,
                "title": intent_record.title,
                "natural_language_request": intent_record.natural_language_request,
                "status": intent_record.status.value if hasattr(intent_record.status, "value") else str(intent_record.status),
                "intent_type": intent_record.intent_type.value if hasattr(intent_record.intent_type, "value") else str(intent_record.intent_type),
                "structured_constraints": intent_record.structured_constraints or {},
                "version": intent_record.version,
                "created_at": intent_record.created_at.isoformat() if intent_record.created_at else None,
            }

    # 6. Authority
    authority = None
    auth_id_to_check = gd.authority_id
    if not auth_id_to_check and agent_run:
        run_obj = await db.get(AgentRun, gd.agent_run_id)
        if run_obj and run_obj.authority_id:
            auth_id_to_check = run_obj.authority_id
    if not auth_id_to_check and agent_action:
        act_obj = await db.get(AgentAction, gd.agent_action_id)
        if act_obj and act_obj.authority_id:
            auth_id_to_check = act_obj.authority_id

    if auth_id_to_check:
        auth_record = await db.get(DelegatedAuthority, auth_id_to_check)
        if auth_record and auth_record.workspace_id == workspace_id:
            authority = {
                "id": auth_record.id,
                "status": auth_record.status.value if hasattr(auth_record.status, "value") else str(auth_record.status),
                "allowed_capabilities": auth_record.allowed_capabilities or [],
                "prohibited_actions": auth_record.prohibited_actions or [],
                "monetary_limit": auth_record.monetary_limit,
                "currency": auth_record.currency,
                "approval_threshold": auth_record.approval_threshold,
                "valid_from": auth_record.valid_from.isoformat() if auth_record.valid_from else None,
                "valid_until": auth_record.valid_until.isoformat() if auth_record.valid_until else None,
                "version": auth_record.version,
            }

    # 7. Risk Assessment
    risk_assessment = None
    risk_id_to_check = gd.risk_assessment_id
    if not risk_id_to_check:
        res = await db.execute(
            select(RiskAssessment)
            .where(
                RiskAssessment.agent_action_id == gd.agent_action_id,
                RiskAssessment.workspace_id == workspace_id
            )
            .order_by(RiskAssessment.created_at.desc())
        )
        ra_first = res.scalars().first()
        if ra_first:
            risk_id_to_check = ra_first.id

    if risk_id_to_check:
        ra_record = await db.get(RiskAssessment, risk_id_to_check)
        if ra_record and ra_record.workspace_id == workspace_id:
            risk_assessment = {
                "id": ra_record.id,
                "risk_score": ra_record.risk_score,
                "risk_level": ra_record.risk_level.value if hasattr(ra_record.risk_level, "value") else str(ra_record.risk_level),
                "assessment_type": ra_record.assessment_type.value if hasattr(ra_record.assessment_type, "value") else str(ra_record.assessment_type),
                "decision_hint": ra_record.decision_hint,
                "signals": ra_record.signals or [],
                "feature_snapshot": ra_record.feature_snapshot or {},
                "model_version": ra_record.model_version,
                "scoring_version": ra_record.scoring_version,
                "status": ra_record.status.value if hasattr(ra_record.status, "value") else str(ra_record.status),
            }

    # 8. Policy Evaluation
    policy_evaluation = None
    snapshot_policy = (gd.evaluation_snapshot or {}).get("policy")
    if gd.policy_evaluation_id or snapshot_policy:
        policy_evaluation = {
            "policy_evaluation_id": gd.policy_evaluation_id,
            "policy_snapshot": snapshot_policy or {},
            "evaluation_snapshot": gd.evaluation_snapshot or {},
        }
        if gd.policy_evaluation_id:
            pol_rec = await db.get(Policy, gd.policy_evaluation_id)
            if pol_rec and pol_rec.workspace_id == workspace_id:
                policy_evaluation["policy_name"] = pol_rec.name
                policy_evaluation["policy_type"] = pol_rec.policy_type.value if hasattr(pol_rec.policy_type, "value") else str(pol_rec.policy_type)

    # 9. Order & Payment Linkage
    order = None
    payment = None

    # Derive order_id
    extracted_order_id = None
    if appr_record and appr_record.transaction_data and isinstance(appr_record.transaction_data, dict):
        extracted_order_id = appr_record.transaction_data.get("order_id")
    if not extracted_order_id and agent_action and agent_action.get("input") and isinstance(agent_action["input"], dict):
        extracted_order_id = agent_action["input"].get("order_id")
    if not extracted_order_id and agent_action and agent_action.get("output") and isinstance(agent_action["output"], dict):
        extracted_order_id = agent_action["output"].get("order_id")
    if not extracted_order_id and gd.evaluation_snapshot and isinstance(gd.evaluation_snapshot, dict):
        extracted_order_id = gd.evaluation_snapshot.get("order_id")

    # Look for Payment
    payment_record = None
    res_payments = await db.execute(
        select(Payment).where(Payment.workspace_id == workspace_id).order_by(Payment.created_at.desc())
    )
    all_ws_payments = res_payments.scalars().all()
    for p in all_ws_payments:
        meta = p.metadata_ or {}
        fs = meta.get("finshield") or {}
        if fs.get("gate_decision_id") == gd.id:
            payment_record = p
            break
        if extracted_order_id and p.order_id == extracted_order_id:
            payment_record = p
            break
        if fs.get("run_id") == gd.agent_run_id and fs.get("action_id") == gd.agent_action_id:
            payment_record = p
            break

    if payment_record:
        if not extracted_order_id and payment_record.order_id:
            extracted_order_id = payment_record.order_id
        payment = {
            "id": payment_record.id,
            "status": payment_record.status.value if hasattr(payment_record.status, "value") else str(payment_record.status),
            "amount": float(payment_record.amount),
            "currency": payment_record.currency,
            "order_id": payment_record.order_id,
            "idempotency_key": payment_record.idempotency_key,
            "payment_intent_id": payment_record.payment_intent_id,
            "failure_code": payment_record.failure_code,
            "failure_reason": payment_record.failure_reason,
            "created_at": payment_record.created_at.isoformat() if payment_record.created_at else None,
        }

    if extracted_order_id:
        order_record = await db.get(Order, extracted_order_id)
        if order_record and order_record.workspace_id == workspace_id:
            # Load items
            res_items = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order_record.id)
            )
            order_items = res_items.scalars().all()
            order = {
                "id": order_record.id,
                "status": order_record.status.value if hasattr(order_record.status, "value") else str(order_record.status),
                "subtotal": float(order_record.subtotal),
                "total": float(order_record.total),
                "currency": order_record.currency,
                "merchant_id": order_record.merchant_id,
                "payment_id": order_record.payment_id,
                "created_at": order_record.created_at.isoformat() if order_record.created_at else None,
                "items": [
                    {
                        "product_name": it.product_name_snapshot,
                        "quantity": it.quantity,
                        "unit_price": float(it.unit_price_at_order),
                        "total": float(it.total),
                    }
                    for it in order_items
                ]
            }

    # 10. Amount and Currency
    amount: Optional[float] = None
    currency: Optional[str] = None
    if appr_record and appr_record.amount is not None:
        amount = float(appr_record.amount)
        currency = appr_record.currency
    elif payment and payment.get("amount") is not None:
        amount = payment["amount"]
        currency = payment.get("currency")
    elif order and order.get("total") is not None:
        amount = order["total"]
        currency = order.get("currency")
    elif agent_action and agent_action.get("input") and isinstance(agent_action["input"], dict):
        raw_amt = agent_action["input"].get("amount")
        if raw_amt is not None:
            try:
                amount = float(raw_amt)
            except Exception:
                pass
        currency = agent_action["input"].get("currency")

    # 11. Evidence Status Map
    reasons = gd.reason_codes or []
    evidence_status: Dict[str, str] = {}

    evidence_status["agent"] = "AVAILABLE" if agent else ("NOT_CONFIGURED" if not gd.agent_id else "MISSING")
    evidence_status["agent_run"] = "AVAILABLE" if agent_run else "MISSING"
    evidence_status["agent_action"] = "AVAILABLE" if agent_action else "MISSING"

    if approval:
        evidence_status["approval"] = "AVAILABLE"
    elif gd.required_approval or (hasattr(gd.decision, "value") and gd.decision.value == "REVIEW"):
        evidence_status["approval"] = "MISSING"
    else:
        evidence_status["approval"] = "NOT_REQUIRED"

    if intent:
        if any("INTENT" in r for r in reasons):
            evidence_status["intent"] = "CHECK_FAILED"
        else:
            evidence_status["intent"] = "AVAILABLE"
    elif gd.intent_id:
        evidence_status["intent"] = "MISSING"
    else:
        evidence_status["intent"] = "NOT_CONFIGURED"

    if authority:
        if any("AUTHORITY" in r or "LIMIT" in r or "CAPABILITY" in r for r in reasons):
            evidence_status["authority"] = "CHECK_FAILED"
        else:
            evidence_status["authority"] = "AVAILABLE"
    elif gd.authority_id:
        evidence_status["authority"] = "MISSING"
    else:
        evidence_status["authority"] = "NOT_CONFIGURED"

    if risk_assessment:
        if any("RISK" in r for r in reasons):
            evidence_status["risk_assessment"] = "CHECK_FAILED"
        else:
            evidence_status["risk_assessment"] = "AVAILABLE"
    elif gd.risk_assessment_id:
        evidence_status["risk_assessment"] = "MISSING"
    elif (gd.evaluation_snapshot or {}).get("risk"):
        evidence_status["risk_assessment"] = "SNAPSHOT_ONLY"
    else:
        evidence_status["risk_assessment"] = "NOT_CONFIGURED"

    if any("POLICY" in r for r in reasons):
        evidence_status["policy_evaluation"] = "CHECK_FAILED"
    elif policy_evaluation:
        evidence_status["policy_evaluation"] = "AVAILABLE"
    else:
        evidence_status["policy_evaluation"] = "NOT_CONFIGURED"

    evidence_status["order"] = "AVAILABLE" if order else "NONE_LINKED"
    evidence_status["payment"] = "AVAILABLE" if payment else "NONE_LINKED"

    decision_val = gd.decision.value if hasattr(gd.decision, "value") else str(gd.decision)
    appr_status_val = (
        appr_record.status.value
        if appr_record and hasattr(appr_record.status, "value")
        else str(appr_record.status)
        if appr_record and appr_record.status
        else None
    )

    if appr_status_val:
        approval_lifecycle_status = appr_status_val
    elif gd.required_approval or decision_val == "REVIEW":
        approval_lifecycle_status = "PENDING"
    else:
        approval_lifecycle_status = "NOT_REQUIRED"

    now_utc = datetime.now(timezone.utc)
    if decision_val == "ALLOW":
        if gd.consumed_at:
            execution_status = "CONSUMED"
        elif _is_expired(gd.valid_until):
            execution_status = "EXPIRED"
        else:
            execution_status = "UNCONSUMED"
    elif decision_val == "REVIEW":
        if approval_lifecycle_status == "CONSUMED":
            execution_status = "RESOLVED_CONSUMED"
        elif approval_lifecycle_status == "APPROVED":
            execution_status = "RESOLVED_APPROVED"
        elif approval_lifecycle_status == "REJECTED":
            execution_status = "BLOCKED_REJECTED"
        elif approval_lifecycle_status in ("CANCELLED", "EXPIRED"):
            execution_status = "TERMINATED"
        else:
            execution_status = "PENDING_REVIEW"
    elif decision_val == "BLOCK":
        execution_status = "NOT_EXECUTABLE"
    else:
        execution_status = "UNKNOWN"

    return GateDecisionDetailResponse(
        id=gd.id,
        workspace_id=gd.workspace_id,
        agent_id=gd.agent_id,
        agent_run_id=gd.agent_run_id,
        agent_action_id=gd.agent_action_id,
        decision=decision_val,
        reason_codes=reasons,
        explanation=gd.explanation,
        required_approval=gd.required_approval or False,
        approval_id=gd.approval_id or (appr_record.id if appr_record else None),
        supersedes_decision_id=gd.supersedes_decision_id,
        valid_until=gd.valid_until,
        nonce=gd.nonce,
        consumed_at=gd.consumed_at,
        evaluation_snapshot=gd.evaluation_snapshot or {},
        created_at=gd.created_at,
        updated_at=gd.updated_at,
        amount=amount,
        currency=currency,
        execution_status=execution_status,
        approval_lifecycle_status=approval_lifecycle_status,
        agent=agent,
        agent_run=agent_run,
        agent_action=agent_action,
        approval=approval,
        intent=intent,
        authority=authority,
        risk_assessment=risk_assessment,
        policy_evaluation=policy_evaluation,
        order=order,
        payment=payment,
        evidence_status=evidence_status,
    )


gate_decisions_router = APIRouter()


@gate_decisions_router.get("/{decision_id}", response_model=GateDecisionDetailResponse)
@gate_decisions_router.get("/decisions/{decision_id}", response_model=GateDecisionDetailResponse)
@router.get("/decisions/{decision_id}", response_model=GateDecisionDetailResponse)
@router.get("/gate-decisions/{decision_id}", response_model=GateDecisionDetailResponse)
async def get_gate_decision_details(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    # 1. Check if ID matches a GateDecision directly within this workspace
    gd = await db.get(GateDecision, decision_id)
    if gd and gd.workspace_id == workspace.id:
        return await _build_gate_decision_details(db, gd, workspace.id)

    # 2. Check if ID matches an ApprovalRequest within this workspace
    appr = await db.get(ApprovalRequest, decision_id)
    if appr and appr.workspace_id == workspace.id:
        if appr.gate_decision_id:
            linked_gd = await db.get(GateDecision, appr.gate_decision_id)
            if linked_gd and linked_gd.workspace_id == workspace.id:
                return await _build_gate_decision_details(db, linked_gd, workspace.id)

    # Uniform 404 without leaking cross-workspace existence
    raise HTTPException(status_code=404, detail=f"Gate decision '{decision_id}' not found")


@gate_decisions_router.get("", response_model=List[GateDecisionListItem])
@gate_decisions_router.get("/", response_model=List[GateDecisionListItem])
@router.get("/gate-decisions", response_model=List[GateDecisionListItem])
async def list_gate_decisions(
    limit: int = 50,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    query = (
        select(
            GateDecision,
            Agent.name.label("agent_name"),
            AgentAction.tool_name.label("tool_name"),
            ApprovalRequest.id.label("matched_approval_id"),
            ApprovalRequest.status.label("matched_approval_status"),
            ApprovalRequest.amount.label("approval_amount"),
            ApprovalRequest.currency.label("approval_currency"),
            AgentAction.input.label("action_input"),
        )
        .outerjoin(Agent, GateDecision.agent_id == Agent.id)
        .outerjoin(AgentAction, GateDecision.agent_action_id == AgentAction.id)
        .outerjoin(
            ApprovalRequest,
            or_(
                GateDecision.approval_id == ApprovalRequest.id,
                GateDecision.id == ApprovalRequest.gate_decision_id,
            ),
        )
        .where(GateDecision.workspace_id == workspace.id)
    )

    if agent_id:
        query = query.where(GateDecision.agent_id == agent_id)
    if run_id:
        query = query.where(GateDecision.agent_run_id == run_id)

    query = query.order_by(GateDecision.created_at.desc()).limit(limit)

    res = await db.execute(query)
    rows = res.all()

    items: List[GateDecisionListItem] = []
    for row in rows:
        gd = row[0]
        agent_name = row[1]
        tool_name = row[2]
        matched_appr_id = row[3]
        matched_appr_status = row[4]
        appr_amt = row[5]
        appr_curr = row[6]
        action_input = row[7]

        decision_str = gd.decision.value if hasattr(gd.decision, "value") else str(gd.decision)
        status_str = (
            matched_appr_status.value
            if hasattr(matched_appr_status, "value")
            else str(matched_appr_status)
            if matched_appr_status
            else None
        )

        amount: Optional[float] = None
        currency: Optional[str] = None
        if appr_amt is not None:
            amount = float(appr_amt)
            currency = appr_curr
        elif action_input and isinstance(action_input, dict):
            raw_amt = action_input.get("amount")
            if raw_amt is not None:
                try:
                    amount = float(raw_amt)
                    currency = action_input.get("currency")
                except Exception:
                    pass
        elif gd.evaluation_snapshot and isinstance(gd.evaluation_snapshot, dict):
            tx = gd.evaluation_snapshot.get("transaction") or {}
            raw_amt = tx.get("amount")
            if raw_amt is not None:
                try:
                    amount = float(raw_amt)
                    currency = tx.get("currency")
                except Exception:
                    pass

        # Derive authoritative statuses
        decision_val = decision_str
        appr_status_val = (
            matched_appr_status.value
            if hasattr(matched_appr_status, "value")
            else str(matched_appr_status)
            if matched_appr_status
            else None
        )

        if appr_status_val:
            approval_lifecycle_status = appr_status_val
        elif gd.consumed_at:
            approval_lifecycle_status = "CONSUMED"
        elif decision_val == "ALLOW" and (gd.approval_id or matched_appr_id):
            approval_lifecycle_status = "APPROVED"
        elif gd.required_approval or decision_val == "REVIEW":
            approval_lifecycle_status = "PENDING"
        else:
            approval_lifecycle_status = "NOT_REQUIRED"

        # status_str maintains backward compatibility for existing tests
        status_str = approval_lifecycle_status if approval_lifecycle_status != "NOT_REQUIRED" else None

        now_utc = datetime.now(timezone.utc)
        if decision_val == "ALLOW":
            if gd.consumed_at:
                execution_status = "CONSUMED"
            elif _is_expired(gd.valid_until):
                execution_status = "EXPIRED"
            else:
                execution_status = "UNCONSUMED"
        elif decision_val == "REVIEW":
            if approval_lifecycle_status == "CONSUMED":
                execution_status = "RESOLVED_CONSUMED"
            elif approval_lifecycle_status == "APPROVED":
                execution_status = "RESOLVED_APPROVED"
            elif approval_lifecycle_status == "REJECTED":
                execution_status = "BLOCKED_REJECTED"
            elif approval_lifecycle_status in ("CANCELLED", "EXPIRED"):
                execution_status = "TERMINATED"
            else:
                execution_status = "PENDING_REVIEW"
        elif decision_val == "BLOCK":
            execution_status = "NOT_EXECUTABLE"
        else:
            execution_status = "UNKNOWN"

        items.append(
            GateDecisionListItem(
                id=gd.id,
                workspace_id=gd.workspace_id,
                agent_id=gd.agent_id,
                agent_name=agent_name,
                agent_run_id=gd.agent_run_id,
                agent_action_id=gd.agent_action_id,
                tool_name=tool_name,
                decision=decision_str,
                reason_codes=gd.reason_codes or [],
                explanation=gd.explanation,
                required_approval=gd.required_approval or False,
                approval_id=gd.approval_id or matched_appr_id,
                approval_status=status_str,
                approval_lifecycle_status=approval_lifecycle_status,
                execution_status=execution_status,
                consumed_at=gd.consumed_at,
                supersedes_decision_id=gd.supersedes_decision_id,
                amount=amount,
                currency=currency,
                created_at=gd.created_at,
            )
        )

    return items

