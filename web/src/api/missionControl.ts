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

// ── Freshness metadata ─────────────────────────────────────────────────────────

export interface FreshnessMeta {
  generated_at: string;
  source_updated_at: string | null;
  freshness_seconds: number | null;
  state: 'LIVE' | 'DELAYED' | 'STALE' | 'UNKNOWN';
}

// ── Intent projection: detail types ────────────────────────────────────────────

export interface CommandEventProjection {
  id: string;
  sequence: number;
  event_type: string;
  state: string;
  payload: Record<string, unknown>;
  previous_hash: string | null;
  event_hash: string;
  created_at: string | null;
}

export interface CommandReceiptProjection {
  id: string;
  receipt_type: string;
  receipt_hash: string;
  audit_log_id: string | null;
  evidence_refs: unknown[];
  created_at: string | null;
}

export interface CommandProjection {
  id: string;
  tenant_id: string;
  requested_by: string;
  command_type: string;
  target_type: string;
  target_id: string;
  idempotency_key: string;
  request_hash: string;
  state: string;
  reason_code: string | null;
  reason: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  audit_log_id: string | null;
  created_at: string | null;
  completed_at: string | null;
  events: CommandEventProjection[];
  receipts: CommandReceiptProjection[];
  freshness: FreshnessMeta | null;
}

// ── Intent projection: summary type for list responses ─────────────────────────

export interface CommandSummary {
  id: string;
  tenant_id: string;
  requested_by: string;
  command_type: string;
  target_type: string;
  target_id: string;
  idempotency_key: string;
  request_hash: string;
  state: string;
  reason_code: string | null;
  reason: string | null;
  audit_log_id: string | null;
  created_at: string | null;
  completed_at: string | null;
  event_count: number;
  receipt_count: number;
}

export interface CommandListResponse {
  items: CommandSummary[];
  total: number;
  limit: number;
  offset: number;
  freshness: FreshnessMeta | null;
}

// ── Execution-state projection: detail types ──────────────────────────────────

export interface RunControlEventProjection {
  id: string;
  sequence: number;
  event_type: string;
  previous_state: string;
  new_state: string;
  previous_version: number;
  new_version: number;
  principal_id: string | null;
  command_id: string | null;
  reason: string | null;
  payload: Record<string, unknown>;
  workflow_status_observed_at: string | null;
  previous_event_hash: string | null;
  event_hash: string;
  event_schema_version: number;
  created_at: string | null;
}

export interface RunControlProjection {
  id: string;
  tenant_id: string;
  workflow_id: string;
  command_id: string | null;
  state: string;
  workflow_status_snapshot: string;
  workflow_status_observed_at: string | null;
  workflow_source: string | null;
  workflow_version_snapshot: number | null;
  state_version: number;
  projection_schema_version: number;
  pause_reason: string | null;
  requested_by: string | null;
  requested_at: string | null;
  confirmation_ref: string | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  paused_at: string | null;
  failed_at: string | null;
  timed_out_at: string | null;
  superseded_at: string | null;
  incident_id: string | null;
  recovery_ref: string | null;
  terminal_reason_code: string | null;
  last_error: string | null;
  created_at: string | null;
  updated_at: string | null;
  events: RunControlEventProjection[];
  freshness: FreshnessMeta | null;
}

// ── Execution-state projection: summary type for list responses ────────────────

export interface RunControlSummary {
  id: string;
  tenant_id: string;
  workflow_id: string;
  command_id: string | null;
  state: string;
  workflow_status_snapshot: string;
  workflow_status_observed_at: string | null;
  workflow_source: string | null;
  workflow_version_snapshot: number | null;
  state_version: number;
  projection_schema_version: number;
  pause_reason: string | null;
  requested_by: string | null;
  requested_at: string | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  paused_at: string | null;
  failed_at: string | null;
  timed_out_at: string | null;
  superseded_at: string | null;
  incident_id: string | null;
  terminal_reason_code: string | null;
  created_at: string | null;
  updated_at: string | null;
  event_count: number;
}

export interface RunControlListResponse {
  items: RunControlSummary[];
  total: number;
  limit: number;
  offset: number;
  freshness: FreshnessMeta | null;
}

