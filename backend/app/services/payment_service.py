from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import uuid

from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentUpdate
from app.services.audit_service import AuditService
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.payment_processors.sandbox import SandboxPaymentProcessor
from app.services.commerce_service import CommerceService
from app.schemas.execution_context import ExecutionContext
from app.models.commerce import Order, OrderStatus

# A simple factory since we only have the Sandbox right now.
def get_payment_processor(payment_method_type: Optional[str] = None):
    return SandboxPaymentProcessor()

async def log_payment_activity(
    db: AsyncSession,
    payment_id: str,
    workspace_id: str,
    action: str,
    actor_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    actor_type: Optional[ActorType] = None,
    details: dict = None,
    severity: EventSeverity = EventSeverity.INFO
):
    audit_service = AuditService(db)
    if not actor_type:
        if agent_id:
            actor_type = ActorType.AGENT
        elif actor_id:
            actor_type = ActorType.USER
        else:
            actor_type = ActorType.SYSTEM

    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=action.value if hasattr(action, "value") else str(action),
        event_category=EventCategory.PAYMENT,
        severity=severity,
        actor_type=actor_type,
        actor_id=actor_id or agent_id,
        agent_id=agent_id,
        entity_type="PAYMENT",
        entity_id=payment_id,
        payload=details or {}
    )

