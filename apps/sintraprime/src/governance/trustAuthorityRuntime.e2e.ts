import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { ReceiptLedger } from '../audit/receiptLedger.js';
import { Executor } from '../core/executor.js';
import { Orchestrator } from '../core/orchestrator.js';
import { Planner } from '../core/planner.js';
import { PolicyGate } from './policyGate.js';
import { ToolRegistry } from '../tools/toolRegistry.js';
import {
  registerTrustAuthorityTools,
  type PrimaryLawProvider,
} from '../tools/trust/trustAuthorityTools.js';
import type { Tool } from '../types/index.js';

class PassiveTool implements Tool {
  constructor(
    readonly name: string,
    readonly description: string,
    private readonly output: any = { ok: true },
  ) {}

  async execute(args: any): Promise<any> {
    return { ...this.output, args };
  }
}

function primaryProvider(mode: 'none' | 'verified' | 'nonprimary'): PrimaryLawProvider {
  return {
    async verify(request) {
      if (mode === 'none') {
        return { authorities: [], jurisdiction: request.jurisdiction };
      }
      if (mode === 'nonprimary') {
        return {
          jurisdiction: request.jurisdiction ?? 'New Jersey',
          authorities: [
            {
              title: 'Secondary commentary fixture',
              citation: 'Secondary source only',
              url: 'https://example.com/secondary-commentary',
              jurisdiction: request.jurisdiction ?? 'New Jersey',
              sourceKind: 'official_guidance',
              primarySource: false,
            },
          ],
        };
      }
      return {
        jurisdiction: request.jurisdiction ?? 'New Jersey',
        authorities: [
          {
            title: 'Official primary authority test fixture',
            citation: 'N.J. Stat. test-primary-authority',
            url: 'https://www.njleg.state.nj.us/test-primary-authority',
            jurisdiction: request.jurisdiction ?? 'New Jersey',
            sourceKind: 'statute',
            primarySource: true,
            checkedAt: new Date().toISOString(),
          },
        ],
      };
    },
  };
}

async function buildSystem(provider: PrimaryLawProvider) {
  const storageDir = await mkdtemp(join(tmpdir(), 'sintraprime-trust-authority-'));
  const ledger = new ReceiptLedger({ storageDir, enableChaining: false });
  const registry = new ToolRegistry();

  registerTrustAuthorityTools(registry, { primaryLawProvider: provider });
  registry.registerTool(new PassiveTool('analyze', 'safe analysis fixture'));
  registry.registerTool(new PassiveTool('execute', 'no-op external execution fixture'));
  registry.registerTool(new PassiveTool('create_document', 'safe report fixture'));

  const policyGate = new PolicyGate(
    {
      budgetPolicy: {
        id: 'rb-ta-2-test',
        name: 'RB-TA-2 permissive test policy',
        spendCaps: { daily: 1_000_000, weekly: 1_000_000, monthly: 1_000_000 },
        thresholds: { requiresApproval: 1_000_000 },
        perToolLimits: {},
      },
      approvalThreshold: 1_000_000,
      highRiskActions: [],
      autoApproveActions: [],
    },
    ledger,
  );

  const executor = new Executor(registry, ledger);
  const planner = new Planner(null);
  const orchestrator = new Orchestrator(policyGate, ledger, executor, planner);

  return { storageDir, ledger, registry, orchestrator };
}

function executedToolNames(ledger: ReceiptLedger): string[] {
  return ledger
    .getReceiptsByActor('executor')
    .filter((receipt) => receipt.action.startsWith('tool_executed:'))
    .map((receipt) => receipt.action.slice('tool_executed:'.length));
}

