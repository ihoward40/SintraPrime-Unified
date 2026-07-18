import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL;

export type EvidenceStatus = 'verified' | 'unknown' | 'unavailable';

export interface MissionMetric {
  value: string | number | null;
  status: EvidenceStatus;
}

export interface MissionControlSummary {
  environment: string;
  health: 'healthy' | 'degraded' | 'offline';
  telemetry_updated_at: string;
  telemetry_source: string;
  active_agents: MissionMetric;
  active_runs: MissionMetric;
  pending_decisions: MissionMetric;
  open_incidents: MissionMetric;
  daily_spend_usd: MissionMetric;
  kill_switch: MissionMetric;
  evidence_items: MissionMetric;
  scheduled_jobs: MissionMetric;
  subsystems: Record<string, { status: string; [key: string]: unknown }>;
}

export async function getMissionControlSummary(): Promise<MissionControlSummary> {
  if (!API_BASE) {
    throw new Error('Mission Control API base URL is not configured.');
  }

  const token = localStorage.getItem('sintraprime_token');
  const { data } = await axios.get<MissionControlSummary>(
    `${API_BASE}/api/v1/mission-control/summary`,
    { headers: token ? { Authorization: `Bearer ${token}` } : undefined, timeout: 15_000 },
  );
  return data;
}