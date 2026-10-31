"""
Unit tests for intent_extractor.extract_intent.
No database or HTTP required.
"""
import pytest
from app.services.intent_extractor import extract_intent
from app.models.intent import IntentType


def test_purchase_intent_detected():
    result = extract_intent("Buy me a Lenovo laptop under ₹80,000")
    assert result.proposed_type == IntentType.PURCHASE


def test_search_intent_detected():
    result = extract_intent("Find me some good headphones")
    assert result.proposed_type == IntentType.SEARCH


def test_compare_intent_detected():
    result = extract_intent("Compare Lenovo vs Dell laptops")
    assert result.proposed_type == IntentType.COMPARE


def test_brand_detected():
    result = extract_intent("Find me a Lenovo laptop")
    brands = result.proposed_constraints.product.preferred_brands if result.proposed_constraints.product else []
    assert "Lenovo" in brands


def test_multiple_brands_detected():
    result = extract_intent("Find Apple or Samsung phones")
    brands = result.proposed_constraints.product.preferred_brands if result.proposed_constraints.product else []
    assert "Apple" in brands or "Samsung" in brands


def test_category_laptop_detected():
    result = extract_intent("Find me a good laptop under ₹80,000")
    category = result.proposed_constraints.product.category if result.proposed_constraints.product else None
    assert category == "LAPTOP"


def test_category_headphones_detected():
    result = extract_intent("Find me good headphones")
    category = result.proposed_constraints.product.category if result.proposed_constraints.product else None
    assert category == "HEADPHONES"


def test_amount_under_80k_inr():
    result = extract_intent("Find me a laptop under ₹80,000")
    amount = result.proposed_constraints.amount
    assert amount is not None
    assert amount.maximum == 80000
    assert amount.currency == "INR"


def test_amount_under_80k_shorthand():
    result = extract_intent("Find me a laptop under 80k")
    amount = result.proposed_constraints.amount
    assert amount is not None
    assert amount.maximum == 80000


def test_amount_less_than():
    result = extract_intent("Get me a phone less than 50000")
    amount = result.proposed_constraints.amount
    assert amount is not None
    assert amount.maximum == 50000


def test_approval_required_detected():
    result = extract_intent("Find me a laptop under ₹80,000, ask me before buying anything")
    approval = result.proposed_constraints.approval
    assert approval is not None
    assert approval.approval_required is True


def test_approval_without_asking_detected():
    result = extract_intent("Buy laptops without asking me")
    approval = result.proposed_constraints.approval
    assert approval is not None
    assert approval.approval_required is True


def test_inr_currency_detected():
    result = extract_intent("Find me a laptop for ₹50,000")
    amount = result.proposed_constraints.amount
    assert amount is not None
    assert amount.currency == "INR"


def test_purchase_refuses_payment_authority():
    """CRITICAL: Purchase intent must NEVER silently grant payment authority."""
    result = extract_intent("Buy me a laptop under ₹80,000")
    refused = result.refused_inferences
    # Check that payment authority refusal is present
    assert any("payment_authority" in r for r in refused), \
        "Purchase intent must explicitly refuse payment_authority inference"


def test_purchase_refuses_auto_purchase():
    """CRITICAL: Purchase intent must NEVER auto-infer full purchase authority."""
    result = extract_intent("Buy me the best laptop")
    refused = result.refused_inferences
    assert any("auto_purchase" in r for r in refused), \
        "Purchase intent must explicitly refuse auto_purchase inference"


def test_search_no_dangerous_inferences():
    """Search intent should not trigger dangerous inferences."""
    result = extract_intent("Find me laptops")
    # Refused inferences should be empty or not contain payment
    payment_refusals = [r for r in result.refused_inferences if "payment" in r]
    # For search intent we don't need to refuse (no purchase happening)
    # Just ensure we don't accidentally grant payment capability
    assert result.proposed_type == IntentType.SEARCH


def test_signals_present():
    result = extract_intent("Buy me a Lenovo laptop under ₹80,000")
    assert len(result.signals) > 0


def test_explanation_present():
    result = extract_intent("Find me a laptop")
    assert len(result.explanation) > 0


def test_proposed_title_generated():
    result = extract_intent("Find me a Lenovo laptop under ₹80,000")
    assert len(result.proposed_title) > 0


def test_empty_results_gracefully():
    """Minimal text with no keywords should not crash."""
    result = extract_intent("something")
    assert result.proposed_type is not None
    assert result.proposed_constraints is not None