async def create_payment_intent(db: AsyncSession, workspace_id: str, payment_data: PaymentCreate, ctx: ExecutionContext) -> Payment:
    if not payment_data.order_id:
        raise HTTPException(status_code=400, detail="An order_id is required for payment creation.")
        
    # Fetch the order
    order_stmt = select(Order).where(
        Order.id == payment_data.order_id,
        Order.workspace_id == workspace_id
    )
    order_res = await db.execute(order_stmt)
    order = order_res.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=409, detail=f"Order is not payable. Current status: {order.status.value}")
        
    payment_amount = order.total
    payment_currency = order.currency

    # Enforce exact amount and currency consistency if explicitly provided in request
    if payment_data.amount is not None:
        if abs(float(payment_data.amount) - float(order.total)) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Payment amount mismatch: requested amount ({payment_data.amount}) does not match order total ({order.total})."
            )
    if payment_data.currency and payment_data.currency.strip().upper() != order.currency.strip().upper():
        raise HTTPException(
            status_code=400,
            detail=f"Payment currency mismatch: requested currency ({payment_data.currency}) does not match order currency ({order.currency})."
        )
    if payment_data.merchant_reference and payment_data.merchant_reference != order.merchant_id:
        from app.models.commerce import Merchant
        stmt_m = select(Merchant).where(Merchant.id == order.merchant_id, Merchant.workspace_id == workspace_id)
        res_m = await db.execute(stmt_m)
        m = res_m.scalar_one_or_none()
        if payment_data.merchant_reference not in (order.merchant_id, getattr(m, 'merchant_reference', None)):
            raise HTTPException(status_code=400, detail="Merchant reference mismatch with linked order merchant.")
    
    decision = None
    if ctx.is_agent:
        decision = await CommerceService._verify_gate_token(db, workspace_id, ctx, "pay_order", amount=payment_amount, currency=payment_currency, target_identity=payment_data.order_id, consume_nonce=True)
    elif order.agent_id is not None:
        # Agent-created order being paid via manual or direct API flow:
        # Enforce strict Action Gate controls. Prevent bypass!
        # Validate exact order, workspace, amount, currency, approval status, and gate decision.
        from app.models.gate import ApprovalRequest, ApprovalStatus, GateDecision, DecisionResult
        from app.models.agent_runtime import AgentAction
        import json
        from datetime import datetime, timezone

        stmt_appr = (
            select(ApprovalRequest)
            .where(
                ApprovalRequest.workspace_id == workspace_id,
                ApprovalRequest.agent_id == order.agent_id
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        res_appr = await db.execute(stmt_appr)
        candidate_approvals = res_appr.scalars().all()

        matching_appr = None
        for appr in candidate_approvals:
            tx = appr.transaction_data
            if isinstance(tx, str):
                try:
                    tx = json.loads(tx)
                except Exception:
                    tx = {}
            elif not isinstance(tx, dict):
                tx = {}

            if tx.get("order_id") == order.id:
                matching_appr = appr
                break

            if appr.agent_action_id:
                act = await db.get(AgentAction, appr.agent_action_id)
                if act and isinstance(act.input, dict) and act.input.get("order_id") == order.id:
                    matching_appr = appr
                    break

        if not matching_appr:
            raise HTTPException(
                status_code=403,
                detail="Payment denied: Agent-governed order requires an approved Action Gate review."
            )

        # Validate approval status
        if matching_appr.status == ApprovalStatus.REJECTED:
            raise HTTPException(
                status_code=403,
                detail="Payment denied: Approval for this agent order was rejected."
            )
        elif matching_appr.status == ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=403,
                detail="Payment denied: Approval for this agent order is pending review."
            )
        elif matching_appr.status in [ApprovalStatus.EXPIRED, ApprovalStatus.CANCELLED]:
            raise HTTPException(
                status_code=403,
                detail=f"Payment denied: Approval for this agent order is {matching_appr.status.value}."
            )
        elif matching_appr.status == ApprovalStatus.CONSUMED:
            raise HTTPException(
                status_code=403,
                detail="Payment denied: Approval has already been consumed."
            )
        elif matching_appr.status != ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=403,
                detail=f"Payment denied: Invalid approval status {matching_appr.status.value}."
            )

        # Validate exact amount and currency against approval
        if matching_appr.amount is not None and abs(float(matching_appr.amount) - float(payment_amount)) > 0.001:
            raise HTTPException(
                status_code=403,
                detail=f"Payment denied: Approved amount ({matching_appr.amount}) does not match order total ({payment_amount})."
            )
        if matching_appr.currency is not None and matching_appr.currency.strip().upper() != payment_currency.strip().upper():
            raise HTTPException(
                status_code=403,
                detail=f"Payment denied: Approved currency ({matching_appr.currency}) does not match order currency ({payment_currency})."
            )

        # Validate applicable gate decision
        gate_dec = await db.get(GateDecision, matching_appr.gate_decision_id)
        if not gate_dec:
            raise HTTPException(
                status_code=403,
                detail="Payment denied: Associated gate decision record not found."
            )

        if gate_dec.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Payment denied: Gate decision workspace mismatch.")
        if gate_dec.agent_id != order.agent_id:
            raise HTTPException(status_code=403, detail="Payment denied: Gate decision agent mismatch.")

        # If gate_dec was REVIEW initially, check if revalidation yielded ALLOW
        if gate_dec.decision != DecisionResult.ALLOW:
            stmt_reval = select(GateDecision).where(
                GateDecision.approval_id == matching_appr.id,
                GateDecision.decision == DecisionResult.ALLOW
            ).order_by(GateDecision.created_at.desc())
            res_reval = await db.execute(stmt_reval)
            allowed_dec = res_reval.scalars().first()
            if not allowed_dec:
                raise HTTPException(
                    status_code=403,
                    detail="Payment denied: Action Gate decision was not allowed."
                )
            gate_dec = allowed_dec

        # Check expiration if specified
        if gate_dec.valid_until:
            valid_dt = gate_dec.valid_until if gate_dec.valid_until.tzinfo else gate_dec.valid_until.replace(tzinfo=timezone.utc)
            if valid_dt < datetime.now(timezone.utc):
                raise HTTPException(status_code=403, detail="Payment denied: Gate decision has expired.")

        # Consume the approval if it was APPROVED so it cannot be re-used for other payments
        if matching_appr.status == ApprovalStatus.APPROVED:
            matching_appr.status = ApprovalStatus.CONSUMED
            await db.commit()

        class DecisionProxy:
            pass
        d_proxy = DecisionProxy()
        d_proxy.decision_id = gate_dec.id
        d_proxy.decision = gate_dec.decision.value if hasattr(gate_dec.decision, "value") else str(gate_dec.decision)
        d_proxy.risk_assessment_id = gate_dec.risk_assessment_id
        d_proxy.intent_id = gate_dec.intent_id
        d_proxy.authority_id = gate_dec.authority_id
        d_proxy.agent_run_id = gate_dec.agent_run_id
        d_proxy.agent_action_id = gate_dec.agent_action_id
        decision = d_proxy
        
    actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
    payment_agent_id = ctx.agent_id if ctx.is_agent else None
    
    # Store FINSHIELD trace in metadata
    finshield_meta = {}
    if decision:
        finshield_meta = {
            "gate_decision_id": decision.decision_id,
            "decision": decision.decision,
            "risk_assessment_id": decision.risk_assessment_id,
            "intent_id": decision.intent_id,
            "authority_id": decision.authority_id,
            "run_id": decision.agent_run_id,
            "action_id": decision.agent_action_id
        }
        if decision.risk_assessment_id:
            from app.models.risk import RiskAssessment
            ra = await db.get(RiskAssessment, decision.risk_assessment_id)
            if ra:
                finshield_meta["risk_level"] = ra.risk_level.value if hasattr(ra.risk_level, 'value') else str(ra.risk_level) if ra.risk_level else None
                finshield_meta["risk_score"] = ra.risk_score
    
    meta = payment_data.metadata_ or {}
    if finshield_meta:
        meta["finshield"] = finshield_meta
    
    # Check idempotency
    stmt = select(Payment).where(
        Payment.workspace_id == workspace_id,
        Payment.idempotency_key == payment_data.idempotency_key
    )
    result = await db.execute(stmt)
    existing_payment = result.scalar_one_or_none()
    
    if existing_payment:
        # Check if it matches logical request (order ID must match)
        if existing_payment.order_id != payment_data.order_id:
            raise HTTPException(status_code=409, detail="Idempotency key already used for a different order")
        return existing_payment

    payment = Payment(
        workspace_id=workspace_id,
        agent_id=payment_agent_id or payment_data.agent_id,
        order_id=payment_data.order_id,
        payment_intent_id=payment_data.payment_intent_id,
        idempotency_key=payment_data.idempotency_key,
        amount=payment_amount,
        currency=payment_currency,
        status=PaymentStatus.CREATED,
        payment_method_type=payment_data.payment_method_type,
        merchant_reference=payment_data.merchant_reference,
        metadata_=meta
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    await log_payment_activity(
        db,
        payment.id,
        workspace_id,
        "INTENT_CREATED",
        actor_id=actor_id,
        agent_id=payment_agent_id or payment.agent_id,
        actor_type=ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM),
        details={"amount": payment.amount, "currency": payment.currency, "order_id": payment.order_id}
    )
    await db.commit()
    return payment

