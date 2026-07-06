import { test, expect } from '@playwright/test';
import { E2E_EMAIL, E2E_PASSWORD, loginViaAPI } from './fixtures/auth';

test.describe.configure({ mode: 'serial' });

test.describe('Login → Document Vault E2E', () => {
  test('login page renders the email/password form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input#email')).toBeVisible();
    await expect(page.locator('input#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toHaveText(/Sign In/i);
  });

  test('real API login returns a valid access token', async () => {
    const login = await loginViaAPI();
    expect(login.access_token).toBeTruthy();
    expect(login.token_type).toBe('bearer');
    expect(login.expires_in).toBeGreaterThan(0);
    expect(login.role).toBeTruthy();
  });

  test('browser login with valid credentials reaches document vault', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input#email', E2E_EMAIL);
    await page.fill('input#password', E2E_PASSWORD);
    await page.click('button[type="submit"]');

    // Wait for post-login redirect (navigates to /documents in current implementation)
    await page.waitForURL('**/documents', { timeout: 10000 });
    await expect(page.locator('text=Document Vault')).toBeVisible();
  });

  test('unauthenticated access to /documents redirects to /login', async ({ page, context }) => {
    // Ensure no token is present
    await context.clearCookies();
    await page.goto('/documents');
    await page.waitForURL('**/login', { timeout: 10000 });
  });

  test('document vault shows empty-state when no documents exist', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input#email', E2E_EMAIL);
    await page.fill('input#password', E2E_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/documents', { timeout: 10000 });

    const docs = page.locator('[data-testid="document-item"]');
    await expect(docs).toHaveCount(0);
  });
});
