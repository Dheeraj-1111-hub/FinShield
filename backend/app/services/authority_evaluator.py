"""
Deterministic Authority Evaluator.

Checks whether a proposed agent action is authorized by a DelegatedAuthority.
Enforces:
  - Authority status (must be ACTIVE)
  - Time bounds (valid_from, valid_until)
  - Capability allowlist / denylist
  - Monetary limits
  - Effective authority = min(agent.max_transaction_amount, authority.monetary_limit, intent.amount.maximum)
"""
from typing import Optional, List
from datetime import datetime, timezone

from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.agent import Agent
from app.models.intent import Intent
from app.schemas.authority import AuthorityEvaluationResult


def evaluate_authority(
    authority: DelegatedAuthority,
    agent: Agent,
    action: str,
    amount: Optional[int] = None,
    currency: Optional[str] = None,
    intent: Optional[Intent] = None,
) -> AuthorityEvaluationResult:
    """
    Evaluate whether an action is authorized under the given DelegatedAuthority.
    
    Returns AuthorityEvaluationResult with authorized bool and explicit reasons.
    The most restrictive monetary constraint wins.
    """
    reasons: List[str] = []
    now = datetime.now(timezone.utc)

    # ── Status check ──────────────────────────────────────────────────────────
    if authority.status != AuthorityStatus.ACTIVE:
        reasons.append(f"Authority is {authority.status.value}, not ACTIVE")
        return AuthorityEvaluationResult(
            authorized=False,
            reasons=reasons,
            effective_monetary_limit=None,
            authority_version=authority.version,
        )

    # ── Time bounds check ─────────────────────────────────────────────────────
    if authority.valid_from:
        vf = authority.valid_from
        if vf.tzinfo is None:
            vf = vf.replace(tzinfo=timezone.utc)
        if now < vf:
            reasons.append(f"Authority is not yet valid (valid from {vf.isoformat()})")

    if authority.valid_until:
        vu = authority.valid_until
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=timezone.utc)
        if now > vu:
            reasons.append(f"Authority has expired (expired at {vu.isoformat()})")

    if reasons:
        return AuthorityEvaluationResult(
            authorized=False,
            reasons=reasons,
            effective_monetary_limit=None,
            authority_version=authority.version,
        )

    # ── Agent binding check ───────────────────────────────────────────────────
    if authority.agent_id != agent.id:
        reasons.append(
            f"Authority is bound to agent '{authority.agent_id}', "
            f"not '{agent.id}'"
        )

    # ── Capability denylist check ─────────────────────────────────────────────
    prohibited = set(authority.prohibited_actions or [])
    if action in prohibited:
        reasons.append(f"Action '{action}' is explicitly prohibited by this authority")

    # ── Canonical Capability Resolution ──────────────────────────────────────
    from app.services.capabilities import TOOL_CAPABILITY_REQUIREMENTS, CANONICAL_TO_TOOL_MAP, check_missing_capabilities
    
    # If action matches a tool name, use its canonical capability requirement set
    if action in TOOL_CAPABILITY_REQUIREMENTS:
        req_sets = TOOL_CAPABILITY_REQUIREMENTS[action]
    elif action in CANONICAL_TO_TOOL_MAP and CANONICAL_TO_TOOL_MAP[action] in TOOL_CAPABILITY_REQUIREMENTS:
        req_sets = TOOL_CAPABILITY_REQUIREMENTS[CANONICAL_TO_TOOL_MAP[action]]
    elif action == "EXECUTE_PAYMENT" or action == "PAY_ORDER":
        req_sets = [{"EXECUTE_PAYMENT", "PAY_ORDER"}]
    elif action == "MANAGE_CART" or action == "ADD_CART_ITEM":
        req_sets = [{"MANAGE_CART", "ADD_CART_ITEM"}]
    else:
        req_sets = [{action}]

    # ── Capability allowlist check ────────────────────────────────────────────
    allowed = set(authority.allowed_capabilities or [])
    missing_from_auth = check_missing_capabilities(req_sets, allowed)
    if missing_from_auth:
        reasons.append(
            f"Action '{action}' is not in the authority's allowed capabilities: {authority.allowed_capabilities}"
        )

    # ── Agent capability check ────────────────────────────────────────────────
    agent_caps = set(agent.capabilities or [])
    missing_from_agent = check_missing_capabilities(req_sets, agent_caps)
    if missing_from_agent:
        reasons.append(
            f"Agent lacks capability '{action}' in its own configuration"
        )

    if reasons:
        return AuthorityEvaluationResult(
            authorized=False,
            reasons=reasons,
            effective_monetary_limit=None,
            authority_version=authority.version,
        )

    # ── Currency check & Effective monetary limit ──────────────────────────────
    tx_currency = (currency or "").upper() if currency else None
    auth_currency = (authority.currency or "").upper() if authority.currency else None
    agent_currency = (agent.currency or "").upper() if agent.currency else None

    # If transaction currency and authority currency are both present and mismatch, reject
    if tx_currency and auth_currency and tx_currency != auth_currency:
        reasons.append(
            f"Transaction currency '{tx_currency}' does not match authority currency '{auth_currency}'"
        )

    limit_candidates: List[int] = []

    # Agent max_transaction_amount applies if agent currency matches or is not specified
    if agent.max_transaction_amount is not None:
        if not tx_currency or not agent_currency or tx_currency == agent_currency:
            limit_candidates.append(agent.max_transaction_amount)
        elif tx_currency and agent_currency and tx_currency != agent_currency:
            reasons.append(
                f"Transaction currency '{tx_currency}' does not match agent currency '{agent_currency}'"
            )

    if authority.monetary_limit is not None:
        if not tx_currency or not auth_currency or tx_currency == auth_currency:
            limit_candidates.append(authority.monetary_limit)

    # Intent amount maximum is also a constraint
    if intent and intent.structured_constraints:
        intent_amount = intent.structured_constraints.get("amount", {})
        if intent_amount:
            intent_curr = (intent_amount.get("currency") or "").upper() if intent_amount.get("currency") else None
            if intent_curr and tx_currency and intent_curr != tx_currency:
                reasons.append(
                    f"Transaction currency '{tx_currency}' does not match intent currency '{intent_curr}'"
                )
            if intent_amount.get("maximum"):
                if not tx_currency or not intent_curr or tx_currency == intent_curr:
                    limit_candidates.append(intent_amount["maximum"])

    effective_limit = min(limit_candidates) if limit_candidates else None

    # ── Monetary amount check ─────────────────────────────────────────────────
    requires_approval = False
    if amount is not None and effective_limit is not None:
        if amount > effective_limit:
            reasons.append(
                f"Transaction amount {amount:,} exceeds effective authority limit {effective_limit:,}"
            )

    if amount is not None and authority.approval_threshold is not None:
        if not tx_currency or not auth_currency or tx_currency == auth_currency:
            if amount > authority.approval_threshold:
                requires_approval = True

    # Agent level approval threshold
    if amount is not None and agent.approval_threshold is not None:
        if not tx_currency or not agent_currency or tx_currency == agent_currency:
            if amount > agent.approval_threshold:
                requires_approval = True

    # Intent approval constraints (e.g. approval_required_above or approval_required)
    if intent and intent.structured_constraints:
        intent_approval = intent.structured_constraints.get("approval")
        if intent_approval:
            thresh = intent_approval.get("approval_required_above")
            if thresh is not None and amount is not None:
                if amount > thresh:
                    requires_approval = True
            elif intent_approval.get("approval_required") and thresh is None:
                requires_approval = True

    if reasons:
        return AuthorityEvaluationResult(
            authorized=False,
            reasons=reasons,
            effective_monetary_limit=effective_limit,
            authority_version=authority.version,
            requires_approval=requires_approval,
        )

    return AuthorityEvaluationResult(
        authorized=True,
        reasons=[],
        effective_monetary_limit=effective_limit,
        authority_version=authority.version,
        requires_approval=requires_approval,
    )
