"""
Deterministic rule-based intent extractor.

This module uses keyword/pattern matching to produce a structured proposal
from natural language text. It is intentionally conservative:
- It NEVER infers payment authority from purchase intent
- Ambiguous inputs return REQUIRES_CONFIRMATION flags
- The result is always a PROPOSAL — it never creates active intent directly
"""
import re
from typing import List, Optional, Tuple
from app.models.intent import IntentType
from app.schemas.intent import (
    ExtractionProposal, ExtractionSignal,
    IntentConstraints, AmountConstraint, ProductConstraint,
    MerchantConstraint, ApprovalConstraint
)


# ─── Category keyword maps ────────────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "LAPTOP": ["laptop", "laptops", "notebook", "macbook", "chromebook", "ultrabook"],
    "HEADPHONES": ["headphone", "headphones", "earphone", "earphones", "earbuds", "airpods", "headset"],
    "PHONE": ["phone", "smartphone", "mobile", "iphone", "android", "handset"],
    "TABLET": ["tablet", "ipad", "surface"],
    "MONITOR": ["monitor", "display", "screen"],
    "KEYBOARD": ["keyboard"],
    "MOUSE": ["mouse"],
    "CAMERA": ["camera", "webcam", "dslr"],
    "TV": ["tv", "television", "smart tv"],
    "CLOTHING": ["shirt", "pants", "shoes", "dress", "jacket", "clothing", "clothes", "apparel"],
    "FURNITURE": ["chair", "desk", "table", "sofa", "furniture"],
    "BOOKS": ["book", "books", "novel", "textbook"],
}

BRAND_KEYWORDS: list[str] = [
    "lenovo", "apple", "samsung", "dell", "hp", "asus", "acer", "microsoft",
    "sony", "lg", "huawei", "oneplus", "xiaomi", "realme", "oppo", "vivo",
    "google", "amazon", "bose", "jbl", "sennheiser", "nike", "adidas", "puma",
]

# Amount pattern: matches "under 80k", "below ₹80,000", "less than 80000", "max 80k", "for ₹50,000"
AMOUNT_PATTERNS = [
    r"(?:under|below|less\s+than|max(?:imum)?|upto?|within)\s*[₹rs\s]*([0-9][0-9,]*(?:k|lakh)?)",
    r"[₹rs]\s*([0-9][0-9,]*(?:k|lakh)?)\s*(?:or\s+less|max|maximum|budget)",
    r"budget\s+(?:of|is|:)?\s*[₹rs\s]*([0-9][0-9,]*(?:k|lakh)?)",
    r"for\s+[₹rs]\s*([0-9][0-9,]*(?:k|lakh)?)",
    r"[₹]([0-9][0-9,]*(?:k|lakh)?)",  # bare ₹ prefix always implies a budget
]

MIN_AMOUNT_PATTERNS = [
    r"(?:above|over|more\s+than|atleast|at\s+least)\s*[₹rs\s]*([0-9][0-9,]*(?:k|lakh)?)",
]

APPROVAL_THRESHOLD_PATTERNS = [
    r"(?:approval|review)\s*(?:is\s*)?(?:required|needed)?\s*(?:for\s+(?:purchases|actions|orders|transactions)\s+)?above\s*[₹rs\s]*([0-9][0-9,]*(?:k|lakh)?)",
    r"(?:purchases|actions|orders|transactions|amounts?)?\s*(?:above|over|exceeding)\s*[₹rs\s]*([0-9][0-9,]*(?:k|lakh)?)\s*(?:require|requires|needs?|must\s+have)\s*(?:my\s+)?(?:approval|confirmation|review)",
]

# Approval trigger phrases
APPROVAL_PHRASES = [
    "without asking", "without my approval", "without confirming",
    "ask me", "ask me before", "don't buy", "do not buy",
    "require my approval", "need my approval", "confirm with me",
    "check with me", "require approval", "needs approval", "requires approval",
]

INTENT_TYPE_KEYWORDS: dict[IntentType, list[str]] = {
    IntentType.PURCHASE: ["buy", "purchase", "order", "get me", "find and buy", "acquire", "cart", "checkout", "add to cart"],
    IntentType.SEARCH: ["find", "search", "look for", "show me", "list", "browse"],
    IntentType.COMPARE: ["compare", "comparison", "difference", "vs", "versus", "which is better"],
    IntentType.BOOKING: ["book", "booking", "reserve", "reservation", "schedule"],
    IntentType.TRANSFER: ["transfer", "send money", "pay someone", "wire"],
    IntentType.PAYMENT: ["pay", "payment", "settle", "clear bill"],
}

# Actions that should NEVER be inferred automatically
DANGEROUS_INFERENCES = [
    "payment_authority",    # Purchase intent ≠ payment authority
    "execute_payment",      # Must be explicit
    "auto_purchase",        # Must be explicit
]


