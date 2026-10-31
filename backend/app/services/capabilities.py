"""
Canonical Capability Mapping for FINSHIELD.

Provides consistent capability mapping across:
- Authority schemas
- Tool registry
- Runtime authorization
- Authority simulator
- UI forms and displays
"""
from typing import Set, List, Dict

# Canonical Authority Capabilities
CANONICAL_CAPABILITIES: List[str] = [
    "SEARCH_PRODUCTS",
    "COMPARE_PRODUCTS",
    "CREATE_CART",
    "MANAGE_CART",
    "ADD_CART_ITEM",
    "UPDATE_CART",
    "CREATE_ORDER",
    "CANCEL_ORDER",
    "PAY_ORDER",
    "REQUEST_PAYMENT",
    "EXECUTE_PAYMENT",
    "REQUEST_REFUND",
]

# Canonical tool to canonical action mapping shared by:
# - Intent extraction
# - Intent alignment
# - Authority evaluation
# - Runtime enforcement
CANONICAL_ACTION_MAP: Dict[str, str] = {
    "search_products": "SEARCH_PRODUCTS",
    "create_cart": "CREATE_CART",
    "add_to_cart": "ADD_CART_ITEM",
    "checkout": "CREATE_ORDER",
    "pay_order": "PAY_ORDER",
}

# Reverse mapping from canonical action / capability aliases to registered runtime tool names
CANONICAL_TO_TOOL_MAP: Dict[str, str] = {
    "SEARCH_PRODUCTS": "search_products",
    "CREATE_CART": "create_cart",
    "ADD_CART_ITEM": "add_to_cart",
    "MANAGE_CART": "add_to_cart",
    "ADD_TO_CART": "add_to_cart",
    "CREATE_ORDER": "checkout",
    "CHECKOUT": "checkout",
    "PAY_ORDER": "pay_order",
    "EXECUTE_PAYMENT": "pay_order",
}

def normalize_action_name(action: str) -> str:
    """
    Returns the canonical uppercase action name for any registered tool or capability name.
    Preserves fail-closed behavior: known mappings are normalized; unknown actions are upper-cased.
    """
    if not action:
        return ""
    act_lower = action.lower()
    if act_lower in CANONICAL_ACTION_MAP:
        return CANONICAL_ACTION_MAP[act_lower]
    act_upper = action.upper()
    if act_upper in CANONICAL_TO_TOOL_MAP:
        tool_name = CANONICAL_TO_TOOL_MAP[act_upper]
        return CANONICAL_ACTION_MAP.get(tool_name, act_upper)
    return act_upper

def get_equivalent_action_names(action: str) -> Set[str]:
    """
    Returns the set of all equivalent representations (tool names and capability names)
    for a given action.
    """
    if not action:
        return set()
    norm = normalize_action_name(action)
    lower = action.lower()
    upper = action.upper()
    equivs = {action, norm, lower, upper}
    if lower in CANONICAL_ACTION_MAP:
        equivs.add(CANONICAL_ACTION_MAP[lower])
    if upper in CANONICAL_TO_TOOL_MAP:
        equivs.add(CANONICAL_TO_TOOL_MAP[upper])
    # Add known capability equivalences
    if norm in {"ADD_CART_ITEM", "MANAGE_CART"}:
        equivs.update({"add_to_cart", "ADD_TO_CART", "ADD_CART_ITEM", "MANAGE_CART"})
    elif norm in {"PAY_ORDER", "EXECUTE_PAYMENT"}:
        equivs.update({"pay_order", "PAY_ORDER", "EXECUTE_PAYMENT"})
    elif norm in {"CREATE_ORDER", "CHECKOUT"}:
        equivs.update({"checkout", "CHECKOUT", "CREATE_ORDER"})
    elif norm in {"CREATE_CART"}:
        equivs.update({"create_cart", "CREATE_CART"})
    elif norm in {"SEARCH_PRODUCTS"}:
        equivs.update({"search_products", "SEARCH_PRODUCTS"})
    return equivs

# Canonical tool to capability requirement sets.
# An agent/authority satisfies a tool requirement if it has AT LEAST ONE
# of the equivalent delegated capabilities in the acceptable set.
# Note: Adding items to a cart strictly requires explicit cart management delegation
# (either MANAGE_CART or ADD_CART_ITEM). CREATE_CART alone does NOT grant adding items.
TOOL_CAPABILITY_REQUIREMENTS: Dict[str, List[Set[str]]] = {
    "search_products": [{"SEARCH_PRODUCTS"}],
    "create_cart": [{"CREATE_CART"}],
    "add_to_cart": [{"MANAGE_CART", "ADD_CART_ITEM"}],
    "checkout": [{"CREATE_ORDER"}],
    "pay_order": [{"PAY_ORDER", "EXECUTE_PAYMENT"}],
}

def check_missing_capabilities(required_capability_sets: List[Set[str]], granted_capabilities: Set[str]) -> List[str]:
    """
    Checks if granted_capabilities satisfies all required capability sets.
    Returns list of missing requirements descriptions if unsatisfied.
    """
    missing = []
    for cap_set in required_capability_sets:
        if not (cap_set & granted_capabilities):
            # None of the acceptable capabilities in this requirement set are granted
            if len(cap_set) == 1:
                missing.append(next(iter(cap_set)))
            else:
                missing.append(" or ".join(sorted(cap_set)))
    return missing
