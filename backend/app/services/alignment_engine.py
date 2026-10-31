"""
Deterministic Intent Alignment Engine.

Compares a proposed agent action against the structured constraints of an Intent
and returns ALIGNED, PARTIAL, MISALIGNED, or UNKNOWN.

This is a Phase 8 building block. Phase 9 will incorporate alignment signals
into the risk score.
"""
from typing import Optional, List
from app.schemas.intent import AlignmentResult, AlignmentSignal, IntentConstraints


ALIGNMENT_ALIGNED = "ALIGNED"
ALIGNMENT_PARTIAL = "PARTIAL"
ALIGNMENT_MISALIGNED = "MISALIGNED"
ALIGNMENT_UNKNOWN = "UNKNOWN"

SIGNAL_ALIGNED = "ALIGNED"
SIGNAL_MISALIGNED = "MISALIGNED"
SIGNAL_UNKNOWN = "UNKNOWN"


def evaluate_alignment(
    constraints: Optional[dict],
    action: str,
    amount: Optional[int] = None,
    currency: Optional[str] = None,
    product_category: Optional[str] = None,
    merchant_id: Optional[str] = None,
) -> AlignmentResult:
    """
    Evaluate how well a proposed action aligns with an intent's constraints.
    
    Returns AlignmentResult with per-signal breakdown.
    """
    if not constraints:
        return AlignmentResult(
            alignment=ALIGNMENT_UNKNOWN,
            signals=[AlignmentSignal(type="GENERAL", status=ALIGNMENT_UNKNOWN,
                                     reason="No structured constraints defined")]
        )

    # Parse the constraints dict into sub-sections
    amount_c = constraints.get("amount")
    if not amount_c:
        if any(k in constraints for k in ("max_budget", "budget", "maximum", "max_amount")):
            amount_c = {
                "maximum": constraints.get("max_budget") or constraints.get("budget") or constraints.get("maximum") or constraints.get("max_amount"),
                "minimum": constraints.get("min_budget") or constraints.get("minimum") or constraints.get("min_amount"),
                "currency": constraints.get("currency", "INR")
            }

    product_c = constraints.get("product")
    if not product_c:
        if "category" in constraints or "product_scope" in constraints:
            cats = constraints.get("product_scope") or constraints.get("category")
            if isinstance(cats, list) and len(cats) > 0:
                cat = cats[0]
            else:
                cat = cats
            product_c = {"category": cat, "product_scope": cats}

    merchant_c = constraints.get("merchant")
    allowed_actions = constraints.get("allowed_actions", [])

    signals: List[AlignmentSignal] = []

    SAFE_READ_ACTIONS = {"search_products", "list_products", "get_product", "SEARCH_PRODUCTS", "LIST_PRODUCTS", "GET_PRODUCT"}

    # ── AMOUNT check ──────────────────────────────────────────────────────────
    if amount_c and amount is not None:
        if isinstance(amount_c, (int, float)):
            max_amount = amount_c
            min_amount = None
            amt_currency = "INR"
        elif isinstance(amount_c, dict):
            max_amount = amount_c.get("maximum")
            min_amount = amount_c.get("minimum")
            amt_currency = amount_c.get("currency", "INR")
        else:
            max_amount = None
            min_amount = None
            amt_currency = "INR"

        if max_amount and amount > max_amount:
            signals.append(AlignmentSignal(
                type="AMOUNT",
                status=SIGNAL_MISALIGNED,
                reason=f"Action amount {currency or amt_currency} {amount:,} exceeds intent maximum {max_amount:,}"
            ))
        elif min_amount and amount < min_amount:
            signals.append(AlignmentSignal(
                type="AMOUNT",
                status=SIGNAL_MISALIGNED,
                reason=f"Action amount {amount:,} is below intent minimum {min_amount:,}"
            ))
        else:
            signals.append(AlignmentSignal(type="AMOUNT", status=SIGNAL_ALIGNED,
                                           reason=f"Amount {amount:,} within intent bounds"))
    elif amount_c and amount is None:
        if action not in ["create_cart", "CREATE_CART"] and action not in SAFE_READ_ACTIONS:
            signals.append(AlignmentSignal(type="AMOUNT", status=ALIGNMENT_UNKNOWN,
                                            reason="Intent has amount constraints but action has no amount"))

    # ── CATEGORY check ────────────────────────────────────────────────────────
    if product_c:
        intent_category = product_c.get("category")
        product_scope = product_c.get("product_scope")
        if (intent_category or product_scope) and product_category:
            from app.services.taxonomy import are_categories_compatible
            is_match = False
            if intent_category and are_categories_compatible(intent_category, product_category):
                is_match = True
            elif isinstance(product_scope, list):
                for sc in product_scope:
                    if are_categories_compatible(sc, product_category):
                        is_match = True
                        break
            elif isinstance(product_scope, str) and are_categories_compatible(product_scope, product_category):
                is_match = True
            
            if is_match:
                signals.append(AlignmentSignal(type="CATEGORY", status=SIGNAL_ALIGNED,
                                                reason=f"Product category '{product_category}' matches intent"))
            else:
                signals.append(AlignmentSignal(
                    type="CATEGORY",
                    status=SIGNAL_MISALIGNED,
                    reason=f"Expected category '{intent_category or product_scope}', got '{product_category}'"
                ))
        elif intent_category and not product_category:
            if action in ["checkout", "pay_order"]:
                signals.append(AlignmentSignal(type="CATEGORY", status=SIGNAL_MISALIGNED,
                                                reason="Intent has category constraint but authoritative category is missing on financial action"))
            elif action not in ["create_cart", "CREATE_CART"] and action not in SAFE_READ_ACTIONS:
                signals.append(AlignmentSignal(type="CATEGORY", status=ALIGNMENT_UNKNOWN,
                                                reason="Intent has category constraint but category is not yet authoritative in this phase"))

        # Blocked brands check
        blocked_brands = product_c.get("blocked_brands", [])
        if blocked_brands:
            # We can't check brand here without more action context, mark unknown
            signals.append(AlignmentSignal(type="BRAND", status=ALIGNMENT_UNKNOWN,
                                            reason="Cannot verify brand constraint without product details"))

    # ── MERCHANT check ────────────────────────────────────────────────────────
    if merchant_c and merchant_id:
        allowed_merchants = merchant_c.get("allowed_merchants", [])
        blocked_merchants = merchant_c.get("blocked_merchants", [])

        if blocked_merchants and merchant_id in blocked_merchants:
            signals.append(AlignmentSignal(
                type="MERCHANT",
                status=SIGNAL_MISALIGNED,
                reason=f"Merchant '{merchant_id}' is in the blocked merchants list"
            ))
        elif allowed_merchants and merchant_id not in allowed_merchants:
            signals.append(AlignmentSignal(
                type="MERCHANT",
                status=SIGNAL_MISALIGNED,
                reason=f"Merchant '{merchant_id}' is not in the allowed merchants list"
            ))
        else:
            signals.append(AlignmentSignal(type="MERCHANT", status=SIGNAL_ALIGNED,
                                            reason="Merchant is permitted by intent"))

    # ── ACTION check ──────────────────────────────────────────────────────────
    from app.services.capabilities import get_equivalent_action_names, normalize_action_name

    SIDE_EFFECTING_COMMERCE_ACTIONS = {
        "create_cart", "add_to_cart", "checkout", "pay_order",
        "CREATE_CART", "ADD_TO_CART", "ADD_CART_ITEM", "MANAGE_CART",
        "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
    }

    action_equivs = get_equivalent_action_names(action)
    action_norm = normalize_action_name(action)

    prohibited_actions = constraints.get("prohibited_actions", [])
    if prohibited_actions:
        prohibited_normalized = {normalize_action_name(a) for a in prohibited_actions}
        prohibited_equivs = set()
        for a in prohibited_actions:
            prohibited_equivs.update(get_equivalent_action_names(a))
        
        if bool(action_equivs & prohibited_equivs) or (action_norm in prohibited_normalized):
            signals.append(AlignmentSignal(
                type="ACTION",
                status=SIGNAL_MISALIGNED,
                reason=f"Action '{action}' is explicitly prohibited by intent"
            ))

    search_only = constraints.get("search_only") or constraints.get("read_only")
    if search_only and action in SIDE_EFFECTING_COMMERCE_ACTIONS:
        if not any(s.type == "ACTION" and s.status == SIGNAL_MISALIGNED for s in signals):
            signals.append(AlignmentSignal(
                type="ACTION",
                status=SIGNAL_MISALIGNED,
                reason=f"Action '{action}' violates read/search-only intent constraint. Side effects are prohibited."
            ))

    if allowed_actions:
        allowed_normalized = {normalize_action_name(a) for a in allowed_actions}
        allowed_equivs = set()
        for a in allowed_actions:
            allowed_equivs.update(get_equivalent_action_names(a))
        
        is_allowed = bool(action_equivs & allowed_equivs) or (action_norm in allowed_normalized)

        if is_allowed:
            signals.append(AlignmentSignal(type="ACTION", status=SIGNAL_ALIGNED,
                                            reason=f"Action '{action}' is explicitly allowed by intent"))
        else:
            if not any(s.type == "ACTION" and s.status == SIGNAL_MISALIGNED for s in signals):
                signals.append(AlignmentSignal(
                    type="ACTION",
                    status=SIGNAL_MISALIGNED,
                    reason=f"Action '{action}' not in intent's allowed actions: {allowed_actions}"
                ))

    # ── Aggregate ─────────────────────────────────────────────────────────────
    if not signals:
        if not search_only and not prohibited_actions:
            signals.append(
                AlignmentSignal(
                    type="ACTION",
                    status=SIGNAL_ALIGNED,
                    reason=f"Action '{action}' is permitted by active intent"
                )
            )
        else:
            return AlignmentResult(alignment=ALIGNMENT_UNKNOWN, signals=[
                AlignmentSignal(type="GENERAL", status=ALIGNMENT_UNKNOWN,
                                reason="No applicable constraints found for this action")
            ])

    statuses = [s.status for s in signals]
    misaligned_count = statuses.count(SIGNAL_MISALIGNED)
    aligned_count = statuses.count(SIGNAL_ALIGNED)

    has_fatal_action_misalignment = any(
        s.type == "ACTION" and s.status == SIGNAL_MISALIGNED for s in signals
    )

    if has_fatal_action_misalignment:
        overall = ALIGNMENT_MISALIGNED
    elif misaligned_count == 0 and aligned_count > 0:
        overall = ALIGNMENT_ALIGNED
    elif misaligned_count > 0 and aligned_count > 0:
        overall = ALIGNMENT_PARTIAL
    elif misaligned_count > 0 and aligned_count == 0:
        overall = ALIGNMENT_MISALIGNED
    else:
        overall = ALIGNMENT_UNKNOWN

    return AlignmentResult(alignment=overall, signals=signals)