def _parse_amount(raw: str) -> int:
    """Convert textual amount string like '80k', '1,00,000', '1 lakh' to integer."""
    raw = raw.lower().replace(",", "").strip()
    if "lakh" in raw:
        raw = raw.replace("lakh", "").strip()
        return int(float(raw) * 100000)
    if "k" in raw:
        raw = raw.replace("k", "").strip()
        return int(float(raw) * 1000)
    return int(float(raw))


def _detect_currency(text: str) -> str:
    if "₹" in text or "inr" in text.lower() or "rupee" in text.lower():
        return "INR"
    if "$" in text or "usd" in text.lower() or "dollar" in text.lower():
        return "USD"
    if "€" in text or "eur" in text.lower():
        return "EUR"
    return "INR"  # Default


SEARCH_ONLY_PATTERNS = [
    r"\bonly\s+search\b",
    r"\bjust\s+search\b",
    r"\bstrictly\s+search\b",
    r"\bsearch\s+only\b",
    r"\bread\s+only\b",
    r"\bview\s+only\b",
    r"\bbrowse\s+only\b",
    r"\bonly\s+(?:show|find|list)\b",
    r"\bshow\s+me\s+matching\b",
]

NEGATIVE_PURCHASE_PATTERNS = [
    r"\b(?:do\s+not|don't|dont|never)\s+(?:buy|purchase|order|pay|checkout)\b",
    r"\b(?:do\s+not|don't|dont|never)\s+(?:create|add(?:\s+to)?|place|make|execute|proceed\s+with)\s+(?:an?\s+|any\s+)?(?:carts?|orders?|payments?|purchases?)\b",
    r"\bno\s+(?:purchases?|orders?|payments?|carts?)\b",
    r"\bwithout\s+(?:buying|purchasing|ordering|paying|checking\s*out)\b",
    r"\bwithout\s+(?:creating|placing|making|executing)\s+(?:an?\s+|any\s+)?(?:carts?|orders?|payments?|purchases?)\b",
]


def _is_search_only_or_prohibits_purchase(text: str) -> bool:
    text_lower = text.lower()
    for pat in SEARCH_ONLY_PATTERNS:
        if re.search(pat, text_lower):
            return True
    for pat in NEGATIVE_PURCHASE_PATTERNS:
        if re.search(pat, text_lower):
            return True
    return False


def _detect_intent_type(text: str) -> Tuple[IntentType, str]:
    text_lower = text.lower()
    
    # 1. Negative purchase constraints or search-only directives take absolute precedence
    if _is_search_only_or_prohibits_purchase(text):
        return IntentType.SEARCH, "search_only_directive"

    # 2. Strip negated clauses to avoid matching negated keywords (e.g. "do not create an order" -> "order")
    cleaned_lower = re.sub(
        r"(?:do\s+not|don't|dont|never|no)\s+[^.!?,\n]+",
        " ",
        text_lower
    )

    for intent_type, keywords in INTENT_TYPE_KEYWORDS.items():
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, cleaned_lower):
                return intent_type, kw
    return IntentType.SEARCH, "default"


