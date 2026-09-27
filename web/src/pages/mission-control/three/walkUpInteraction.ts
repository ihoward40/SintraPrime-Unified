import type { AgentPresence3D, TownDistrictId } from './townWorld';

export type WalkUpIntent =
  | 'inspect-agent'
  | 'inspect-district'
  | 'request-brief'
  | 'open-evidence'
  | 'propose-townhall-topic';

export interface WalkUpInteraction {
  interactionId: string;
  principalId: string;
  targetAgentId?: string;
  targetDistrict?: TownDistrictId;
  intent: WalkUpIntent;
  requestedAt: string;
}

export interface WalkUpProjection {
  interaction: WalkUpInteraction;
  targetAgent?: AgentPresence3D;
  mode: 'projection-only';
  canExecute: false;
  canApprove: false;
  canGrantAuthority: false;
}

/**
 * Builds a visualization interaction envelope.
 *
 * It intentionally cannot express execution, approval, permission grants,
 * connector grants, hiring, or agent spawning. Mutating work must leave the
 * visualization and enter the governed command/approval layer.
 */
export function createWalkUpProjection(
  interaction: WalkUpInteraction,
  targetAgent?: AgentPresence3D,
): WalkUpProjection {
  return {
    interaction,
    targetAgent,
    mode: 'projection-only',
    canExecute: false,
    canApprove: false,
    canGrantAuthority: false,
  };
}
