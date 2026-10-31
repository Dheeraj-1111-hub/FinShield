from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from app.schemas.risk import RiskEvaluateRequest, RiskAssessmentResponse, TransactionContext
from app.models.risk import RiskAssessment, RiskAssessmentType, RiskAssessmentStatus, RiskLevel
from app.models.intent import Intent
from app.models.authority import DelegatedAuthority
from app.services.risk_signals.intent import evaluate_intent_risk
from app.services.risk_signals.authority import evaluate_authority_risk
from app.services.risk_signals.transaction import evaluate_transaction_risk
from app.services.risk_signals.merchant import evaluate_merchant_risk
from app.services.risk_signals.velocity_behavior import evaluate_velocity_behavior_risk
from app.services.risk_scoring import calculate_final_risk
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
import uuid
import datetime
from sqlalchemy import select


async def fetch_intent(db: AsyncSession, intent_id: Optional[str]) -> Optional[Intent]:
    if not intent_id:
        return None
    result = await db.execute(select(Intent).where(Intent.id == intent_id))
    return result.scalar_one_or_none()

async def fetch_authority(db: AsyncSession, authority_id: Optional[str]) -> Optional[DelegatedAuthority]:
    if not authority_id:
        return None
    result = await db.execute(select(DelegatedAuthority).where(DelegatedAuthority.id == authority_id))
    return result.scalar_one_or_none()


async def evaluate_risk(
    db: AsyncSession, 
    workspace_id: str, 
    request: RiskEvaluateRequest, 
    persist: bool = True
) -> RiskAssessmentResponse:
    
    intent = await fetch_intent(db, request.intent_id)
    authority = await fetch_authority(db, request.authority_id)
    
    # 1. Gather Context & Build Feature Snapshot
    feature_snapshot = {
        "intent_constraints": intent.structured_constraints if intent else None,
        "authority_limits": authority.monetary_limit if authority else None,
        "transaction": request.transaction.model_dump() if request.transaction else None,
        "merchant_id": request.merchant_id,
        "product_category": request.product_category
    }

    # 2. Evaluate Signals (Deterministic Weighted Approach)
    signals = []
    
    # Intent Alignment (25%)
    intent_signal = evaluate_intent_risk(
        intent=intent, 
        transaction=request.transaction, 
        action_category=request.product_category,
        merchant_id=request.merchant_id,
        weight=0.25
    )
    signals.append(intent_signal)
    
    # Authority Proximity (20%)
    authority_signal = evaluate_authority_risk(
        authority=authority,
        transaction=request.transaction,
        weight=0.20
    )
    signals.append(authority_signal)
    
    # Transaction Size (15%)
    tx_signal = evaluate_transaction_risk(
        transaction=request.transaction,
        weight=0.15
    )
    signals.append(tx_signal)
    
    # Merchant Trust (15%)
    merchant_signal = evaluate_merchant_risk(
        merchant_id=request.merchant_id,
        weight=0.15
    )
    signals.append(merchant_signal)
    
    # Velocity & Behavior (25%)
    velocity_signal = evaluate_velocity_behavior_risk(
        agent_id=request.agent_id,
        action_type="TRANSACTION",
        weight=0.25
    )
    signals.append(velocity_signal)
    
    # 3. Score Aggregation
    final_score, risk_level, decision_hint = calculate_final_risk(signals)
    
    # 4. Construct Assessment Record
    assessment = RiskAssessment(
        workspace_id=workspace_id,
        agent_id=request.agent_id,
        agent_run_id=request.agent_run_id,
        agent_action_id=request.agent_action_id,
        intent_id=request.intent_id,
        intent_version=intent.version if intent else None,
        authority_id=request.authority_id,
        authority_version=authority.version if authority else None,
        assessment_type=RiskAssessmentType.TRANSACTION,
        risk_score=final_score,
        risk_level=risk_level,
        decision_hint=decision_hint,
        signals=[s.model_dump() for s in signals],
        feature_snapshot=feature_snapshot,
        model_version="det-1.0.0",
        scoring_version="v1",
        status=RiskAssessmentStatus.COMPLETED
    )
    
    if persist:
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        
        audit_service = AuditService(db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="RISK_ASSESSMENT_COMPLETED",
            event_category=EventCategory.RISK,
            severity=EventSeverity.WARNING if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else EventSeverity.INFO,
            actor_type=ActorType.SYSTEM,
            entity_type="RISK_ASSESSMENT",
            entity_id=assessment.id,
            payload={"risk_score": final_score, "risk_level": risk_level.value, "agent_id": request.agent_id}
        )
    else:
        # Mocking values if not persisting
        assessment.id = f"ra_mock_{uuid.uuid4().hex[:8]}"
        assessment.created_at = datetime.datetime.now(datetime.timezone.utc)
        assessment.updated_at = assessment.created_at
        
    return RiskAssessmentResponse.model_validate(assessment)
