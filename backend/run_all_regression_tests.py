import asyncio
import traceback
from app.db.database import get_db
from tests.api.test_agent_runtime import (
    test_regression_action_name_normalization_and_intent_alignment,
    test_regression_duplicate_cart_prevention,
    test_regression_search_cart_add_item_authoritative_hydration,
    test_regression_150_purchase_with_100_threshold_requires_approval_before_payment,
    test_regression_blocked_actions_produce_no_payment_side_effects
)

async def main():
    print("--- 1. Testing action name normalization ---")
    await test_regression_action_name_normalization_and_intent_alignment()
    print("PASS: action name normalization")

    async for s in get_db():
        print("--- 2. Testing duplicate cart prevention ---")
        await test_regression_duplicate_cart_prevention(None, None, s)
        print("PASS: duplicate cart prevention")

        print("--- 3. Testing search -> cart -> add item authoritative hydration ---")
        await test_regression_search_cart_add_item_authoritative_hydration(None, None, s)
        print("PASS: search -> cart -> add item authoritative hydration")

        print("--- 4. Testing 150 purchase with 100 threshold review & approval before payment ---")
        await test_regression_150_purchase_with_100_threshold_requires_approval_before_payment(None, None, s)
        print("PASS: 150 purchase with 100 threshold review & approval before payment")

        print("--- 5. Testing blocked actions produce no payment side effects ---")
        await test_regression_blocked_actions_produce_no_payment_side_effects(None, None, s)
        print("PASS: blocked actions produce no payment side effects")
        break

if __name__ == "__main__":
    asyncio.run(main())
