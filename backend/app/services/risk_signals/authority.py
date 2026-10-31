from typing import Optional
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.schemas.risk import RiskSignal, TransactionContext
from app.models.risk import RiskLevel


def evaluate_authority_risk(authority: Optional[DelegatedAuthority], transaction: Optional[TransactionContext], weight: float = 0.20) -> RiskSignal:
    if not authority:
        return RiskSignal(
            signal_type="AUTHORITY_PROXIMITY",
            score=50.0,
            severity=RiskLevel.MEDIUM,
            weight=weight,
            contribution=50.0 * weight,
            reason_code="NO_AUTHORITY_CONTEXT",
            explanation="No delegated authority was provided."
        )
        
    if authority.status != AuthorityStatus.ACTIVE:
        return RiskSignal(
            signal_type="AUTHORITY_PROXIMITY",
            score=100.0,
            severity=RiskLevel.CRITICAL,
            weight=weight,
            contribution=100.0 * weight,
            reason_code="AUTHORITY_INACTIVE",
            explanation=f"Authority is in {authority.status.value} state, but must be ACTIVE."
        )

    if not transaction or transaction.amount is None:
        return RiskSignal(
            signal_type="AUTHORITY_PROXIMITY",
            score=50.0,
            severity=RiskLevel.MEDIUM,
            weight=weight,
            contribution=50.0 * weight,
            reason_code="UNKNOWN_TRANSACTION_AMOUNT",
            explanation="Transaction amount is unknown."
        )

    # Authority proximity scoring based on amount vs maximum allowed
    max_amount = authority.monetary_limit or 0
    if max_amount == 0:
        return RiskSignal(
            signal_type="AUTHORITY_PROXIMITY",
            score=0.0,
            severity=RiskLevel.LOW,
            weight=weight,
            contribution=0.0,
            reason_code="NO_AMOUNT_LIMIT",
            explanation="Authority has no maximum amount limit."
        )

    amount = transaction.amount
    if amount > max_amount:
        return RiskSignal(
            signal_type="AUTHORITY_PROXIMITY",
            score=100.0,
            severity=RiskLevel.CRITICAL,
            weight=weight,
            contribution=100.0 * weight,
            reason_code="LIMIT_EXCEEDED",
            explanation=f"Transaction amount {amount} exceeds authority limit {max_amount}."
        )

    utilization = (amount / max_amount) * 100.0
    
    # Heuristics:
    # 0-50%: low risk
    # 51-80%: medium risk
    # 81-99%: high risk
    if utilization <= 50.0:
        score = utilization * 0.5  # 0 to 25 score
        severity = RiskLevel.LOW
    elif utilization <= 80.0:
        score = 25.0 + ((utilization - 50.0) / 30.0) * 35.0  # 25 to 60 score
        severity = RiskLevel.MEDIUM
    else:
        score = 60.0 + ((utilization - 80.0) / 20.0) * 30.0  # 60 to 90 score
        severity = RiskLevel.HIGH
        
    return RiskSignal(
        signal_type="AUTHORITY_PROXIMITY",
        score=score,
        severity=severity,
        weight=weight,
        contribution=score * weight,
        reason_code="PROXIMITY_CALCULATED",
        explanation=f"Transaction uses {utilization:.1f}% of delegated authority limit."
    )
