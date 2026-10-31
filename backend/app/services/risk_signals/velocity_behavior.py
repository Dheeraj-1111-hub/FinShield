from typing import Optional
from app.schemas.risk import RiskSignal
from app.models.risk import RiskLevel


def evaluate_velocity_behavior_risk(agent_id: str, action_type: str, weight: float = 0.25) -> RiskSignal:
    # In a real engine, this would query recent actions, failed attempts, and historical baseline.
    # For Phase 9 deterministic mock, we will just return a stable baseline score
    # unless a specific test agent ID triggers a scenario.
    
    if agent_id == "ag_velocity_high":
        score = 85.0
        severity = RiskLevel.HIGH
        reason = "HIGH_VELOCITY_ANOMALY"
        explanation = "Agent has executed unusually high number of transactions in last 10 minutes."
    elif agent_id == "ag_behavior_erratic":
        score = 95.0
        severity = RiskLevel.CRITICAL
        reason = "ERRATIC_BEHAVIOR_PATTERN"
        explanation = "Agent exhibiting non-linear path with high error rates before attempting transaction."
    else:
        score = 10.0
        severity = RiskLevel.LOW
        reason = "NORMAL_BEHAVIOR"
        explanation = "Velocity and behavior patterns are within normal historical bounds."
        
    return RiskSignal(
        signal_type="VELOCITY_BEHAVIOR",
        score=score,
        severity=severity,
        weight=weight,
        contribution=score * weight,
        reason_code=reason,
        explanation=explanation
    )
