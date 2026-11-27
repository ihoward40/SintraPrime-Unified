import type { MissionSpec, MissionState, ProposedAction } from './types.js';

export class BudgetGovernor {
  check(spec: MissionSpec, state: MissionState, action: ProposedAction): { allow: boolean; reason: string } {
    const cost = action.estimatedCost ?? 0;

    if (cost < 0 || !Number.isFinite(cost)) {
      return { allow: false, reason: 'Invalid estimated cost' };
    }

    if (state.spent + cost > spec.budget.totalCap) {
      return {
        allow: false,
        reason: `Projected spend ${state.spent + cost} exceeds mission cap ${spec.budget.totalCap}`,
      };
    }

    return { allow: true, reason: 'Within mission budget' };
  }

  apply(state: MissionState, action: ProposedAction): MissionState {
    const cost = action.estimatedCost ?? 0;
    return { ...state, spent: state.spent + cost, lastActionId: action.id };
  }
}
