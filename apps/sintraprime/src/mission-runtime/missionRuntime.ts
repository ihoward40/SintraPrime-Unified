import { Executor } from '../core/executor.js';
import { ReceiptLedger } from '../audit/receiptLedger.js';
import { AuthorityEngine } from './authorityEngine.js';
import { BudgetGovernor } from './budgetGovernor.js';
import { ModelRouter } from './modelRouter.js';
import type { MissionSpec, MissionState, ProposedAction } from './types.js';

export interface MissionRuntimeDependencies {
  executor: Executor;
  receiptLedger: ReceiptLedger;
  authority: AuthorityEngine;
  budget: BudgetGovernor;
  models: ModelRouter;
}

export class MissionRuntime {
  constructor(private readonly deps: MissionRuntimeDependencies) {}

  createState(spec: MissionSpec): MissionState {
    return {
      missionId: spec.id,
      status: 'ready',
      spent: 0,
      iteration: 0,
      evidenceIds: [],
    };
  }

  async run(spec: MissionSpec, initialState?: MissionState, context?: unknown): Promise<MissionState> {
    let state = initialState ?? this.createState(spec);
    state = { ...state, status: 'running' };

    while (state.iteration < spec.maxIterations) {
      const proposals = await this.deps.models.collect(spec, state, context);
      const selected = this.deps.models.select(proposals);

      if (!selected || selected.stop || !selected.action) {
        await this.record(spec.id, 'mission_stopped:no_action', { iteration: state.iteration, proposals });
        return { ...state, status: 'stopped' };
      }

      const action: ProposedAction = {
        ...selected.action,
        id: `action_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
        missionId: spec.id,
      };

      const authority = this.deps.authority.evaluate(spec, action);
      await this.record(action.id, 'authority_decision', { action, authority });

      if (authority.decision === 'block') {
        await this.record(action.id, 'mission_action_blocked', { reason: authority.reason });
        return { ...state, status: 'stopped', lastActionId: action.id };
      }

      if (authority.decision === 'require_approval') {
        await this.record(action.id, 'mission_waiting_approval', {
          principalId: spec.authority.principalId,
          requiredLevel: authority.requiredLevel,
          reason: authority.reason,
          action,
        });
        return { ...state, status: 'waiting_approval', lastActionId: action.id };
      }

      const budget = this.deps.budget.check(spec, state, action);
      await this.record(action.id, 'budget_decision', { action, budget, spent: state.spent });
      if (!budget.allow) {
        await this.record(action.id, 'mission_budget_blocked', { reason: budget.reason });
        return { ...state, status: 'stopped', lastActionId: action.id };
      }

      const result = await this.deps.executor.executeTool(action.tool, action.args);
      state = this.deps.budget.apply(state, action);
      state = {
        ...state,
        iteration: state.iteration + 1,
        lastActionId: action.id,
        evidenceIds: [...state.evidenceIds, action.id],
      };

      await this.record(action.id, 'mission_action_completed', {
        modelId: action.modelId,
        agentId: action.agentId,
        tool: action.tool,
        actionClass: action.actionClass,
        estimatedCost: action.estimatedCost ?? 0,
        result,
      });
    }

    await this.record(spec.id, 'mission_iteration_limit_reached', { maxIterations: spec.maxIterations });
    return { ...state, status: 'stopped' };
  }

  private async record(toolCallId: string, action: string, result: unknown): Promise<void> {
    const id = `amr_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    await this.deps.receiptLedger.recordAction({
      id,
      toolCallId,
      actor: 'mission-runtime',
      action,
      timestamp: new Date().toISOString(),
      result,
      hash: '',
    });
  }
}
