import { test, expect, type Route } from '@playwright/test';

test('SP-MC3D-001 enters the governed 3D Command Town', async ({ page }) => {
  const authToken = 'mission-control-smoke-token';
  const mutatingRequests: string[] = [];
  const authorizationHeaders: string[] = [];
  page.on('request', (request) => {
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method())) {
      mutatingRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  await page.addInitScript((token) => {
    localStorage.setItem('sintraprime_token', token);
  }, authToken);
  const fulfillProjection = (body: object) => async (route: Route) => {
    if (route.request().method() === 'GET') {
      authorizationHeaders.push(route.request().headers().authorization);
    }
    await route.fulfill({ json: body });
  };
  await page.route('**/api/v1/mission-control/summary', fulfillProjection({
    environment: 'e2e',
    health: 'healthy',
    telemetry_updated_at: '2026-09-27T15:00:00Z',
    telemetry_source: 'playwright',
    active_agents: { value: 17, status: 'verified' },
    active_runs: { value: 4, status: 'verified' },
    pending_decisions: { value: 0, status: 'verified' },
    open_incidents: { value: 0, status: 'verified' },
    daily_spend_usd: { value: 0, status: 'verified' },
    kill_switch: { value: 'ready', status: 'verified' },
    evidence_items: { value: 29, status: 'verified' },
    scheduled_jobs: { value: 0, status: 'verified' },
    subsystems: {},
  }));
  await page.route('**/api/v1/mission-control/principal-brief', fulfillProjection({
    schema_version: 'sp-principal-brief-v2',
    generated_at: '2026-09-27T15:00:00Z',
    available: true,
    unavailable_reason: null,
    active_missions: ['alpha', 'beta', 'gamma'],
    agents: [],
    blocked_agents: ['delta', 'epsilon'],
    pending_approvals: [],
    external_effect_attempts: [],
    security_events: [],
    recent_receipt_ids: [],
    authority_expirations: [],
    memory_change_summary: {},
    recommended_principal_decisions: [],
  }));
  await page.route('**/api/v1/mission-control/sigma-gate', fulfillProjection({
    execution_scoped: 'ENABLED',
    tenant_scoped: 'ENABLED',
    platform_break_glass: 'DISABLED',
    gate: {
      gate_id: 'SIGMA_LEASE_EXPIRY_CONTINUATION_GATE',
      state: 'SATISFIED',
      description: 'E2E fixture',
      criteria: [],
      cancellation_controls: 'ENABLED',
      blocking_phase_3b: false,
    },
    reason: 'E2E fixture',
  }));

  await page.goto('/mission-control/town');

  await expect(page.getByRole('heading', { name: 'SintraPrime Command Town' })).toBeVisible();
  await expect(page.locator('.mc-town-hud > div')).toContainText([
    'ACTIVE AGENTS17',
    'ACTIVE MISSIONS3',
    'BLOCKED AGENTS2',
    'EVIDENCE ITEMS29',
    'AUTHORITY GATESATISFIED',
  ]);
  await expect.poll(() => authorizationHeaders.length).toBeGreaterThanOrEqual(3);
  const expectedAuthorization = ['Bear', 'er ', authToken].join('');
  expect(authorizationHeaders.every((header) => header === expectedAuthorization)).toBe(true);
  const enter = page.getByRole('button', { name: /ENTER 3D/i });
  await expect(enter).toBeVisible();
  await enter.click();

  await expect(page.getByText('COMMAND TOWN 3D')).toBeVisible();
  await expect(page.getByText(/NO EXECUTION AUTHORITY/i)).toBeVisible();
  await expect(page.locator('.mc3d-renderer canvas')).toBeVisible();
  await expect(page.getByRole('button', { name: 'ENTER WORLD' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'EXIT 3D' })).toBeVisible();
  expect(mutatingRequests, 'visualization must not issue mutating network requests').toEqual([]);
});
