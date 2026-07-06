import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for SintraPrime Document Vault.
 *
 * Pre-requisites:
 *   1. Backend is running on VITE_API_BASE_URL (defaults to http://localhost:8000).
 *   2. Database is seeded with E2E tenant/user via:
 *        python -m portal.scripts.seed_e2e
 *   3. MinIO bucket exists.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // shared seeded user; sequential safer for E2E
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    headless: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
