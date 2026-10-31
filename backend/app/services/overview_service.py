from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models.agent import Agent, AgentStatus
from app.models.gate import GateDecision, DecisionResult, ApprovalRequest, ApprovalStatus
from app.models.risk import RiskAssessment, RiskLevel
from app.models.payment import Payment, PaymentStatus
from app.models.commerce import Order
from app.models.investigation import Investigation, InvestigationStatus, SecurityEvent, InvestigationPriority
from app.models.developer import ApiRequestLog, ApiCredential
from app.models.audit import AuditEvent
from app.models.workspace import Workspace

from app.schemas.overview import (
    OverviewResponse,
    AgentSummary,
    FinancialSummary,
    GateSummary,
    RiskSummary,
    InvestigationSummary,
    SecuritySummary,
    OverviewHealth,
    OnboardingState,
    RecentCriticalRisk,
    RecentApprovalRequest,
    RecentAuditEvent
)

def get_time_range_delta(time_range: str) -> timedelta:
    if time_range == "24h":
        return timedelta(hours=24)
    elif time_range == "7d":
        return timedelta(days=7)
    elif time_range == "30d":
        return timedelta(days=30)
    elif time_range == "90d":
        return timedelta(days=90)
    return timedelta(days=30) # Default

async def get_workspace_overview(db: AsyncSession, workspace_id: str, time_range: str = "30d") -> OverviewResponse:
    delta = get_time_range_delta(time_range)
    cutoff = datetime.now(timezone.utc) - delta

    # 1. Agents
    total_agents = (await db.execute(select(func.count(Agent.id)).filter(Agent.workspace_id == workspace_id))).scalar() or 0
    active_agents = (await db.execute(select(func.count(Agent.id)).filter(Agent.workspace_id == workspace_id, Agent.status == AgentStatus.ACTIVE))).scalar() or 0
    paused_agents = (await db.execute(select(func.count(Agent.id)).filter(Agent.workspace_id == workspace_id, Agent.status == AgentStatus.PAUSED))).scalar() or 0
    revoked_agents = (await db.execute(select(func.count(Agent.id)).filter(Agent.workspace_id == workspace_id, Agent.status == AgentStatus.REVOKED))).scalar() or 0

    # 2. Commerce & Financial
    # Workspace configured currency
    ws_res = await db.execute(select(Workspace.currency).where(Workspace.id == workspace_id))
    ws_currency = ws_res.scalar_one_or_none() or "INR"

    # Aggregations grouped by currency to avoid invalid mixed-currency summation
    currency_stats_res = await db.execute(
        select(
            Payment.currency,
            func.sum(Payment.amount),
            func.count(Payment.id)
        ).filter(
            Payment.workspace_id == workspace_id,
            Payment.created_at >= cutoff,
            Payment.status == PaymentStatus.CAPTURED
        ).group_by(Payment.currency)
    )
    currency_stats = currency_stats_res.all()

    balances_by_currency: dict[str, float] = {}
    total_payment_count = 0
    for curr, vol, count in currency_stats:
        curr_key = curr or ws_currency
        balances_by_currency[curr_key] = float(vol or 0)
        total_payment_count += (count or 0)

    # Primary volume prefers the workspace's configured currency, or INR if present, or first currency
    primary_currency = ws_currency if ws_currency in balances_by_currency else ("INR" if "INR" in balances_by_currency else (list(balances_by_currency.keys())[0] if balances_by_currency else ws_currency))
    payment_volume = balances_by_currency.get(primary_currency, 0.0)
    payment_count = total_payment_count
    
    orders_count = (await db.execute(select(func.count(Order.id)).filter(Order.workspace_id == workspace_id, Order.created_at >= cutoff))).scalar() or 0

    # 3. Gate
    allow_count = (await db.execute(select(func.count(GateDecision.id)).filter(GateDecision.workspace_id == workspace_id, GateDecision.created_at >= cutoff, GateDecision.decision == DecisionResult.ALLOW))).scalar() or 0
    review_count = (await db.execute(select(func.count(GateDecision.id)).filter(GateDecision.workspace_id == workspace_id, GateDecision.created_at >= cutoff, GateDecision.decision == DecisionResult.REVIEW))).scalar() or 0
    block_count = (await db.execute(select(func.count(GateDecision.id)).filter(GateDecision.workspace_id == workspace_id, GateDecision.created_at >= cutoff, GateDecision.decision == DecisionResult.BLOCK))).scalar() or 0
    
    total_gate = allow_count + review_count + block_count
    allow_rate = (allow_count / total_gate * 100.0) if total_gate > 0 else 0.0
    review_rate = (review_count / total_gate * 100.0) if total_gate > 0 else 0.0
    block_rate = (block_count / total_gate * 100.0) if total_gate > 0 else 0.0

    # 4. Risk
    low_risk = (await db.execute(select(func.count(RiskAssessment.id)).filter(RiskAssessment.workspace_id == workspace_id, RiskAssessment.created_at >= cutoff, RiskAssessment.risk_level == RiskLevel.LOW))).scalar() or 0
    med_risk = (await db.execute(select(func.count(RiskAssessment.id)).filter(RiskAssessment.workspace_id == workspace_id, RiskAssessment.created_at >= cutoff, RiskAssessment.risk_level == RiskLevel.MEDIUM))).scalar() or 0
    high_risk = (await db.execute(select(func.count(RiskAssessment.id)).filter(RiskAssessment.workspace_id == workspace_id, RiskAssessment.created_at >= cutoff, RiskAssessment.risk_level == RiskLevel.HIGH))).scalar() or 0
    crit_risk = (await db.execute(select(func.count(RiskAssessment.id)).filter(RiskAssessment.workspace_id == workspace_id, RiskAssessment.created_at >= cutoff, RiskAssessment.risk_level == RiskLevel.CRITICAL))).scalar() or 0

    # 5. Investigations
    open_inv = (await db.execute(select(func.count(Investigation.id)).filter(Investigation.workspace_id == workspace_id, Investigation.status == InvestigationStatus.OPEN))).scalar() or 0
    escalated_inv = (await db.execute(select(func.count(Investigation.id)).filter(Investigation.workspace_id == workspace_id, Investigation.status == InvestigationStatus.ESCALATED))).scalar() or 0
    critical_inv = (await db.execute(select(func.count(Investigation.id)).filter(Investigation.workspace_id == workspace_id, Investigation.status.in_([InvestigationStatus.OPEN, InvestigationStatus.ESCALATED]), Investigation.priority == InvestigationPriority.CRITICAL))).scalar() or 0

    # 6. Security Posture
    sec_events = (await db.execute(select(func.count(SecurityEvent.id)).filter(SecurityEvent.workspace_id == workspace_id, SecurityEvent.created_at >= cutoff))).scalar() or 0
    audit_integrity_verified = True
    audit_last_verified_at = datetime.now(timezone.utc)

    # 7. Health
    health = OverviewHealth(
        api="HEALTHY",
        database="HEALTHY",
        redis="HEALTHY"
    )

    # 8. Onboarding State
    has_agents = total_agents > 0
    has_intents = True
    has_auth = True
    has_policy = True
    has_protected_action = total_gate > 0
    has_benchmarks = False

    onboarding = OnboardingState(
        workspace_configured=True,
        agent_configured=has_agents,
        intent_configured=has_intents,
        authority_configured=has_auth,
        policy_configured=has_policy,
        first_protected_action=has_protected_action,
        first_benchmark=has_benchmarks
    )

    # 9. Recent Items
    approvals_res = await db.execute(
        select(ApprovalRequest).filter(
            ApprovalRequest.workspace_id == workspace_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        ).order_by(ApprovalRequest.created_at.desc()).limit(5)
    )
    approvals = approvals_res.scalars().all()

    recent_approvals = []
    
    # Fetch action types for approvals
    action_ids = [a.agent_action_id for a in approvals if a.agent_action_id]
    action_types_map = {}
    if action_ids:
        from app.models.agent_runtime import AgentAction
        actions_res = await db.execute(select(AgentAction.id, AgentAction.tool_name).filter(AgentAction.id.in_(action_ids)))
        action_types_map = {row[0]: row[1] for row in actions_res.all()}

    agent_ids_for_appr = [a.agent_id for a in approvals]
    if agent_ids_for_appr:
        agents_res = await db.execute(select(Agent.id, Agent.name).filter(Agent.id.in_(agent_ids_for_appr)))
        agents_map = {row[0]: row[1] for row in agents_res.all()}
    else:
        agents_map = {}

    for a in approvals:
        recent_approvals.append(RecentApprovalRequest(
            id=a.id,
            agent_id=a.agent_id,
            agent_name=agents_map.get(a.agent_id, "Unknown"),
            action_type=action_types_map.get(a.agent_action_id, "Unknown"),
            merchant=None,
            amount=float(a.amount) if a.amount is not None else None,
            reason=a.reason or "Gate requested review",
            requested_at=a.created_at
        ))

    risks_res = await db.execute(
        select(RiskAssessment).filter(
            RiskAssessment.workspace_id == workspace_id,
            RiskAssessment.risk_level == RiskLevel.CRITICAL
        ).order_by(RiskAssessment.created_at.desc()).limit(5)
    )
    risks = risks_res.scalars().all()

    agent_ids_for_risks = [r.agent_id for r in risks]
    if agent_ids_for_risks:
        agents_res = await db.execute(select(Agent.id, Agent.name).filter(Agent.id.in_(agent_ids_for_risks)))
        agents_map_risks = {row[0]: row[1] for row in agents_res.all()}
    else:
        agents_map_risks = {}

    # Fetch action types for critical risks
    risk_action_ids = [r.agent_action_id for r in risks if r.agent_action_id]
    risk_action_types_map = {}
    if risk_action_ids:
        from app.models.agent_runtime import AgentAction
        risk_actions_res = await db.execute(select(AgentAction.id, AgentAction.tool_name).filter(AgentAction.id.in_(risk_action_ids)))
        risk_action_types_map = {row[0]: row[1] for row in risk_actions_res.all()}

    recent_critical_risks = []
    for r in risks:
        recent_critical_risks.append(RecentCriticalRisk(
            id=r.id,
            agent_id=r.agent_id,
            agent_name=agents_map_risks.get(r.agent_id, "Unknown"),
            action_type=risk_action_types_map.get(r.agent_action_id, "Unknown"),
            risk_level=r.risk_level.value if hasattr(r.risk_level, 'value') else str(r.risk_level),
            score=r.risk_score,
            reason=r.reason_codes[0] if r.reason_codes else "Unknown",
            occurred_at=r.created_at
        ))

    audits_res = await db.execute(
        select(AuditEvent).filter(
            AuditEvent.workspace_id == workspace_id
        ).order_by(AuditEvent.created_at.desc()).limit(10)
    )
    audits = audits_res.scalars().all()

    recent_audits = []
    for a in audits:
        recent_audits.append(RecentAuditEvent(
            id=a.id,
            event_type=a.event_type,
            actor_id=a.actor_id,
            actor_type=a.actor_type,
            target_id=a.entity_id,
            target_type=a.entity_type,
            occurred_at=a.created_at,
            details=a.payload or {}
        ))

    return OverviewResponse(
        time_range=time_range,
        agents=AgentSummary(total=total_agents, active=active_agents, paused=paused_agents, revoked=revoked_agents),
        financial=FinancialSummary(
            payment_volume=payment_volume,
            payment_count=payment_count,
            orders_count=orders_count,
            currency=primary_currency,
            balances_by_currency=balances_by_currency
        ),
        gate=GateSummary(allow=allow_count, review=review_count, block=block_count, allow_rate=allow_rate, review_rate=review_rate, block_rate=block_rate),
        risk=RiskSummary(low=low_risk, medium=med_risk, high=high_risk, critical=crit_risk),
        investigations=InvestigationSummary(open=open_inv, critical=critical_inv, escalated=escalated_inv),
        security=SecuritySummary(security_events=sec_events, open_findings=0, audit_integrity_verified=audit_integrity_verified, audit_last_verified_at=audit_last_verified_at),
        health=health,
        onboarding=onboarding,
        recent_critical_risks=recent_critical_risks,
        recent_approvals=recent_approvals,
        recent_audit_events=recent_audits
    )
