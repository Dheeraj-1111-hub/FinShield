from typing import Optional
from app.schemas.risk import RiskSignal
from app.models.risk import RiskLevel


def evaluate_merchant_risk(merchant_id: Optional[str], weight: float = 0.15) -> RiskSignal:
    if not merchant_id:
        return RiskSignal(
            signal_type="MERCHANT_TRUST",
            score=60.0,
            severity=RiskLevel.MEDIUM,
            weight=weight,
            contribution=60.0 * weight,
            reason_code="NO_MERCHANT_ID",
            explanation="Merchant identity is unknown, defaulting to moderate-high risk."
        )

    # In a real engine, we would query the Merchant model or an external fraud database.
    # For Phase 9 deterministic mock, we will hardcode a few test merchant IDs to demonstrate variance.
    if merchant_id == "m_trusted":
        score = 0.0
        severity = RiskLevel.LOW
        reason = "TRUSTED_MERCHANT"
    elif merchant_id == "m_new":
        score = 65.0
        severity = RiskLevel.HIGH
        reason = "NEW_MERCHANT_NO_HISTORY"
    elif merchant_id == "m_high_risk":
        score = 95.0
        severity = RiskLevel.CRITICAL
        reason = "KNOWN_FRAUDULENT_MERCHANT"
    else:
        # Default fallback for unknown string ID
        score = 40.0
        severity = RiskLevel.MEDIUM
        reason = "UNKNOWN_MERCHANT_HISTORY"
        
    return RiskSignal(
        signal_type="MERCHANT_TRUST",
        score=score,
        severity=severity,
        weight=weight,
        contribution=score * weight,
        reason_code=reason,
        explanation=f"Merchant risk assessed as {reason} with score {score}."
    )