def _detect_category(text: str) -> Optional[str]:
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def _detect_brands(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for brand in BRAND_KEYWORDS:
        if brand in text_lower:
            found.append(brand.capitalize())
    return found


def _detect_max_amount(text: str) -> Optional[int]:
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return _parse_amount(match.group(1))
            except (ValueError, IndexError):
                pass
    return None


def _detect_min_amount(text: str) -> Optional[int]:
    for pattern in MIN_AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return _parse_amount(match.group(1))
            except (ValueError, IndexError):
                pass
    return None


def _detect_approval_constraint(text: str) -> Tuple[bool, Optional[int], str]:
    """
    Detect approval requirement and threshold from text.
    Returns (approval_required, approval_required_above, text_without_approval_clause).
    """
    threshold = None
    cleaned_text = text
    for pattern in APPROVAL_THRESHOLD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                threshold = _parse_amount(match.group(1))
                # Remove the approval phrase so it doesn't trigger MIN_AMOUNT_PATTERNS
                cleaned_text = text[:match.start()] + " " + text[match.end():]
                break
            except (ValueError, IndexError):
                pass

    text_lower = text.lower()
    has_phrase = any(phrase in text_lower for phrase in APPROVAL_PHRASES)
    approval_required = (threshold is not None) or has_phrase
    return approval_required, threshold, cleaned_text


def extract_intent(text: str) -> ExtractionProposal:
    """
    Deterministically extract structured intent from natural language.
    
    Returns an ExtractionProposal. Never creates active intent.
    Never infers payment/purchase authority without explicit statement.
    """
    signals: List[ExtractionSignal] = []
    refused_inferences: List[str] = []

    # Detect approval requirement and threshold first to clean text
    approval_required, approval_threshold, text_for_amounts = _detect_approval_constraint(text)

    # Detect intent type
    intent_type, matched_kw = _detect_intent_type(text)
    signals.append(ExtractionSignal(field="intent_type", value=intent_type, confidence="HIGH"
                                    if intent_type != IntentType.SEARCH else "MEDIUM"))

    # Detect category
    category = _detect_category(text)
    if category:
        signals.append(ExtractionSignal(field="product.category", value=category, confidence="HIGH"))

    # Detect brands
    brands = _detect_brands(text)
    if brands:
        signals.append(ExtractionSignal(field="product.preferred_brands", value=brands, confidence="HIGH"))

    # Detect amounts using cleaned text (to avoid parsing approval threshold as minimum amount)
    max_amount = _detect_max_amount(text_for_amounts)
    min_amount = _detect_min_amount(text_for_amounts)
    currency = _detect_currency(text)

    if max_amount:
        signals.append(ExtractionSignal(field="amount.maximum", value=max_amount, confidence="HIGH"))
    if min_amount:
        signals.append(ExtractionSignal(field="amount.minimum", value=min_amount, confidence="HIGH"))
    if currency:
        signals.append(ExtractionSignal(field="amount.currency", value=currency, confidence="MEDIUM"))

    # Record approval signals
    if approval_required:
        signals.append(ExtractionSignal(field="approval.approval_required", value=True, confidence="HIGH"))
    if approval_threshold is not None:
        signals.append(ExtractionSignal(field="approval.approval_required_above", value=approval_threshold, confidence="HIGH"))

    is_search_only = _is_search_only_or_prohibits_purchase(text)
    if is_search_only:
        intent_type = IntentType.SEARCH
        refused_inferences.append(
            "cart_and_purchase_prohibited: Read/search-only intent detected. "
            "Cart creation, cart modification, checkout, order creation, and payment are categorically prohibited."
        )
        allowed_actions = ["search_products", "list_products", "get_product"]
        prohibited_actions = [
            "create_cart", "add_to_cart", "checkout", "create_order",
            "pay_order", "execute_payment"
        ]
        signals.append(ExtractionSignal(field="intent_type", value="SEARCH (SEARCH_ONLY_ENFORCED)", confidence="HIGH"))
        signals.append(ExtractionSignal(field="constraints.search_only", value=True, confidence="HIGH"))
    else:
        allowed_actions = None
        prohibited_actions = []

    # --- Safety: NEVER infer payment authority from purchase intent ---
    if intent_type == IntentType.PURCHASE:
        refused_inferences.append(
            "payment_authority: Purchase intent does not automatically grant EXECUTE_PAYMENT capability. "
            "Payment authority must be explicitly granted in DelegatedAuthority."
        )
        refused_inferences.append(
            "auto_purchase: Automatic purchase was not inferred. If you want the agent to purchase "
            "autonomously, you must explicitly grant CREATE_ORDER capability in DelegatedAuthority."
        )

    # Build constraints
    amount_constraint = None
    if max_amount or min_amount:
        amount_constraint = AmountConstraint(
            maximum=max_amount,
            minimum=min_amount,
            currency=currency,
        )

    product_constraint = None
    if category or brands:
        product_constraint = ProductConstraint(
            category=category,
            preferred_brands=brands,
        )

    approval_constraint = None
    if approval_required or approval_threshold is not None:
        approval_constraint = ApprovalConstraint(
            approval_required=approval_required,
            approval_required_above=approval_threshold,
        )

    constraints = IntentConstraints(
        amount=amount_constraint,
        product=product_constraint,
        approval=approval_constraint,
        allowed_actions=allowed_actions,
        prohibited_actions=prohibited_actions,
        search_only=is_search_only if is_search_only else None,
        read_only=is_search_only if is_search_only else None,
    )

    # Build title
    title_parts = []
    if intent_type == IntentType.PURCHASE:
        title_parts.append("Purchase")
    elif intent_type == IntentType.SEARCH:
        title_parts.append("Search for")
    elif intent_type == IntentType.COMPARE:
        title_parts.append("Compare")
    else:
        title_parts.append(intent_type.value.capitalize())

    if brands:
        title_parts.append(", ".join(brands[:2]))
    if category:
        title_parts.append(category.lower())
    if max_amount:
        title_parts.append(f"under {currency} {max_amount:,}")

    proposed_title = " ".join(title_parts) if title_parts else text[:100]

    explanation_parts = []
    if intent_type != IntentType.SEARCH:
        explanation_parts.append(f"Detected intent: {intent_type.value}")
    if category:
        explanation_parts.append(f"Product category: {category}")
    if brands:
        explanation_parts.append(f"Preferred brands: {', '.join(brands)}")
    if max_amount:
        explanation_parts.append(f"Maximum amount: {currency} {max_amount:,}")
    if approval_required:
        explanation_parts.append("Approval required before purchase")

    explanation = ". ".join(explanation_parts) or "General search intent detected."

    return ExtractionProposal(
        proposed_type=intent_type,
        proposed_title=proposed_title,
        proposed_constraints=constraints,
        signals=signals,
        explanation=explanation,
        refused_inferences=refused_inferences,
    )