async def _format_payment_row(payment, agent_name, order_status, merchant_id, merchant_name, risk_map: Optional[dict] = None):
    d = payment.__dict__.copy()
    d.pop('_sa_instance_state', None)
    d['agent_name'] = agent_name
    d['order_status'] = order_status.value if order_status else None
    d['merchant_id'] = merchant_id
    d['merchant_name'] = merchant_name
    
    meta = d.get('metadata_') or {}
    fs = meta.get('finshield', {})
    d['gate_decision_id'] = fs.get('gate_decision_id')
    d['gate_decision'] = fs.get('decision')
    ra_id = fs.get('risk_assessment_id')
    d['risk_assessment_id'] = ra_id
    d['intent_id'] = fs.get('intent_id')
    d['authority_id'] = fs.get('authority_id')
    d['run_id'] = fs.get('run_id')
    d['action_id'] = fs.get('action_id')

    if risk_map and ra_id and ra_id in risk_map:
        ra = risk_map[ra_id]
        d['risk_level'] = ra.risk_level.value if hasattr(ra.risk_level, 'value') else str(ra.risk_level) if ra.risk_level else None
        d['risk_score'] = ra.risk_score
    else:
        d['risk_level'] = fs.get('risk_level')
        d['risk_score'] = fs.get('risk_score')

    return d

