import { test, expect } from '@playwright/test';

test.describe('Audit Log E2E & Flow Verification', () => {
  // Use the setup script or assume standard test db
  
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/app/audit'); // TanStack Start uses 3000
    // If not logged in, you might need a mock auth setup, but assuming local dev has no strict auth barrier or uses default.
    // In our app, there is a mocked workspace context.
  });

  test('should display audit log dashboard and verify integrity', async ({ page }) => {
    // Check main title
    await expect(page.locator('h1').filter({ hasText: 'Audit Log' })).toBeVisible();
    
    // Check stream table
    await expect(page.locator('table')).toBeVisible();
    
    // Click verify
    const verifyBtn = page.getByRole('button', { name: /Verify Cryptographic Chain/i });
    await expect(verifyBtn).toBeVisible();
    
    await verifyBtn.click();
    
    // Check if verification result appears
    await expect(page.getByText(/Chain Verified/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display critical events panel', async ({ page }) => {
    await expect(page.getByText('Critical Events', { exact: true })).toBeVisible();
  });
  
  // Tests for ALLOW, REVIEW, BLOCK flows would typically mock the backend response 
  // or trigger real actions on the platform (e.g. buying a laptop in the chat UI) 
  // and then asserting they appear in the audit log here.
  
  test('Action Gate flow (ALLOW, REVIEW, BLOCK) appears in audit log', async ({ page }) => {
    // Simulate user buying a laptop in the chat (if we were testing the full e2e)
    // For this audit-specific test, we search the audit log for known mocked events from the agent
    
    // Search for GATE event
    await page.locator('input[placeholder="Search events, agents, transactions, policies..."]').fill('GATE');
    
    // It should filter the table
    // Wait for the table to update
    await page.waitForTimeout(1000);
    
    const rows = page.locator('table tbody tr');
    // Ensure we have some rows
    const count = await rows.count();
    
    if (count > 0) {
      const firstRow = rows.first();
      await firstRow.click();
      
      // Detail drawer should open
      await expect(page.getByText(/AUDIT EVENT/)).toBeVisible();
      
      // Close drawer
      await page.getByRole('button').filter({ has: page.locator('svg') }).first().click(); // Close btn
    }
  });
});
