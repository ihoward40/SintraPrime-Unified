import { test, expect, type Page } from '@playwright/test';

const emptyEnvelope = JSON.stringify({ items: [] });

async function mockMatterEndpoints(page: Page) {
  await page.route('**/api/v1/matters/matter-1/intelligence/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: emptyEnvelope });
  });
}

test.describe('Matter workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('sintraprime_token', 'frontend-test-token');
      localStorage.setItem('sintraprime_token_expires_at', String(Date.now() + 60 * 60 * 1000));
    });
    await mockMatterEndpoints(page);
  });

  test('renders the protected matter workspace and empty states', async ({ page }) => {
    await page.goto('/matters/matter-1');

    await expect(page.getByTestId('matter-workspace')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Matter workspace' })).toBeVisible();
    await expect(page.getByText('Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Chronology' })).toBeVisible();
    await expect(page.getByText('Evidence graph is empty')).toBeVisible();
    await expect(page.getByText('No open findings')).toBeVisible();
    await expect(page.getByText('Read-only review posture')).toBeVisible();
  });

  test('surfaces protected API failures without inventing matter records', async ({ page }) => {
    await page.unroute('**/api/v1/matters/matter-1/intelligence/**');
    await page.route('**/api/v1/matters/matter-1/intelligence/**', async (route) => {
      await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'service unavailable' }) });
    });
    await page.goto('/matters/matter-1');

    await expect(page.getByRole('alert')).toContainText('Some matter data could not be loaded');
    await expect(page.getByText('No parties returned')).toBeVisible();
    await expect(page.getByText('No accounts returned')).toBeVisible();
    await expect(page.getByText('No assessments returned')).toBeVisible();
  });
});