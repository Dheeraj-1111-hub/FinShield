from typing import Optional
from app.schemas.risk import RiskSignal, TransactionContext
from app.models.risk import RiskLevel


def evaluate_transaction_risk(transaction: Optional[TransactionContext], weight: float = 0.15) -> RiskSignal:
    if not transaction or transaction.amount is None:
        return RiskSignal(
            signal_type="TRANSACTION_SIZE",
            score=50.0,
            severity=RiskLevel.MEDIUM,
            weight=weight,
            contribution=50.0 * weight,
            reason_code="NO_TRANSACTION_AMOUNT",
            explanation="Transaction size is unknown."
        )

    amount = transaction.amount
    
    # Static baseline heuristic. In reality, this would use the user's/workspace's typical average.
    # We treat < 10,000 as LOW, 10,000 - 50,000 as MEDIUM, 50,000 - 100,000 as HIGH, > 100,000 as CRITICAL
    
    if amount < 10000:
        score = (amount / 10000.0) * 20.0  # 0-20
        severity = RiskLevel.LOW
    elif amount < 50000:
        score = 20.0 + ((amount - 10000.0) / 40000.0) * 40.0  # 20-60
        severity = RiskLevel.MEDIUM
    elif amount < 100000:
        score = 60.0 + ((amount - 50000.0) / 50000.0) * 30.0  # 60-90
        severity = RiskLevel.HIGH
    else:
        score = min(100.0, 90.0 + ((amount - 100000.0) / 100000.0) * 10.0)  # 90-100
        severity = RiskLevel.CRITICAL
        
    return RiskSignal(
        signal_type="TRANSACTION_SIZE",
        score=score,
        severity=severity,
        weight=weight,
        contribution=score * weight,
        reason_code="STATIC_AMOUNT_HEURISTIC",
        explanation=f"Transaction size {amount} mapped to static absolute risk brackets."
    )
