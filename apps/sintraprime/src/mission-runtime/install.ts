import type { ReceiptLedger } from '../audit/receiptLedger.js';
import type { Executor } from '../core/executor.js';
import type { ToolRegistry } from '../tools/toolRegistry.js';
import { AuthorityEngine } from './authorityEngine.js';
import { BrowserL0Tool } from './adapters/browserL0Tool.js';
import { OpenAICompatibleModelAdapter } from './adapters/openAICompatibleModelAdapter.js';
import { BudgetGovernor } from './budgetGovernor.js';
import { MissionRuntime } from './missionRuntime.js';
import { ModelRouter } from './modelRouter.js';

export interface InstallMissionRuntimeArgs {
  toolRegistry: ToolRegistry;
  executor: Executor;
  receiptLedger: ReceiptLedger;
  modelAdapters?: Array<{
    id: string;
    baseUrl: string;
    model: string;
    apiKeyEnv?: string;
    timeoutMs?: number;
  }>;
}

/**
 * Installs the governed autonomy layer on top of SintraPrime's existing
 * ToolRegistry, Executor, and immutable ReceiptLedger.
 *
 * No provider receives execution authority. Models only propose actions;
 * the MissionRuntime authorizes, budgets, executes, and records them.
 */
export function installMissionRuntime(args: InstallMissionRuntimeArgs) {
  if (!args.toolRegistry.getTool('browser.l0')) {
    args.toolRegistry.registerTool(new BrowserL0Tool());
  }

  const models = new ModelRouter();
  for (const config of args.modelAdapters ?? []) {
    models.register(new OpenAICompatibleModelAdapter(config));
  }

  const authority = new AuthorityEngine();
  const budget = new BudgetGovernor();
  const runtime = new MissionRuntime({
    executor: args.executor,
    receiptLedger: args.receiptLedger,
    authority,
    budget,
    models,
  });

  return { runtime, models, authority, budget };
}

export function missionModelAdaptersFromEnv() {
  const raw = process.env.SINTRAPRIME_MODEL_ADAPTERS_JSON;
  if (!raw) return [];
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) throw new Error('SINTRAPRIME_MODEL_ADAPTERS_JSON must be a JSON array');
  return parsed;
}
