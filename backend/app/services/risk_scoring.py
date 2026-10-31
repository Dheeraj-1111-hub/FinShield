from typing import List, Tuple
from app.schemas.risk import RiskSignal
from app.models.risk import RiskLevel


def calculate_risk_level(score: float) -> RiskLevel:
    if score >= 85.0:
        return RiskLevel.CRITICAL
    elif score >= 60.0:
        return RiskLevel.HIGH
    elif score >= 30.0:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def calculate_final_risk(signals: List[RiskSignal]) -> Tuple[float, RiskLevel, str]:
    """
    Computes the final deterministic risk score based on weighted sum of signals.
    Also returns the overall RiskLevel and a generated decision hint.
    """
    total_score = 0.0
    total_weight = 0.0
    
    for signal in signals:
        total_score += signal.contribution
        total_weight += signal.weight
        
    # Normalize if total weight doesn't exactly equal 1.0 (though it should)
    if total_weight > 0:
        final_score = total_score / total_weight
    else:
        final_score = 100.0  # Safe default if no signals
        
    final_score = round(final_score, 2)
    risk_level = calculate_risk_level(final_score)
    
    # Generate decision hint
    if risk_level == RiskLevel.CRITICAL:
        hint = "BLOCK_AND_ALERT"
    elif risk_level == RiskLevel.HIGH:
        hint = "REQUIRE_HUMAN_REVIEW"
    elif risk_level == RiskLevel.MEDIUM:
        hint = "PROCEED_WITH_WARNING"
    else:
        hint = "AUTO_APPROVE"
        
    return final_score, risk_level, hint
