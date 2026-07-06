import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for SintraPrime.
 *
 * Environment variables:
 *   E2E_EMAIL     — test user email (default: e2e-attorney@sintraprime.test)
 *   E2E_PASSWORD  — test user password (default: E2E-Test-Pass-1234!)
 *
 * The backend must be running on VITE_API_BASE_URL. Playwright starts the
 * Vite dev server automatically via webServer; it does NOT start the FastAPI
 * backend (do that separately with `uvicorn portal.main:app`).
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // shared backend DB state => sequential E2E tests
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