// ── Correlation / causation chain ──────────────────────────────────────────────

export interface CausationLink {
  source_type: 'command_event' | 'run_control_event' | 'receipt';
  source_id: string;
  sequence: number;
  event_type: string;
  state: string;
  hash: string;
  previous_hash: string | null;
  created_at: string | null;
  command_id: string | null;
  run_control_id: string | null;
}

export interface CausationChain {
  command_id: string;
  tenant_id: string;
  command_type: string;
  command_state: string;
  links: CausationLink[];
  truncated: boolean;
  total_links: number;
  warnings: string[];
  freshness: FreshnessMeta | null;
}

// ── Sigma gate status ──────────────────────────────────────────────────────────

export interface SigmaGateStatus {
  gate_id: 'SIGMA_LEASE_EXPIRY_CONTINUATION_GATE';
  state: 'BLOCKED' | 'DEFINED' | 'SATISFIED';
  description: string;
  criteria: string[];
  cancellation_controls: 'DISABLED' | 'ENABLED';
  blocking_phase_3b: boolean;
}

export interface CancellationControlStatus {
  execution_scoped: 'DISABLED' | 'ENABLED';
  tenant_scoped: 'DISABLED' | 'ENABLED';
  platform_break_glass: 'DISABLED' | 'ENABLED';
  gate: SigmaGateStatus;
  reason: string;
}

// ── Source load state ──────────────────────────────────────────────────────────

/**
 * Independent load status for each data source.
 *
 * LOADING   — request in flight, no data yet (or prior data shown as stale)
 * AVAILABLE — request succeeded, data is current
 * STALE     — request failed, prior data retained but labeled stale
 * UNAVAILABLE — request failed, no prior data, source is down
 * ERROR     — request failed with an unexpected error
 */
export type SourceLoadState = 'LOADING' | 'AVAILABLE' | 'STALE' | 'UNAVAILABLE' | 'ERROR';

// ── API helpers ────────────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('sintraprime_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function getJson<T>(path: string): Promise<T> {
  if (!API_BASE) {
    throw new Error('Mission Control API base URL is not configured.');
  }
  const { data } = await axios.get<T>(`${API_BASE}${path}`, {
    headers: authHeaders(),
    timeout: 15_000,
  });
  return data;
}

// ── API functions ──────────────────────────────────────────────────────────────

export async function getMissionControlSummary(): Promise<MissionControlSummary> {
  return getJson<MissionControlSummary>('/api/v1/mission-control/summary');
}

export async function listIntents(params?: {
  state?: string;
  command_type?: string;
  limit?: number;
  offset?: number;
}): Promise<CommandListResponse> {
  const query = new URLSearchParams();
  if (params?.state) query.set('state', params.state);
  if (params?.command_type) query.set('command_type', params.command_type);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  const qs = query.toString();
  return getJson<CommandListResponse>(
    `/api/v1/mission-control/intents${qs ? `?${qs}` : ''}`,
  );
}

export async function getIntent(commandId: string): Promise<CommandProjection> {
  return getJson<CommandProjection>(
    `/api/v1/mission-control/intents/${commandId}`,
  );
}

export async function listRunControls(params?: {
  state?: string;
  workflow_id?: string;
  limit?: number;
  offset?: number;
}): Promise<RunControlListResponse> {
  const query = new URLSearchParams();
  if (params?.state) query.set('state', params.state);
  if (params?.workflow_id) query.set('workflow_id', params.workflow_id);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  const qs = query.toString();
  return getJson<RunControlListResponse>(
    `/api/v1/mission-control/run-controls${qs ? `?${qs}` : ''}`,
  );
}

export async function getRunControl(runControlId: string): Promise<RunControlProjection> {
  return getJson<RunControlProjection>(
    `/api/v1/mission-control/run-controls/${runControlId}`,
  );
}

export async function getCausationChain(commandId: string): Promise<CausationChain> {
  return getJson<CausationChain>(
    `/api/v1/mission-control/intents/${commandId}/causation-chain`,
  );
}

export async function getCancellationStatus(): Promise<CancellationControlStatus> {
  return getJson<CancellationControlStatus>(
    '/api/v1/mission-control/sigma-gate',
  );
}