from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.policy import Policy, PolicyStatus
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyEvaluationRequest, PolicyEvaluationResponse, DecisionType, MatchedPolicyInfo
from app.services.audit_service import AuditService
from app.models.audit import EventCategory, EventSeverity, ActorType, EventTypes

async def get_policies(db: AsyncSession, workspace_id: str) -> List[Policy]:
    stmt = select(Policy).where(
        Policy.workspace_id == workspace_id,
        Policy.status != PolicyStatus.ARCHIVED
    ).order_by(Policy.priority.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_policy(db: AsyncSession, workspace_id: str, policy_id: str) -> Policy:
    stmt = select(Policy).where(
        Policy.id == policy_id,
        Policy.workspace_id == workspace_id,
        Policy.status != PolicyStatus.ARCHIVED
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

async def create_policy(db: AsyncSession, workspace_id: str, user_id: str, policy_data: PolicyCreate) -> Policy:
    policy = Policy(
        workspace_id=workspace_id,
        name=policy_data.name,
        description=policy_data.description,
        status=policy_data.status,
        priority=policy_data.priority,
        policy_type=policy_data.policy_type,
        conditions=policy_data.conditions,
        actions=policy_data.actions,
        created_by=user_id
    )
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type="POLICY_CREATED",
        event_category=EventCategory.POLICY,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="POLICY",
        entity_id=policy.id,
        payload={"name": policy.name, "status": policy.status.value, "policy_type": policy.policy_type.value}
    )
    
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

async def update_policy(db: AsyncSession, workspace_id: str, policy_id: str, user_id: str, policy_data: PolicyUpdate) -> Policy:
    policy = await get_policy(db, workspace_id, policy_id)
    
    update_data = policy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
        
    await db.commit()
    await db.refresh(policy)
    
    action = EventTypes.POLICY_UPDATED
    if "status" in update_data:
        if update_data["status"] == PolicyStatus.ACTIVE:
            action = EventTypes.POLICY_ACTIVATED
        elif update_data["status"] == PolicyStatus.DISABLED:
            action = EventTypes.POLICY_DISABLED
            
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=action,
        event_category=EventCategory.POLICY,
        severity=EventSeverity.INFO,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="POLICY",
        entity_id=policy.id,
        payload={"updated_fields": list(update_data.keys())}
    )
    
    return policy

async def delete_policy(db: AsyncSession, workspace_id: str, policy_id: str, user_id: str) -> None:
    policy = await get_policy(db, workspace_id, policy_id)
    policy.status = PolicyStatus.ARCHIVED
    
    audit_service = AuditService(db)
    await audit_service.record_event(
        workspace_id=workspace_id,
        event_type=EventTypes.POLICY_ARCHIVED,
        event_category=EventCategory.POLICY,
        severity=EventSeverity.WARNING,
        actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
        actor_id=user_id,
        entity_type="POLICY",
        entity_id=policy.id
    )
    
    await db.commit()


def _evaluate_condition(condition_key: str, condition_value: Any, request: PolicyEvaluationRequest) -> bool:
    if condition_key == "transaction_amount":
        if not isinstance(condition_value, dict):
            return request.amount == condition_value
        op = condition_value.get("operator")
        val = condition_value.get("value")
        if op == "GT": return request.amount > val
        if op == "GTE": return request.amount >= val
        if op == "LT": return request.amount < val
        if op == "LTE": return request.amount <= val
        if op == "EQ": return request.amount == val
        return False
        
    if condition_key == "currency":
        return request.currency == condition_value
        
    if condition_key == "merchant_id":
        return request.merchant_id == condition_value
        
    if condition_key == "capabilities_required":
        req_caps = set(condition_value)
        provided_caps = set(request.capabilities)
        # If the request lacks any required capability, it matches the condition (e.g. for blocking)
        # Wait, if a policy says "capabilities_required", it means "Does the request meet these capabilities?"
        # If the policy is designed to block missing capabilities, it might be formulated differently.
        # Let's say if condition_key is "missing_capabilities", it checks if `req_caps - provided_caps` is not empty.
        pass
        
    return False

def _policy_matches(policy: Policy, request: PolicyEvaluationRequest) -> bool:
    if not policy.conditions:
        return True # Empty conditions matches everything
    
    for key, value in policy.conditions.items():
        if not _evaluate_condition(key, value, request):
            return False
    return True

async def evaluate_policies(db: AsyncSession, workspace_id: str, request: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
    stmt = select(Policy).where(
        Policy.workspace_id == workspace_id,
        Policy.status == PolicyStatus.ACTIVE
    )
    result = await db.execute(stmt)
    policies = list(result.scalars().all())
    
    matched_policies = []
    
    for policy in policies:
        if _policy_matches(policy, request):
            matched_policies.append(policy)
            
    if not matched_policies:
        return PolicyEvaluationResponse(
            decision=DecisionType.ALLOW,
            matched_policies=[],
            reasons=["No active policies matched, allowing by default."]
        )
        
    # Resolve precedence: BLOCK > REVIEW > ALLOW
    # Group by decision
    decision_groups = {
        DecisionType.BLOCK: [],
        DecisionType.REVIEW: [],
        DecisionType.ALLOW: []
    }
    
    for policy in matched_policies:
        decision_str = policy.actions.get("decision", "ALLOW")
        try:
            decision = DecisionType(decision_str)
        except ValueError:
            decision = DecisionType.ALLOW
            
        decision_groups[decision].append(policy)
        
    final_decision = DecisionType.ALLOW
    winning_policies = []
    
    if decision_groups[DecisionType.BLOCK]:
        final_decision = DecisionType.BLOCK
        winning_policies = sorted(decision_groups[DecisionType.BLOCK], key=lambda p: p.priority, reverse=True)
    elif decision_groups[DecisionType.REVIEW]:
        final_decision = DecisionType.REVIEW
        winning_policies = sorted(decision_groups[DecisionType.REVIEW], key=lambda p: p.priority, reverse=True)
    elif decision_groups[DecisionType.ALLOW]:
        final_decision = DecisionType.ALLOW
        winning_policies = sorted(decision_groups[DecisionType.ALLOW], key=lambda p: p.priority, reverse=True)
        
    reasons = []
    # Collect reasons from the winning decision policies
    for p in winning_policies:
        reason = p.actions.get("reason")
        if reason:
            reasons.append(reason)
            
    if not reasons:
        reasons = [f"Matched {len(winning_policies)} policy(ies) resulting in {final_decision.value}"]
        
    matched_info = [MatchedPolicyInfo(policy_id=p.id, name=p.name) for p in winning_policies]
    
    response = PolicyEvaluationResponse(
        decision=final_decision,
        matched_policies=matched_info,
        reasons=reasons
    )
    
    # Log evaluation for matched policies
    for p in winning_policies:
        audit_service = AuditService(db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="POLICY_EVALUATED",
            event_category=EventCategory.POLICY,
            severity=EventSeverity.INFO,
            actor_type=ActorType.SYSTEM,
            entity_type="POLICY",
            entity_id=p.id,
            payload={
                "agent_id": request.agent_id,
                "amount": request.amount,
                "currency": request.currency,
                "decision": final_decision.value,
                "reason": response.reasons[0] if response.reasons else None
            }
        )
        
    return response
