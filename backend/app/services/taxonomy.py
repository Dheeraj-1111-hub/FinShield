"""
Authoritative Catalog Taxonomy and Category Normalization for FINSHIELD.

Provides deterministic category canonicalization, synonym mapping, and
compatibility evaluation between Intent constraints and Agent actions/products.
"""
from typing import Optional, Set, List, Dict

# Authoritative Catalog Taxonomy
# Maps top-level canonical categories and aliases to compatible terms in the FINSHIELD catalog.
CATALOG_TAXONOMY: Dict[str, Set[str]] = {
    "ELECTRONICS": {
        "ELECTRONICS", "ELECTRONIC",
        "LAPTOP", "LAPTOPS", "NOTEBOOK", "NOTEBOOKS",
        "COMPUTER", "COMPUTERS", "PC",
        "PHONE", "PHONES", "SMARTPHONE", "SMARTPHONES", "MOBILE",
        "TABLET", "TABLETS", "IPAD",
        "MONITOR", "MONITORS", "SCREEN", "DISPLAY",
        "HEADPHONES", "HEADPHONE", "EARPHONES", "EARBUDS", "AUDIO", "HEADSET",
        "HARDWARE", "SERVER", "SERVERS",
        "ACCESSORIES", "ACCESSORY",
    },
    "LAPTOP": {
        "LAPTOP", "LAPTOPS", "NOTEBOOK", "NOTEBOOKS",
        "ELECTRONICS", "ELECTRONIC", "HARDWARE", "COMPUTER", "COMPUTERS"
    },
    "HARDWARE": {
        "HARDWARE", "ELECTRONICS", "ELECTRONIC",
        "LAPTOP", "LAPTOPS", "COMPUTER", "COMPUTERS",
        "SERVER", "SERVERS"
    },
    "ACCESSORIES": {
        "ACCESSORIES", "ACCESSORY",
        "MOUSE", "MICE",
        "KEYBOARD", "KEYBOARDS",
        "HEADPHONES", "HEADPHONE", "EARPHONES", "AUDIO",
        "CABLE", "CABLES", "CHARGER", "CHARGERS"
    },
    "SOFTWARE": {
        "SOFTWARE", "SAAS", "SUBSCRIPTION", "SUBSCRIPTIONS",
        "APP", "APPS", "LICENSE", "LICENSES"
    },
    "CLOTHING": {
        "CLOTHING", "APPAREL", "CLOTHES", "SHIRT", "SHIRTS",
        "PANTS", "SHOES", "JACKET", "DRESS"
    },
    "FURNITURE": {
        "FURNITURE", "CHAIR", "CHAIRS", "DESK", "DESKS", "TABLE", "TABLES", "SOFA"
    },
    "BOOKS": {
        "BOOKS", "BOOK", "NOVEL", "NOVELS", "TEXTBOOK", "TEXTBOOKS"
    }
}

# Cross-domain strictly disallowed sets: disjoint major taxonomy domains
INCOMPATIBLE_DOMAINS: List[Set[str]] = [
    CATALOG_TAXONOMY["ELECTRONICS"],
    CATALOG_TAXONOMY["CLOTHING"],
    CATALOG_TAXONOMY["FURNITURE"],
    CATALOG_TAXONOMY["BOOKS"],
]


def normalize_category_string(cat: Optional[str]) -> str:
    """Normalize a category string to uppercase stripped format."""
    if not cat:
        return ""
    return cat.strip().upper()


def get_taxonomy_synonyms(category: Optional[str]) -> List[str]:
    """
    Get lowercase synonyms for a category name for database query expansion.
    """
    if not category:
        return []
    cleaned = category.strip().lower()
    if not cleaned:
        return []
    
    cat_upper = cleaned.upper()
    synonyms_set: Set[str] = {cleaned}
    
    # Check taxonomy matches
    for key, terms in CATALOG_TAXONOMY.items():
        if cat_upper == key or cat_upper in terms:
            for t in terms:
                synonyms_set.add(t.lower())
                
    return sorted(list(synonyms_set))


def are_categories_compatible(intent_cat: Optional[str], target_cat: Optional[str]) -> bool:
    """
    Deterministically evaluates whether a target/action/product category aligns
    with the intent constraint category according to authoritative catalog taxonomy.
    
    Fail-closed: returns False if either category is missing or if they belong
    to genuinely incompatible domains (e.g., CLOTHING vs ELECTRONICS).
    """
    if not intent_cat or not target_cat:
        return False
        
    ic = normalize_category_string(intent_cat)
    tc = normalize_category_string(target_cat)
    
    if not ic or not tc:
        return False
        
    # 1. Exact string match (case-insensitive)
    if ic == tc:
        return True
        
    # 2. Singular/plural normalization (e.g. LAPTOP <-> LAPTOPS, BOOK <-> BOOKS)
    # Strip trailing S if not ending in SS
    def strip_plural(s: str) -> str:
        if s.endswith("S") and not s.endswith("SS") and len(s) > 2:
            return s[:-1]
        return s
        
    if strip_plural(ic) == strip_plural(tc):
        return True
        
    # 3. Direct taxonomy lookup
    if ic in CATALOG_TAXONOMY and tc in CATALOG_TAXONOMY[ic]:
        return True
    if tc in CATALOG_TAXONOMY and ic in CATALOG_TAXONOMY[tc]:
        return True
        
    # 4. Canonical hierarchy check:
    # If both belong to the same top-level domain
    for domain in INCOMPATIBLE_DOMAINS:
        if (ic in domain or strip_plural(ic) in domain) and (tc in domain or strip_plural(tc) in domain):
            return True
            
    # Fail-closed: genuinely incompatible categories
    return False
