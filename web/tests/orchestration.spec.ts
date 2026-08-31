import { expect, test, type Page } from '@playwright/test';

type RunOverrides = Partial<{
  status: string;
  approvals: Array<Record<string, unknown>>;
  verification: Array<Record<string, unknown>>;
  events: Array<Record<string, unknown>>;
  reconciliation: Record<string, unknown> | null;
  budget: Record<string, unknown>;
}>;

function mockRun(overrides: RunOverrides = {}) {
  return {
    run_id: 'test-run-1',
    objective: 'Test governed orchestration',
    status: overrides.status || 'APPROVAL_REQUIRED',
    execution_mode: 'THINK_WORK_CHECK',
    classification: {
      task_type: 'coding',
      sensitivity: 'CONFIDENTIAL',
      required_roles: ['PLANNER', 'THINKER', 'WORKER', 'CHECKER', 'RECONCILER'],
      approval_requirement: true,
    },
    nodes: [
      { node_id: 'planner-1', role: 'PLANNER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.76, dependencies: [] },
      { node_id: 'thinker-1', role: 'THINKER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.76, dependencies: [] },
      { node_id: 'worker-1', role: 'WORKER', status: 'COMPLETED', assigned_provider: 'coding_model', confidence: 0.8, dependencies: ['thinker-1'] },
      { node_id: 'checker-1', role: 'CHECKER', status: 'COMPLETED', assigned_provider: 'checker_model', confidence: 0.55, dependencies: ['worker-1'] },
      { node_id: 'reconciler-1', role: 'RECONCILER', status: 'COMPLETED', assigned_provider: 'reasoning_model', confidence: 0.54, dependencies: ['checker-1'] },
    ],
    routing_decisions: [
      { selected_provider: 'coding_model', candidate_providers: ['coding_model', 'checker_model'], rejected_providers: [], selection_reason: 'Selected by task fit.' },
    ],
    budget: {
      input_tokens_used: 0,
      output_tokens_used: 0,
      provider_cost_used: 0,
      nodes_used: 5,
      retries_used: 0,
      hard_limit_reached: false,
      ...overrides.budget,
    },
    verification: overrides.verification || [
      {
        verification_result: 'DISPUTED',
        confidence_score: 0.55,
        evidence_quality: 'test',
        contradictions: ['Worker output did not prove external action remained disabled.'],
        unresolved_uncertainty: ['External action boundary must be confirmed.'],
      },
    ],
    reconciliation: overrides.reconciliation ?? {
      verified_result: { claims: [] },
      supported_inference: [],
      unresolved_issue: ['External action boundary must be confirmed.'],
      principal_decision_required: ['Principal review recommended for unresolved disagreement.'],
      disputed_claims: [{ claim: 'Worker output did not prove external action remained disabled.', resolution: 'unresolved' }],
      final_confidence: 0.54,
    },
    approvals: overrides.approvals || [
      { approval_id: 'approval-1', requested_action: 'Approve governed orchestration result', reason: 'Approval required by policy.', status: 'REQUESTED' },
    ],
    events: overrides.events || [
      { sequence: 1, event_type: 'RUN_PLANNED', actor_role: 'PLANNER', created_at: 'mock' },
      { sequence: 2, event_type: 'NODE_COMPLETED', actor_role: 'WORKER', created_at: 'mock' },
      { sequence: 3, event_type: 'APPROVAL_REQUESTED', actor_role: 'GOVERNANCE_REVIEWER', created_at: 'mock' },
    ],
  };
}

async function gotoCommandCenter(page: Page) {
  await page.goto('/orchestration');
  await expect(page.getByTestId('orchestration-command-center')).toBeVisible();
}

test('new run form renders and selectors update', async ({ page }) => {
  await gotoCommandCenter(page);

  await expect(page.getByText('New Run')).toBeVisible();
  await expect(page.getByLabel('Objective')).toBeVisible();
  await expect(page.getByLabel('Constraints')).toBeVisible();

  await page.getByLabel('Execution Mode').selectOption('PARALLEL_COMPARE');
  await page.getByLabel('Provider Policy').selectOption('checker-only');
  await page.getByLabel('Sensitivity').selectOption('RESTRICTED');

  await expect(page.getByLabel('Execution Mode')).toHaveValue('PARALLEL_COMPARE');
  await expect(page.getByLabel('Provider Policy')).toHaveValue('checker-only');
  await expect(page.getByText('checker-only')).toBeVisible();
});

test('budget fields render and enforce numeric minimums', async ({ page }) => {
  await gotoCommandCenter(page);

  const maxNodes = page.getByLabel('Max Nodes');
  const inputTokens = page.getByLabel('Input Tokens');
  await expect(maxNodes).toHaveValue('12');
  await expect(inputTokens).toHaveValue('8000');

  await maxNodes.fill('0');
  await expect(maxNodes).toHaveJSProperty('validity.valid', false);
});

test('execution graph, role cards, approval, disagreement, and audit panels render', async ({ page }) => {
  await gotoCommandCenter(page);

  await expect(page.getByText('Execution Graph')).toBeVisible();
  await expect(page.getByText('PLANNER', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('WORKER', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('CHECKER', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Approval', { exact: true })).toBeVisible();
  await expect(page.getByText('REQUESTED', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('DISPUTED', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Evidence And Confidence')).toBeVisible();
  await expect(page.getByText('Audit And Evidence Timeline')).toBeVisible();
});

test('starting a run sends selected provider policy and renders completed state', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('sintraprime_token', 'test-token'));
  await page.route('**/api/orchestration/execute', async (route) => {
    expect(route.request().headers().authorization).toBe('Bearer test-token');
    const payload = route.request().postDataJSON();
    expect(payload.budget_limits.approved_providers).toEqual(['checker_model']);
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(mockRun({
        status: 'COMPLETED',
        approvals: [],
        verification: [{ verification_result: 'PASSED', confidence_score: 0.92, evidence_quality: 'test', contradictions: [], unresolved_uncertainty: [] }],
        reconciliation: { verified_result: { claims: ['Tests pass'] }, supported_inference: [], unresolved_issue: [], principal_decision_required: [], disputed_claims: [], final_confidence: 0.9 },
        events: [{ sequence: 1, event_type: 'RUN_COMPLETED', actor_role: 'RECONCILER', created_at: 'mock' }],
      })),
    });
  });

  await gotoCommandCenter(page);
  await page.getByLabel('Provider Policy').selectOption('checker-only');
  await page.getByRole('button', { name: 'Start Mock Run' }).click();

  await expect(page.getByText('COMPLETED').first()).toBeVisible();
  await expect(page.getByText('No Principal approval pending.')).toBeVisible();
  await expect(page.getByText('RUN_COMPLETED')).toBeVisible();
});

test('provider-failure state renders retry and failure event', async ({ page }) => {
  await page.route('**/api/orchestration/execute', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(mockRun({
        events: [
          { sequence: 1, event_type: 'RUN_PLANNED', actor_role: 'PLANNER', created_at: 'mock' },
          { sequence: 2, event_type: 'PROVIDER_FAILED', actor_role: 'WORKER', created_at: 'mock' },
          { sequence: 3, event_type: 'APPROVAL_REQUESTED', actor_role: 'GOVERNANCE_REVIEWER', created_at: 'mock' },
        ],
        budget: { retries_used: 1 },
      })),
    });
  });

  await gotoCommandCenter(page);
  await page.getByRole('button', { name: 'Start Mock Run' }).click();

  await expect(page.getByText('PROVIDER_FAILED')).toBeVisible();
  await expect(page.getByText('Retries')).toBeVisible();
  await expect(page.locator('div').filter({ has: page.getByText('Retries', { exact: true }) }).filter({ has: page.getByText('1', { exact: true }) }).first()).toBeVisible();
});

test('principal approval cannot be bypassed from the command center', async ({ page }) => {
  await gotoCommandCenter(page);

  await expect(page.getByText('REQUESTED', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /^Approve$/i })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /bypass/i })).toHaveCount(0);
});

test('mobile rendering remains usable with no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await gotoCommandCenter(page);

  await expect(page.getByText('Orchestration Command Center')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Mock Run' })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});

test('operations floor orchestration integration remains visible without overflow', async ({ page }) => {
  await page.goto('/operations-floor');
  await expect(page.getByTestId('operations-floor')).toBeVisible();
  await expect(page.getByText('Adaptive Orchestration Activity')).toBeVisible();
  await expect(page.getByText('Principal decision required')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});