async def get_payments(db: AsyncSession, workspace_id: str) -> List[dict]:
    from app.models.agent import Agent
    from app.models.commerce import Merchant
    from app.models.risk import RiskAssessment
    stmt = (
        select(Payment, Agent.name, Order.status, Merchant.id, Merchant.name)
        .outerjoin(Agent, Payment.agent_id == Agent.id)
        .outerjoin(Order, Payment.order_id == Order.id)
        .outerjoin(Merchant, Order.merchant_id == Merchant.id)
        .where(Payment.workspace_id == workspace_id)
        .order_by(Payment.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    ra_ids = set()
    for p, an, os, mid, mn in rows:
        meta = p.metadata_ or {}
        ra_id = meta.get('finshield', {}).get('risk_assessment_id')
        if ra_id:
            ra_ids.add(ra_id)

    risk_map = {}
    if ra_ids:
        ra_res = await db.execute(select(RiskAssessment).where(RiskAssessment.id.in_(list(ra_ids))))
        for ra in ra_res.scalars().all():
            risk_map[ra.id] = ra

    return [await _format_payment_row(p, an, os, mid, mn, risk_map) for p, an, os, mid, mn in rows]

async def get_payment_metrics(db: AsyncSession, workspace_id: str, currency: str = "INR") -> dict:
    stmt = select(Payment.status, Payment.amount).where(
        Payment.workspace_id == workspace_id,
        Payment.currency == currency
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    metrics = {
        "total_volume": 0,
        "transactions": len(rows),
        "captured_count": 0,
        "failed_count": 0,
        "failed_value": 0
    }
    
    for status, amount in rows:
        if status == PaymentStatus.CAPTURED:
            metrics["captured_count"] += 1
            metrics["total_volume"] += amount
        elif status == PaymentStatus.FAILED:
            metrics["failed_count"] += 1
            metrics["failed_value"] += amount
            
    return metrics

async def get_payment(db: AsyncSession, workspace_id: str, payment_id: str) -> Payment:
    stmt = select(Payment).where(Payment.id == payment_id, Payment.workspace_id == workspace_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

async def get_payment_dict(db: AsyncSession, workspace_id: str, payment_id: str) -> dict:
    from app.models.agent import Agent
    from app.models.commerce import Merchant
    from app.models.risk import RiskAssessment
    stmt = (
        select(Payment, Agent.name, Order.status, Merchant.id, Merchant.name)
        .outerjoin(Agent, Payment.agent_id == Agent.id)
        .outerjoin(Order, Payment.order_id == Order.id)
        .outerjoin(Merchant, Order.merchant_id == Merchant.id)
        .where(Payment.workspace_id == workspace_id, Payment.id == payment_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    p, an, os, mid, mn = row
    risk_map = {}
    ra_id = (p.metadata_ or {}).get('finshield', {}).get('risk_assessment_id')
    if ra_id:
        ra = await db.get(RiskAssessment, ra_id)
        if ra:
            risk_map[ra_id] = ra

    return await _format_payment_row(p, an, os, mid, mn, risk_map)

async def authorize_payment(db: AsyncSession, workspace_id: str, payment_id: str, ctx: ExecutionContext) -> Payment:
    payment = await get_payment(db, workspace_id, payment_id)
    
    if payment.status != PaymentStatus.CREATED:
        raise HTTPException(status_code=409, detail=f"Cannot authorize payment in status {payment.status.value}")

    # Downstream gate token verification with exact context binding
    if ctx.is_agent:
        await CommerceService._verify_gate_token(
            db, workspace_id, ctx, "pay_order",
            amount=payment.amount,
            currency=payment.currency,
            target_identity=payment.order_id,
            consume_nonce=False
        )

    # Enforce exact amount, currency, and merchant consistency with linked order
    if payment.order_id:
        order = await db.get(Order, payment.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Linked order not found for payment authorization")
        if order.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Linked order workspace mismatch")
        if order.status == OrderStatus.PAID:
            raise HTTPException(status_code=409, detail="Linked order is already paid")
        if abs(float(payment.amount) - float(order.total)) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Payment authorization denied: Payment amount ({payment.amount}) does not match linked order total ({order.total})."
            )
        if payment.currency.strip().upper() != order.currency.strip().upper():
            raise HTTPException(
                status_code=400,
                detail=f"Payment authorization denied: Payment currency ({payment.currency}) does not match linked order currency ({order.currency})."
            )
        if payment.merchant_reference and payment.merchant_reference != order.merchant_id:
            from app.models.commerce import Merchant
            stmt_m = select(Merchant).where(Merchant.id == order.merchant_id, Merchant.workspace_id == workspace_id)
            res_m = await db.execute(stmt_m)
            m = res_m.scalar_one_or_none()
            if payment.merchant_reference not in (order.merchant_id, getattr(m, 'merchant_reference', None)):
                raise HTTPException(status_code=400, detail="Merchant reference mismatch between payment and linked order.")

        # Revalidate gate decision immediately prior to authorization if agent-governed
        if (order.agent_id or payment.agent_id) and not ctx.is_agent:
            gate_meta = (payment.metadata_ or {}).get("finshield", {})
            gdec_id = gate_meta.get("gate_decision_id")
            if not gdec_id:
                raise HTTPException(status_code=403, detail="Payment authorization denied: Agent-governed order is missing gate decision context.")
            from app.models.gate import GateDecision, DecisionResult
            from datetime import timezone
            gate_dec = await db.get(GateDecision, gdec_id)
            if not gate_dec or gate_dec.workspace_id != workspace_id or gate_dec.decision != DecisionResult.ALLOW:
                raise HTTPException(status_code=403, detail="Payment authorization denied: Gate decision is not ALLOW or workspace mismatch.")
            if gate_dec.valid_until:
                v_dt = gate_dec.valid_until if gate_dec.valid_until.tzinfo else gate_dec.valid_until.replace(tzinfo=timezone.utc)
                if v_dt < datetime.now(timezone.utc):
                    raise HTTPException(status_code=403, detail="Payment authorization denied: Gate decision has expired.")
        
    actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
    
    payment_agent_id = payment.agent_id or (ctx.agent_id if ctx.is_agent else None)
    payment_actor_type = ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)

    payment.status = PaymentStatus.REQUIRES_AUTHORIZATION
    await log_payment_activity(
        db,
        payment.id,
        workspace_id,
        "AUTHORIZATION_REQUESTED",
        actor_id=actor_id,
        agent_id=payment_agent_id,
        actor_type=payment_actor_type,
        details={"amount": payment.amount, "currency": payment.currency}
    )
    await db.commit()
    
    processor = get_payment_processor(payment.payment_method_type)
    success, failure_code, failure_reason = await processor.authorize(payment)
    
    if success:
        payment.status = PaymentStatus.AUTHORIZED
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "AUTHORIZED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"amount": payment.amount, "currency": payment.currency}
        )
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = failure_code
        payment.failure_reason = failure_reason
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "FAILED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"code": failure_code, "reason": failure_reason, "amount": payment.amount, "currency": payment.currency},
            severity=EventSeverity.WARNING
        )
        if payment.order_id:
            await CommerceService.mark_order_payment_failed(db, payment.order_id, payment.id)
        
    await db.commit()
    await db.refresh(payment)
    return payment

async def capture_payment(db: AsyncSession, workspace_id: str, payment_id: str, ctx: ExecutionContext) -> Payment:
    payment = await get_payment(db, workspace_id, payment_id)
    
    if payment.status != PaymentStatus.AUTHORIZED:
        raise HTTPException(status_code=409, detail=f"Cannot capture payment in status {payment.status.value}")

    # Downstream gate token verification with exact context binding
    if ctx.is_agent:
        await CommerceService._verify_gate_token(
            db, workspace_id, ctx, "pay_order",
            amount=payment.amount,
            currency=payment.currency,
            target_identity=payment.order_id,
            consume_nonce=False
        )

    # Enforce exact amount, currency, and merchant consistency with linked order
    if payment.order_id:
        order = await db.get(Order, payment.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Linked order not found for payment capture")
        if order.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Linked order workspace mismatch")
        if order.status == OrderStatus.PAID and order.payment_id != payment.id:
            raise HTTPException(status_code=409, detail="Linked order has already been paid by another transaction")
        if abs(float(payment.amount) - float(order.total)) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Payment capture denied: Payment amount ({payment.amount}) does not match linked order total ({order.total})."
            )
        if payment.currency.strip().upper() != order.currency.strip().upper():
            raise HTTPException(
                status_code=400,
                detail=f"Payment capture denied: Payment currency ({payment.currency}) does not match linked order currency ({order.currency})."
            )
        if payment.merchant_reference and payment.merchant_reference != order.merchant_id:
            from app.models.commerce import Merchant
            stmt_m = select(Merchant).where(Merchant.id == order.merchant_id, Merchant.workspace_id == workspace_id)
            res_m = await db.execute(stmt_m)
            m = res_m.scalar_one_or_none()
            if payment.merchant_reference not in (order.merchant_id, getattr(m, 'merchant_reference', None)):
                raise HTTPException(status_code=400, detail="Merchant reference mismatch between payment and linked order.")

        # Revalidate gate decision immediately prior to capture if agent-governed
        if (order.agent_id or payment.agent_id) and not ctx.is_agent:
            gate_meta = (payment.metadata_ or {}).get("finshield", {})
            gdec_id = gate_meta.get("gate_decision_id")
            if not gdec_id:
                raise HTTPException(status_code=403, detail="Payment capture denied: Agent-governed order is missing gate decision context.")
            from app.models.gate import GateDecision, DecisionResult
            from datetime import timezone
            gate_dec = await db.get(GateDecision, gdec_id)
            if not gate_dec or gate_dec.workspace_id != workspace_id or gate_dec.decision != DecisionResult.ALLOW:
                raise HTTPException(status_code=403, detail="Payment capture denied: Gate decision is not ALLOW or workspace mismatch.")
            if gate_dec.valid_until:
                v_dt = gate_dec.valid_until if gate_dec.valid_until.tzinfo else gate_dec.valid_until.replace(tzinfo=timezone.utc)
                if v_dt < datetime.now(timezone.utc):
                    raise HTTPException(status_code=403, detail="Payment capture denied: Gate decision has expired.")

    actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
    payment_agent_id = payment.agent_id or (ctx.agent_id if ctx.is_agent else None)
    payment_actor_type = ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)

    # Enforce exact consistency against any linked approval
    gate_meta = (payment.metadata_ or {}).get("finshield", {})
    gdec_id = gate_meta.get("gate_decision_id")
    if gdec_id:
        from app.models.gate import ApprovalRequest
        stmt_appr_check = select(ApprovalRequest).where(
            ApprovalRequest.gate_decision_id == gdec_id,
            ApprovalRequest.workspace_id == workspace_id
        )
        res_appr_check = await db.execute(stmt_appr_check)
        linked_appr = res_appr_check.scalars().first()
        if linked_appr and linked_appr.amount is not None:
            if abs(float(linked_appr.amount) - float(payment.amount)) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=f"Payment capture denied: Payment amount ({payment.amount}) does not match approved amount ({linked_appr.amount})."
                )
            if linked_appr.currency and linked_appr.currency.strip().upper() != payment.currency.strip().upper():
                raise HTTPException(
                    status_code=400,
                    detail=f"Payment capture denied: Payment currency ({payment.currency}) does not match approved currency ({linked_appr.currency})."
                )
    
    processor = get_payment_processor(payment.payment_method_type)
    success, failure_code, failure_reason = await processor.capture(payment)
    
    if success:
        payment.status = PaymentStatus.CAPTURED
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "CAPTURED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"amount": payment.amount, "currency": payment.currency, "order_id": payment.order_id}
        )
        if payment.order_id:
            await CommerceService.mark_order_paid(db, payment.order_id, payment.id)
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = failure_code
        payment.failure_reason = failure_reason
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "FAILED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"code": failure_code, "reason": failure_reason, "amount": payment.amount, "currency": payment.currency},
            severity=EventSeverity.WARNING
        )
        if payment.order_id:
            await CommerceService.mark_order_payment_failed(db, payment.order_id, payment.id)
        
    await db.commit()
    await db.refresh(payment)
    return payment

