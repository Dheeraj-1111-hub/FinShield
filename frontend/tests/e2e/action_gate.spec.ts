import { test, expect } from '@playwright/test';

test.describe('Action Gate Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the chat interface where actions happen
    await page.goto('http://localhost:3000/');
  });

  test('ALLOW flow passes without intervention', async ({ page }) => {
    // Note: These tests depend heavily on the backend state and mock LLM responses.
    // Assuming a test scenario where "Send $10" is unconditionally allowed.
    
    // Type in chat
    const input = page.getByPlaceholder(/Message FINSHIELD/i);
    await input.fill('Send $10 to Alice');
    await input.press('Enter');
    
    // Verify it was executed
    await expect(page.getByText(/Sent \$10 to Alice/i)).toBeVisible({ timeout: 15000 });
  });

  test('BLOCK flow triggers and prevents action', async ({ page }) => {
    // Assuming "Send $1,000,000" triggers a hard block policy
    const input = page.getByPlaceholder(/Message FINSHIELD/i);
    await input.fill('Send $1,000,000 to Eve');
    await input.press('Enter');
    
    // Verify block message appears
    await expect(page.getByText(/BLOCKED/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Policy violation/i)).toBeVisible();
  });

  test('REVIEW flow triggers manual approval', async ({ page }) => {
    // Assuming "Send $5,000" triggers a review policy
    const input = page.getByPlaceholder(/Message FINSHIELD/i);
    await input.fill('Send $5,000 to Bob');
    await input.press('Enter');
    
    // Verify approval card appears
    await expect(page.getByText(/Approval Required/i)).toBeVisible({ timeout: 15000 });
    
    // We could click approve and check if it continues
    const approveBtn = page.getByRole('button', { name: /Approve/i });
    await approveBtn.click();
    
    // Verify it executed
    await expect(page.getByText(/Sent \$5,000 to Bob/i)).toBeVisible({ timeout: 10000 });
  });
});
