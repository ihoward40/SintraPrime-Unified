import { request, type APIRequestContext } from '@playwright/test';

/**
 * E2E authentication helpers.
 *
 * These use the real backend login endpoint. They DO NOT mock auth.
 * The returned JWT is stored in localStorage exactly as the frontend expects.
 */

export const E2E_EMAIL = 'e2e-attorney@sintraprime.test';
export const E2E_PASSWORD = 'E2E-Test-Pass-1234!';
export const E2E_TENANT_ID = 'e2e00000-0000-0000-0000-000000000001';

export interface LoginResult {
  access_token: string;
  user_id: string;
  tenant_id: string;
  role: string;
  expires_in: number;
}

export async function loginViaAPI(
  baseURL: string = process.env.VITE_API_BASE_URL || 'http://localhost:8000'
): Promise<LoginResult> {
  const ctx: APIRequestContext = await request.newContext({ baseURL });
  try {
    const response = await ctx.post('/api/v1/auth/login', {
      data: { email: E2E_EMAIL, password: E2E_PASSWORD },
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(`E2E login failed: ${response.status()} ${body}`);
    }

    return (await response.json()) as LoginResult;
  } finally {
    await ctx.dispose();
  }
}

export function authStorage(token: string) {
  return {
    origins: [],
    cookies: [],
    localStorage: [
      { name: 'sintraprime_token', value: token },
      { name: 'sintraprime_refresh_token', value: 'e2e-refresh-placeholder' },
    ],
  };
}
