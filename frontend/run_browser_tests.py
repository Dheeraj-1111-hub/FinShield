import asyncio
from playwright.async_api import async_playwright

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # We assume the frontend is running on 8081 (or 3000)
        try:
            await page.goto("http://localhost:8081/app/console", timeout=10000)
        except Exception:
            try:
                await page.goto("http://localhost:3000/app/console", timeout=10000)
            except Exception as e:
                print(f"Could not connect to frontend: {e}")
                await browser.close()
                return

        print("Successfully loaded Agent Console")
        # Let's verify Test A
        print("\n--- TEST A: Search ---")
        await page.fill('input[placeholder*="Message"]', 'Find me a laptop under ₹40,000.')
        await page.click('button:has(.lucide-arrow-right)')
        
        try:
            # Wait for execution to finish (status changes to COMPLETED)
            await page.wait_for_selector('text="COMPLETED"', timeout=60000)
            print("Test A passed: Agent completed successfully.")
        except Exception as e:
            print("Test A failed or timed out waiting for COMPLETED.")
            await page.screenshot(path="test_a_fail.png")

        # Start a new session for Test B
        print("\n--- TEST B: Review ---")
        # Click new session button (the plus icon)
        await page.click('button:has(.lucide-plus)')
        await page.fill('input[placeholder*="What should the agent do?"]', 'Buy me a laptop for ₹75,000.')
        await page.click('button:has-text("Start Agent Run")')

        try:
            await page.wait_for_selector('text="REVIEW_REQUIRED"', timeout=60000)
            print("Test B passed: Agent stopped at REVIEW_REQUIRED.")
        except Exception as e:
            print("Test B failed.")
            await page.screenshot(path="test_b_fail.png")

        # Test C: Approve
        print("\n--- TEST C: Approve ---")
        try:
            await page.click('button:has-text("Go To Approvals")')
            await page.wait_for_selector('text="Pending Review"', timeout=10000)
            # Click the first pending approval row
            await page.click('tr:has-text("Pending Review")')
            # Click Approve button in details pane
            await page.click('button:has-text("Approve Request")')
            print("Approval submitted via UI.")
            
            # Go back to console
            await page.click('a[href="/app/console"]')
            # Click the recent agent
            await page.click('text="Finshield Retail Agent"')
            
            # Click Resume Run
            await page.click('button:has-text("Resume Run")')
            await page.wait_for_selector('text="COMPLETED"', timeout=60000)
            print("Test C passed: Agent resumed and completed successfully.")
        except Exception as e:
            print(f"Test C failed: {e}")
            await page.screenshot(path="test_c_fail.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
