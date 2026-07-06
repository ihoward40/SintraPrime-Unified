import { request, type APIRequestContext } from '@playwright/test';

/**
 * E2E authentication helpers using the real backend login endpoint.
 *
 * These are intentionally separate from the frontend code so tests can
 * authenticate via API and then exercise the browser journey with a valid
 * localStorage token injected.
 */

export const E2E_EMAIL = process.env.E2E_EMAIL || 'e2e-attorney@sintraprime.test';
export const E2E_PASSWORD = process.env.E2E_PASSWORD || 'E2E-Test-Pass-1234!';
export const E2E_TENANT_ID = '00000000-0000-0000-0000-000000000e2e';

const API_BASE = process.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface APILoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  role: string;
  tenant_id: string;
}

/**
 * Authenticate via POST /api/v1/auth/login and return the access token.
 */
export async function loginViaAPI(): Promise<APILoginResponse> {
  const ctx = await request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: { 'Content-Type': 'application/json' },
  });

  try {
    const response = await ctx.post('/api/v1/auth/login', {
      data: { email: E2E_EMAIL, password: E2E_PASSWORD },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(`Login failed: ${response.status()} ${body}`);
    }

    return (await response.json()) as APILoginResponse;
  } finally {
    await ctx.dispose();
  }
}

/**
 * Call the backend seed script via a lightweight HTTP helper if one exists,
 * otherwise require the seeder to be run before the E2E suite.
 */
export async function ensureE2ESeed(): Promise<void> {
  // The deterministic seeder is run manually/CI-side before Playwright.
  // No-op here to keep tests isolated from DB mutation during runtime.
}