async def cancel_payment(db: AsyncSession, workspace_id: str, payment_id: str, ctx: ExecutionContext) -> Payment:
    await CommerceService._verify_gate_token(db, workspace_id, ctx, "cancel_payment", consume_nonce=True)
        
    actor_id = ctx.agent_id if ctx.is_agent else ctx.user_id
    payment = await get_payment(db, workspace_id, payment_id)
    payment_agent_id = payment.agent_id or (ctx.agent_id if ctx.is_agent else None)
    payment_actor_type = ActorType.AGENT if ctx.is_agent else (ActorType.USER if ctx.user_id else ActorType.SYSTEM)
    
    if payment.status not in [PaymentStatus.CREATED, PaymentStatus.REQUIRES_AUTHORIZATION, PaymentStatus.AUTHORIZED]:
        raise HTTPException(status_code=409, detail=f"Cannot cancel payment in status {payment.status.value}")
        
    processor = get_payment_processor(payment.payment_method_type)
    success, failure_code, failure_reason = await processor.cancel(payment)
    
    if success:
        payment.status = PaymentStatus.CANCELLED
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "CANCELLED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"amount": payment.amount, "currency": payment.currency}
        )
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_code = failure_code
        payment.failure_reason = failure_reason
        await log_payment_activity(
            db,
            payment.id,
            workspace_id,
            "FAILED",
            actor_id=actor_id,
            agent_id=payment_agent_id,
            actor_type=payment_actor_type,
            details={"code": failure_code, "reason": failure_reason, "amount": payment.amount, "currency": payment.currency},
            severity=EventSeverity.WARNING
        )

    await db.commit()
    await db.refresh(payment)
    return payment
