import type { AuthorityDecision, MissionSpec, ProposedAction } from './types.js';

export class AuthorityEngine {
  evaluate(spec: MissionSpec, action: ProposedAction): AuthorityDecision {
    if (!spec.allowedModels.includes(action.modelId)) {
      return { decision: 'block', reason: `Model not authorized: ${action.modelId}` };
    }

    if (!spec.allowedTools.includes(action.tool)) {
      return { decision: 'block', reason: `Tool not authorized: ${action.tool}` };
    }

    const level = spec.authority.byActionClass[action.actionClass];

    if (level === 'prohibited') {
      return {
        decision: 'block',
        reason: `Action class prohibited by mission constitution: ${action.actionClass}`,
        requiredLevel: level,
      };
    }

    if (action.actionClass === 'financial') {
      const cost = action.estimatedCost ?? 0;
      if (cost > spec.budget.totalCap) {
        return { decision: 'block', reason: `Requested spend ${cost} exceeds mission budget cap ${spec.budget.totalCap}` };
      }
      if (cost > spec.budget.autonomousTransactionCap) {
        return {
          decision: 'require_approval',
          reason: `Spend ${cost} exceeds autonomous transaction cap ${spec.budget.autonomousTransactionCap}`,
          requiredLevel: 'principal',
        };
      }
    }

    if (level === 'principal' || level === 'supervisor') {
      return {
        decision: 'require_approval',
        reason: `${action.actionClass} requires ${level} approval`,
        requiredLevel: level,
      };
    }

    return { decision: 'allow', reason: 'Action is within delegated mission authority', requiredLevel: level };
  }
}