async function runCurrentLawBlockedScenario(
  id: string,
  providerMode: 'none' | 'nonprimary',
): Promise<void> {
  const system = await buildSystem(primaryProvider(providerMode));
  try {
    let blocked = false;
    try {
      await system.orchestrator.processTask({
        id,
        prompt: 'Determine the legal effect of the ISIAH TARIK HOWARD TRUST amendment and file it.',
        priority: 'high',
        requester: 'rb-ta-2-e2e',
        timestamp: new Date().toISOString(),
        context: {
          trustAuthority: {
            principalApproval: true,
            jurisdiction: 'New Jersey',
          },
        },
      });
    } catch (error) {
      blocked = /current law has not been verified/i.test(String(error));
    }

    assert.equal(blocked, true, `${providerMode} evidence must fail closed`);
    assert.deepEqual(executedToolNames(system.ledger), [
      'trust-instrument-authority',
      'weisss-trustee-handbook',
      'current-law-verifier',
    ]);
    assert.equal(system.ledger.getReceiptsByAction('trust_execution_blocked').length, 1);
  } finally {
    await rm(system.storageDir, { recursive: true, force: true });
  }
}

async function scenarioNoVerification(): Promise<void> {
  const system = await buildSystem(primaryProvider('none'));
  try {
    assert.ok(system.registry.getTool('trust-instrument-authority'));
    assert.ok(system.registry.getTool('weisss-trustee-handbook'));
    assert.ok(system.registry.getTool('current-law-verifier'));
  } finally {
    await rm(system.storageDir, { recursive: true, force: true });
  }
  await runCurrentLawBlockedScenario('rb-ta-2-no-verification', 'none');
}

async function scenarioRejectsNonPrimaryEvidence(): Promise<void> {
  await runCurrentLawBlockedScenario('rb-ta-2-nonprimary', 'nonprimary');
}

async function scenarioNoApproval(): Promise<void> {
  const system = await buildSystem(primaryProvider('verified'));
  try {
    let blocked = false;
    try {
      await system.orchestrator.processTask({
        id: 'rb-ta-2-no-approval',
        prompt: 'Determine the legal effect of the ISIAH TARIK HOWARD TRUST amendment and file it.',
        priority: 'high',
        requester: 'rb-ta-2-e2e',
        timestamp: new Date().toISOString(),
        context: {
          trustAuthority: {
            principalApproval: false,
            jurisdiction: 'New Jersey',
          },
        },
      });
    } catch (error) {
      blocked = /principal\/trustee approval is not documented/i.test(String(error));
    }

    assert.equal(blocked, true, 'verified law must not bypass trustee approval');
    assert.deepEqual(executedToolNames(system.ledger), [
      'trust-instrument-authority',
      'weisss-trustee-handbook',
      'current-law-verifier',
    ]);
    const updates = system.ledger.getReceiptsByAction('current_law_verification_updated');
    assert.equal(updates.length, 1);
    assert.equal(updates[0]?.result?.verification?.status, 'VERIFIED_CURRENT');
  } finally {
    await rm(system.storageDir, { recursive: true, force: true });
  }
}

async function scenarioVerifiedAndApproved(): Promise<void> {
  const system = await buildSystem(primaryProvider('verified'));
  try {
    const job = await system.orchestrator.processTask({
      id: 'rb-ta-2-green-path',
      prompt: 'Determine the legal effect of the ISIAH TARIK HOWARD TRUST amendment and file it.',
      priority: 'high',
      requester: 'rb-ta-2-e2e',
      timestamp: new Date().toISOString(),
      context: {
        trustAuthority: {
          principalApproval: true,
          jurisdiction: 'New Jersey',
        },
      },
    });

    assert.equal(job.status, 'completed');
    assert.deepEqual(executedToolNames(system.ledger), [
      'trust-instrument-authority',
      'weisss-trustee-handbook',
      'current-law-verifier',
      'analyze',
      'execute',
      'create_document',
    ]);

    const updates = system.ledger.getReceiptsByAction('current_law_verification_updated');
    assert.equal(updates.length, 1);
    assert.equal(updates[0]?.result?.verification?.status, 'VERIFIED_CURRENT');
    assert.equal(system.ledger.getReceiptsByAction('trust_execution_blocked').length, 0);
  } finally {
    await rm(system.storageDir, { recursive: true, force: true });
  }
}

await scenarioNoVerification();
await scenarioRejectsNonPrimaryEvidence();
await scenarioNoApproval();
await scenarioVerifiedAndApproved();

console.log('RB-TA-2 Runtime Authority Adapters E2E: PASS');
console.log('Proof: trust instrument -> Weiss -> primary current law -> approval -> execution.');
console.log('No external filing or transaction was performed; the execute adapter was a no-op fixture.');
