"""
Unit tests for alignment_engine.evaluate_alignment.
No database or HTTP required.
"""
import pytest
from app.services.alignment_engine import (
    evaluate_alignment,
    ALIGNMENT_ALIGNED, ALIGNMENT_MISALIGNED, ALIGNMENT_PARTIAL, ALIGNMENT_UNKNOWN,
    SIGNAL_ALIGNED, SIGNAL_MISALIGNED,
)


def test_no_constraints_returns_unknown():
    result = evaluate_alignment(constraints=None, action="search_products")
    assert result.alignment == ALIGNMENT_UNKNOWN


def test_empty_constraints_returns_unknown():
    result = evaluate_alignment(constraints={}, action="search_products")
    assert result.alignment == ALIGNMENT_UNKNOWN


def test_amount_within_max_is_aligned():
    constraints = {"amount": {"maximum": 80000, "currency": "INR"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", amount=70000)
    assert result.alignment == ALIGNMENT_ALIGNED
    amount_signals = [s for s in result.signals if s.type == "AMOUNT"]
    assert len(amount_signals) == 1
    assert amount_signals[0].status == SIGNAL_ALIGNED


def test_amount_exceeds_max_is_misaligned():
    constraints = {"amount": {"maximum": 80000, "currency": "INR"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", amount=90000)
    assert result.alignment == ALIGNMENT_MISALIGNED
    amount_signals = [s for s in result.signals if s.type == "AMOUNT"]
    assert amount_signals[0].status == SIGNAL_MISALIGNED


def test_amount_below_min_is_misaligned():
    constraints = {"amount": {"minimum": 10000, "maximum": 80000, "currency": "INR"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", amount=5000)
    assert result.alignment == ALIGNMENT_MISALIGNED


def test_amount_exactly_at_max_is_aligned():
    constraints = {"amount": {"maximum": 80000, "currency": "INR"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", amount=80000)
    assert result.alignment == ALIGNMENT_ALIGNED


def test_category_match_is_aligned():
    constraints = {"product": {"category": "LAPTOP"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", product_category="LAPTOP")
    assert result.alignment == ALIGNMENT_ALIGNED


def test_category_mismatch_is_misaligned():
    constraints = {"product": {"category": "LAPTOP"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", product_category="HEADPHONES")
    assert result.alignment == ALIGNMENT_MISALIGNED
    cat_signals = [s for s in result.signals if s.type == "CATEGORY"]
    assert cat_signals[0].status == SIGNAL_MISALIGNED


def test_category_case_insensitive():
    constraints = {"product": {"category": "LAPTOP"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", product_category="laptop")
    assert result.alignment == ALIGNMENT_ALIGNED


def test_partial_alignment_one_aligned_one_misaligned():
    constraints = {
        "amount": {"maximum": 80000, "currency": "INR"},
        "product": {"category": "LAPTOP"},
    }
    # Amount OK (70k < 80k), but category mismatch
    result = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        amount=70000,
        product_category="HEADPHONES",
    )
    assert result.alignment == ALIGNMENT_PARTIAL


def test_merchant_blocked_is_misaligned():
    constraints = {"merchant": {"blocked_merchants": ["bad_merchant_1"], "allowed_merchants": []}}
    result = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        merchant_id="bad_merchant_1",
    )
    assert result.alignment == ALIGNMENT_MISALIGNED


def test_merchant_allowed_is_aligned():
    constraints = {"merchant": {"allowed_merchants": ["good_merchant"], "blocked_merchants": []}}
    result = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        merchant_id="good_merchant",
    )
    assert result.alignment == ALIGNMENT_ALIGNED


def test_merchant_not_in_allowed_list_is_misaligned():
    constraints = {"merchant": {"allowed_merchants": ["good_merchant"], "blocked_merchants": []}}
    result = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        merchant_id="unknown_merchant",
    )
    assert result.alignment == ALIGNMENT_MISALIGNED


def test_allowed_actions_match_is_aligned():
    constraints = {"allowed_actions": ["search_products", "create_cart"]}
    result = evaluate_alignment(constraints=constraints, action="search_products")
    assert result.alignment == ALIGNMENT_ALIGNED


def test_allowed_actions_mismatch_is_misaligned():
    constraints = {"allowed_actions": ["search_products"]}
    result = evaluate_alignment(constraints=constraints, action="pay_order")
    assert result.alignment == ALIGNMENT_MISALIGNED


def test_multiple_all_aligned():
    constraints = {
        "amount": {"maximum": 100000, "currency": "INR"},
        "product": {"category": "LAPTOP"},
        "allowed_actions": ["search_products"],
    }
    result = evaluate_alignment(
        constraints=constraints,
        action="search_products",
        amount=70000,
        product_category="LAPTOP",
    )
    assert result.alignment == ALIGNMENT_ALIGNED


def test_amount_constraint_no_amount_on_action():
    """If intent has amount constraint but action provides no amount → UNKNOWN for that signal."""
    constraints = {"amount": {"maximum": 80000, "currency": "INR"}}
    result = evaluate_alignment(constraints=constraints, action="search_products", amount=None)
    amount_signals = [s for s in result.signals if s.type == "AMOUNT"]
    assert amount_signals[0].status == ALIGNMENT_UNKNOWN
