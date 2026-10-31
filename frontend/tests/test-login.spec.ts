import { test, expect } from '@playwright/test';

test('login test', async ({ page }) => {
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText));
    
    await page.goto('http://localhost:8081');
    const emailInput = page.getByRole('textbox', { name: 'Email address' });
    const passInput = page.locator('input[type="password"]');
    await emailInput.fill('admin@finshield.dev');
    await passInput.fill('password');
    console.log("Filled form, clicking submit");
    await page.getByRole('button', { name: /sign in|login/i }).click();
    console.log("Clicked submit, waiting 5 seconds");
    await page.waitForTimeout(5000);
});
