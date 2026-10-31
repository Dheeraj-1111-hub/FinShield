from typing import Optional
from app.models.intent import Intent
from app.schemas.risk import RiskSignal, TransactionContext
from app.models.risk import RiskLevel
from app.services.alignment_engine import evaluate_alignment, ALIGNMENT_ALIGNED, ALIGNMENT_PARTIAL, ALIGNMENT_MISALIGNED


def evaluate_intent_risk(intent: Optional[Intent], transaction: Optional[TransactionContext], action_category: Optional[str] = None, merchant_id: Optional[str] = None, weight: float = 0.25) -> RiskSignal:
    if not intent:
        return RiskSignal(
            signal_type="INTENT_ALIGNMENT",
            score=50.0,
            severity=RiskLevel.MEDIUM,
            weight=weight,
            contribution=50.0 * weight,
            reason_code="NO_INTENT_CONTEXT",
            explanation="No intent was provided for this action."
        )

    # Evaluate alignment using Phase 8 alignment engine
    alignment_result = evaluate_alignment(
        constraints=intent.structured_constraints,
        action="PURCHASE" if transaction else "UNKNOWN",
        amount=transaction.amount if transaction else None,
        currency=transaction.currency if transaction else None,
        product_category=action_category,
        merchant_id=merchant_id
    )

    if alignment_result.alignment == ALIGNMENT_MISALIGNED:
        score = 90.0
        severity = RiskLevel.CRITICAL
        reason = "INTENT_MISMATCH"
    elif alignment_result.alignment == ALIGNMENT_PARTIAL:
        score = 40.0
        severity = RiskLevel.MEDIUM
        reason = "INTENT_PARTIAL_MATCH"
    elif alignment_result.alignment == ALIGNMENT_ALIGNED:
        score = 0.0
        severity = RiskLevel.LOW
        reason = "INTENT_ALIGNED"
    else:
        score = 50.0
        severity = RiskLevel.MEDIUM
        reason = "INTENT_UNKNOWN"

    return RiskSignal(
        signal_type="INTENT_ALIGNMENT",
        score=score,
        severity=severity,
        weight=weight,
        contribution=score * weight,
        reason_code=reason,
        explanation=f"Intent evaluated as {alignment_result.alignment}: " + ", ".join([s.reason for s in alignment_result.signals])
    )
