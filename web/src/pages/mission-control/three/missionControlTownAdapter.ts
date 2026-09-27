import type { PrincipalBrief, MissionControlSummary } from '../../../api/missionControl';
import {
  GRAPHICS_PRESETS,
  TOWN_DISTRICTS_3D,
  type AgentPresence3D,
  type GraphicsPreset,
  type SpatialActivity,
  type TownWorldState,
} from './townWorld';

function textField(value: unknown, key: string, fallback: string): string {
  if (value && typeof value === 'object' && key in value) {
    const found = (value as Record<string, unknown>)[key];
    if (typeof found === 'string' && found.trim()) return found;
  }
  return fallback;
}

export function projectMissionControlToTown(
  summary: MissionControlSummary | null,
  brief: PrincipalBrief | null,
  preset: GraphicsPreset,
): TownWorldState {
  const agentLimit = GRAPHICS_PRESETS[preset].avatarLimit;
  const sourceAgents = brief?.agents ?? [];
  const agents: AgentPresence3D[] = sourceAgents.slice(0, agentLimit).map((raw, index) => {
    const id = textField(raw, 'agent_id', textField(raw, 'id', `agent-${index + 1}`));
    const stateRaw = textField(raw, 'state', 'idle');
    const state: AgentPresence3D['state'] =
      stateRaw === 'blocked' ? 'blocked'
      : stateRaw === 'awaiting-approval' ? 'awaiting-approval'
      : stateRaw === 'working' || stateRaw === 'running' ? 'working'
      : stateRaw === 'offline' ? 'offline'
      : 'idle';
    return {
      agentId: id,
      displayName: textField(raw, 'display_name', textField(raw, 'name', id)),
      district: state === 'blocked' || state === 'awaiting-approval' ? 'constitution' : 'agents',
      position: { x: (index % 6) * 1.8 - 4.5, y: 0, z: Math.floor(index / 6) * 1.8 },
      state,
      authorityLabel: textField(raw, 'authority', 'governed / unspecified'),
    };
  });

  const activity: SpatialActivity[] = [];
  if (brief?.recent_receipt_ids?.length) {
    activity.push({
      id: 'receipt-flow',
      kind: 'receipt',
      from: 'agents',
      to: 'evidence',
      intensity: Math.min(1, brief.recent_receipt_ids.length / 10),
      verified: true,
    });
  }
  if (brief?.pending_approvals?.length) {
    activity.push({
      id: 'approval-flow',
      kind: 'approval',
      from: 'agents',
      to: 'constitution',
      intensity: Math.min(1, brief.pending_approvals.length / 10),
      verified: true,
    });
  }

  return {
    preset,
    districts: TOWN_DISTRICTS_3D,
    agents,
    townHall: null,
    activity,
    environment: {
      timeOfDay: 20.5,
      weather: 'clear',
      volumetrics: GRAPHICS_PRESETS[preset].volumetrics,
      trafficDensity: Math.min(
        GRAPHICS_PRESETS[preset].trafficLimit,
        Number(summary?.active_runs?.value ?? 0),
      ),
    },
  };
}
