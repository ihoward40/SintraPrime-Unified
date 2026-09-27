export type GraphicsPreset = 'lite' | 'balanced' | 'cinematic';

export type TownDistrictId =
  | 'citadel' | 'town-hall' | 'constitution' | 'agents'
  | 'evidence' | 'build' | 'finance' | 'creative';

export interface Vec3 { x: number; y: number; z: number }

export interface TownDistrict3D {
  id: TownDistrictId;
  label: string;
  position: Vec3;
  scale: Vec3;
  authority: 'projection' | 'governed' | 'locked';
  activity: number;
}

export interface AgentPresence3D {
  agentId: string;
  displayName: string;
  district: TownDistrictId;
  position: Vec3;
  state: 'idle' | 'working' | 'blocked' | 'awaiting-approval' | 'offline';
  authorityLabel: string;
}

export interface TownHallSession {
  sessionId: string;
  topic: string;
  chair: 'principal';
  participantAgentIds: string[];
  proposalIds: string[];
  approvalIds: string[];
  status: 'scheduled' | 'assembling' | 'in-session' | 'adjourned';
}

export interface SpatialActivity {
  id: string;
  kind: 'mission' | 'evidence' | 'proposal' | 'approval' | 'receipt' | 'incident';
  from: TownDistrictId;
  to: TownDistrictId;
  intensity: number;
  verified: boolean;
}

export interface TownEnvironment {
  timeOfDay: number;
  weather: 'clear' | 'haze' | 'rain';
  volumetrics: boolean;
  trafficDensity: number;
}

export interface TownWorldState {
  preset: GraphicsPreset;
  districts: TownDistrict3D[];
  agents: AgentPresence3D[];
  townHall: TownHallSession | null;
  activity: SpatialActivity[];
  environment: TownEnvironment;
}

export const GRAPHICS_PRESETS: Record<GraphicsPreset, {
  label: string;
  targetFps: number;
  pixelRatioCap: number;
  shadows: boolean;
  volumetrics: boolean;
  reflections: boolean;
  avatarLimit: number;
  trafficLimit: number;
}> = {
  lite: {
    label: 'Lite / legacy GPU',
    targetFps: 30,
    pixelRatioCap: 1,
    shadows: false,
    volumetrics: false,
    reflections: false,
    avatarLimit: 16,
    trafficLimit: 20,
  },
  balanced: {
    label: 'Balanced',
    targetFps: 45,
    pixelRatioCap: 1.5,
    shadows: true,
    volumetrics: false,
    reflections: false,
    avatarLimit: 48,
    trafficLimit: 60,
  },
  cinematic: {
    label: 'Cinematic / RTX-class',
    targetFps: 60,
    pixelRatioCap: 2,
    shadows: true,
    volumetrics: true,
    reflections: true,
    avatarLimit: 128,
    trafficLimit: 180,
  },
};

export const TOWN_DISTRICTS_3D: TownDistrict3D[] = [
  { id: 'citadel', label: 'Command Citadel', position: { x: 0, y: 0, z: -18 }, scale: { x: 12, y: 20, z: 12 }, authority: 'governed', activity: .9 },
  { id: 'town-hall', label: 'Town Hall', position: { x: 0, y: 0, z: 0 }, scale: { x: 15, y: 9, z: 15 }, authority: 'governed', activity: 1 },
  { id: 'constitution', label: 'Constitutional Chamber', position: { x: -24, y: 0, z: -8 }, scale: { x: 11, y: 12, z: 11 }, authority: 'locked', activity: .75 },
  { id: 'agents', label: 'Agent Quarter', position: { x: 24, y: 0, z: -8 }, scale: { x: 14, y: 14, z: 14 }, authority: 'projection', activity: .85 },
  { id: 'evidence', label: 'Evidence Vault', position: { x: -24, y: 0, z: 18 }, scale: { x: 12, y: 8, z: 12 }, authority: 'governed', activity: .65 },
  { id: 'build', label: 'Build Lab', position: { x: 24, y: 0, z: 18 }, scale: { x: 13, y: 9, z: 13 }, authority: 'projection', activity: .7 },
  { id: 'finance', label: 'Financial District', position: { x: -10, y: 0, z: 34 }, scale: { x: 10, y: 11, z: 10 }, authority: 'locked', activity: .45 },
  { id: 'creative', label: 'Creative Studio', position: { x: 10, y: 0, z: 34 }, scale: { x: 10, y: 8, z: 10 }, authority: 'projection', activity: .55 },
];

export function chooseGraphicsPreset(input: {
  hardwareConcurrency?: number;
  deviceMemoryGb?: number;
  renderer?: string;
}): GraphicsPreset {
  const renderer = (input.renderer ?? '').toLowerCase();
  if (renderer.includes('gt 1030') || (input.deviceMemoryGb ?? 8) <= 2) return 'lite';
  if (renderer.includes('rtx') && (input.deviceMemoryGb ?? 0) >= 8) return 'cinematic';
  if ((input.hardwareConcurrency ?? 4) >= 8 && (input.deviceMemoryGb ?? 0) >= 4) return 'balanced';
  return 'lite';
}
