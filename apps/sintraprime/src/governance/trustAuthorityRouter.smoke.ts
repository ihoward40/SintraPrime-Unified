import assert from 'node:assert/strict';
import type { PlanStep, TaskRequest } from '../types/index.js';
import {
  attachTrustAuthorityRoute,
  evaluateTrustAuthorityStep,
  routeTrustAuthority,
} from './trustAuthorityRouter.js';

function request(overrides: Partial<TaskRequest> = {}): TaskRequest {
  return {
    id: 'task_trust_001',
    prompt: 'Analyze trustee authority under the ISIAH TARIK HOWARD TRUST.',
    priority: 'medium',
    requester: 'smoke-test',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

const researchOnly = routeTrustAuthority(request());
assert.equal(researchOnly.isTrustRelated, true);
assert.deepEqual(researchOnly.authorityOrder, [
  'trust-instrument-authority',
  'weisss-trustee-handbook',
  'current-law-verifier',
]);
assert.equal(researchOnly.executionAllowed, true);

const legalEffect = routeTrustAuthority(
  request({
    prompt: 'Determine the legally binding effect of this trust amendment and file it.',
  }),
);
assert.equal(legalEffect.legalEffectRequested, true);
assert.equal(legalEffect.externalExecutionRequested, true);
assert.equal(legalEffect.currentLawVerification.status, 'NOT_YET_VERIFIED');
assert.equal(legalEffect.executionAllowed, false);
assert.equal(legalEffect.blockingReasons.length, 2);

const authorityResearchStep: PlanStep = {
  id: 'verify_1',
  description: 'Run current-law-verifier for the governing jurisdiction',
  tool: 'current-law-verifier',
  args: {
    authorityStage: 'current-law-verifier',
    task: 'current trust law',
    jurisdiction: 'New Jersey',
  },
  dependencies: [],
};
assert.equal(evaluateTrustAuthorityStep(authorityResearchStep, legalEffect).allowed, true);

const executionStep: PlanStep = {
  id: 'execute_1',
  description: 'File the trust amendment externally',
  tool: 'execute',
  args: { action: 'file trust amendment' },
  dependencies: [],
};
assert.equal(evaluateTrustAuthorityStep(executionStep, legalEffect).allowed, false);

// Caller-supplied VERIFIED_CURRENT must never bypass the explicit verifier stage.
const attemptedPreseed = routeTrustAuthority(
  request({
    prompt: 'Determine the legally binding effect of this trust amendment and file it.',
    context: {
      trustAuthority: {
        principalApproval: true,
        jurisdiction: 'New Jersey',
        currentLawVerification: {
          status: 'VERIFIED_CURRENT',
          jurisdiction: 'New Jersey',
          authorities: ['caller-supplied-placeholder'],
          verifier: 'current-law-verifier',
          verifiedAt: new Date().toISOString(),
        },
      },
    },
  }),
);
assert.equal(attemptedPreseed.currentLawVerification.status, 'NOT_YET_VERIFIED');
assert.equal(attemptedPreseed.executionAllowed, false);
assert.equal(evaluateTrustAuthorityStep(executionStep, attemptedPreseed).allowed, false);

const governed = attachTrustAuthorityRoute(request());
assert.ok(governed.context?.trustAuthorityRoute);
assert.equal(
  governed.context.trustAuthorityRoute.authorityOrder[0],
  'trust-instrument-authority',
);

console.log('Trust Authority Router smoke test: PASS');
