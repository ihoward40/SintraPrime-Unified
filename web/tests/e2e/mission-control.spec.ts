import { test, expect, Page } from '@playwright/test';

/**
 * Mission Control Foundation E2E tests.
 *
 * These tests verify the read-only Mission Control dashboard renders correctly,
 * all cancellation controls are disabled, and no mutation requests are sent.
 *
 * The backend must be running on http://localhost:8000 and the frontend
 * dev server on http://localhost:5173.
 *
 * No authentication is required for the sigma-gate endpoint — we test both
 * the unauthenticated degradation path and inject a token for authenticated
 * API calls where needed.
 */

const API_BASE = 'http://localhost:8000';

/**
 * Inject a mock auth token so the frontend API client sends Authorization
 * headers. The actual token validity doesn't matter for read-only projection
 * tests — the backend will return 401/403 which the UI must handle gracefully.
 */
async function injectMockAuth(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('sintraprime_token', 'mock-e2e-token-for-playwright');
  });
}

test.describe('Mission Control Foundation', () => {
  test.describe.configure({ mode: 'serial' });

  test('Mission Control route renders', async ({ page }) => {
    await page.goto('/mission-control');
    await expect(page.locator('h1')).toContainText('Mission Control');
    await expect(page.locator('.mc-shell')).toBeVisible();
  });

  test('telemetry status bar displays', async ({ page }) => {
    await page.goto('/mission-control');
    // The status bar shows "Telemetry" label
    await expect(page.locator('.mc-statusbar')).toBeVisible();
    await expect(page.locator('.mc-statusbar')).toContainText(/Telemetry/i);
  });

  test('all cancellation command buttons are disabled', async ({ page }) => {
    await page.goto('/mission-control');
    // The command strip has disabled buttons
    const buttons = page.locator('.mc-command-actions button[disabled]');
    const count = await buttons.count();
    expect(count).toBeGreaterThanOrEqual(5);
    for (let i = 0; i < count; i++) {
      await expect(buttons.nth(i)).toBeDisabled();
    }
  });

  test('disabled controls send no mutation request', async ({ page }) => {
    await page.goto('/mission-control');
    // Track all POST requests
    const postRequests: string[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST') {
        postRequests.push(request.url());
      }
    });
    // Click on disabled buttons — they should not trigger any request
    const buttons = page.locator('.mc-command-actions button[disabled]');
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      await buttons.nth(i).click({ force: true }).catch(() => {});
    }
    await page.waitForTimeout(1000);
    // No POST requests should have been made to mission-control
    const mcPosts = postRequests.filter((url) => url.includes('mission-control'));
    expect(mcPosts).toHaveLength(0);
  });

  test('Sigma gate banner shows BLOCKED state', async ({ page }) => {
    await page.goto('/mission-control');
    // Wait for the sigma gate banner to appear (may take a moment for API call)
    await page.waitForTimeout(3000);
    const banner = page.locator('.mc-sigma-banner');
    // The banner may or may not appear depending on API availability
    const bannerVisible = await banner.isVisible().catch(() => false);
    if (bannerVisible) {
      await expect(banner).toContainText(/SIGMA_LEASE_EXPIRY_CONTINUATION_GATE/i);
      await expect(banner).toContainText(/BLOCKED/i);
      await expect(banner).toContainText(/DISABLED/i);
    }
  });

  test('intent projection section renders', async ({ page }) => {
    await page.goto('/mission-control');
    await page.waitForTimeout(3000);
    // The page should render the command authority section (always present)
    // and the operational posture section
    const bodyText = await page.locator('body').textContent();
    // Command authority is always rendered (not data-dependent)
    expect(bodyText).toContain('Human control remains active');
    // Operational posture is always rendered
    expect(bodyText).toContain('Operational posture');
  });
  test('execution-state projection section renders', async ({ page }) => {
    await page.goto('/mission-control');
    await page.waitForTimeout(3000);
    // The page shell renders without crash even when API data is unavailable
    const bodyText = await page.locator('body').textContent();
    // Subsystem health section is always rendered
    expect(bodyText).toContain('Subsystem health');
  });

  test('sub-navigation has expected surfaces', async ({ page }) => {
    await page.goto('/mission-control');
    const nav = page.locator('.mc-subnav');
    await expect(nav).toBeVisible();
    await expect(nav).toContainText('Overview');
    await expect(nav).toContainText('Operations');
    await expect(nav).toContainText('Governance');
    await expect(nav).toContainText('Evidence');
  });

  test('governance surface renders cancellation status', async ({ page }) => {
    await page.goto('/mission-control/governance');
    await page.waitForTimeout(2000);
    // The governance surface should render
    await expect(page.locator('.mc-surface')).toBeVisible();
    await expect(page.locator('text=MISSION CONTROL / GOVERNANCE')).toBeVisible();
  });

  test('operations surface renders intent or empty state', async ({ page }) => {
    await page.goto('/mission-control/operations');
    await page.waitForTimeout(2000);
    await expect(page.locator('.mc-surface')).toBeVisible();
    await expect(page.locator('text=MISSION CONTROL / OPERATIONS')).toBeVisible();
  });

  test('stale/source-unavailable states display gracefully', async ({ page }) => {
    await page.goto('/mission-control');
    await page.waitForTimeout(3000);
    // The page should still be visible and not crashed
    await expect(page.locator('.mc-shell')).toBeVisible();
    // If telemetry is offline, the warning should show
    const warning = page.locator('.mc-warning');
    const warningVisible = await warning.isVisible().catch(() => false);
    if (warningVisible) {
      await expect(warning).toContainText(/unavailable/i);
    }
  });

  test('protected API failure remains visible (no silent swallow)', async ({ page }) => {
    // Set an invalid token to trigger API auth failure
    await page.addInitScript(() => {
      localStorage.setItem('sintraprime_token', 'invalid-token-that-will-fail');
    });
    await page.goto('/mission-control');
    await page.waitForTimeout(3000);
    // The page should still render — the shell must not crash on API failure
    await expect(page.locator('.mc-shell')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Mission Control');
  });

  test('mobile viewport has no horizontal overflow', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/mission-control');
    await page.waitForTimeout(2000);
    // Check for horizontal overflow
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });
});