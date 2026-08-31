import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  LockKeyhole,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldX,
  ShieldQuestion,
} from 'lucide-react';
import {
  getMissionControlSummary,
  getCancellationStatus,
  listIntents,
  listRunControls,
  getRealTimeMetrics,
  MissionControlSummary,
  MissionMetric,
  CommandListResponse,
  RunControlListResponse,
  CancellationControlStatus,
  RealTimeMetrics,
  FreshnessMeta,
  SourceLoadState,
} from '../../api/missionControl';

const unavailable: MissionMetric = { value: null, status: 'unavailable' };

// ── Per-source state container ─────────────────────────────────────────────────

interface SourceState<T> {
  status: SourceLoadState;
  data: T | null;
  error: string | null;
  freshness: FreshnessMeta | null;
}

function initialSourceState<T>(): SourceState<T> {
  return { status: 'LOADING', data: null, error: null, freshness: null };
}

// ── Freshness badge ────────────────────────────────────────────────────────────

function FreshnessBadge({ freshness }: { freshness: FreshnessMeta | null }) {
  if (!freshness) return null;
  const cls = freshness.state.toLowerCase();
  const label = freshness.state;
  const seconds =
    freshness.freshness_seconds !== null
      ? `${Math.round(freshness.freshness_seconds)}s`
      : 'n/a';
  return (
    <span className={`mc-freshness ${cls}`} title={`Record age: ${seconds}`}>
      <Clock /> {label} ({seconds})
    </span>
  );
}

// ── Source status banner ───────────────────────────────────────────────────────

function SourceStatusBanner({ status, error }: { status: SourceLoadState; error: string | null }) {
  if (status === 'AVAILABLE' || status === 'LOADING') return null;
  const messages: Record<SourceLoadState, string> = {
    AVAILABLE: '',
    LOADING: '',
    STALE: 'Prior data retained but may be outdated.',
    UNAVAILABLE: 'Source is unavailable. No data displayed.',
    ERROR: error ?? 'An unexpected error occurred while loading this source.',
  };
  return (
    <div className={`mc-source-warning ${status.toLowerCase()}`}>
      <AlertTriangle /> {messages[status]}
    </div>
  );
}

// ── Metric card ────────────────────────────────────────────────────────────────

function MetricCard({
  label,
  metric,
  format,
}: {
  label: string;
  metric: MissionMetric;
  format?: (value: string | number) => string;
}) {
  const display =
    metric.value === null
      ? '—'
      : format
        ? format(metric.value)
        : String(metric.value);
  return (
    <article className="mc-metric">
      <div className="mc-metric-label">{label}</div>
      <div className="mc-metric-value">{display}</div>
      <div className={`mc-source ${metric.status}`}>
        {metric.status === 'verified' ? <CheckCircle2 /> : <AlertTriangle />}
        {metric.status}
      </div>
    </article>
  );
}

// ── Sigma gate banner ──────────────────────────────────────────────────────────

function SigmaGateBanner({
  status,
  loadState,
}: {
  status: CancellationControlStatus | null;
  loadState: SourceLoadState;
}) {
  // If the Sigma-gate request itself failed, show STATUS UNKNOWN — never hide the banner.
  if (loadState === 'UNAVAILABLE' || loadState === 'ERROR') {
    return (
      <div className="mc-sigma-banner unknown">
        <ShieldQuestion />
        <div>
          <strong>SIGMA_LEASE_EXPIRY_CONTINUATION_GATE</strong>
          <span> — STATUS UNKNOWN</span>
          <p>
            Sigma-gate retrieval failed. Controls remain BLOCKED. Do not assume the
            gate is satisfied.
          </p>
          <div className="mc-cancellation-controls">
            <span className="disabled">Execution-scoped: DISABLED</span>
            <span className="disabled">Tenant-scoped: DISABLED</span>
            <span className="disabled">Platform break-glass: DISABLED</span>
          </div>
        </div>
      </div>
    );
  }

  // STALE: show the last-known state but warn it may be outdated.
  const staleWarning = loadState === 'STALE';

  if (!status) return null;
  const blocked = status.gate.state === 'BLOCKED';
  return (
    <div className={`mc-sigma-banner ${blocked ? 'blocked' : 'satisfied'}${staleWarning ? ' stale' : ''}`}>
      <ShieldX />
      <div>
        <strong>{status.gate.gate_id}</strong>
        <span> — {status.gate.state}{staleWarning ? ' (STALE READ)' : ''}</span>
        <p>{status.reason}</p>
        <div className="mc-cancellation-controls">
          <span className={status.execution_scoped === 'DISABLED' ? 'disabled' : 'enabled'}>
            Execution-scoped: {status.execution_scoped}
          </span>
          <span className={status.tenant_scoped === 'DISABLED' ? 'disabled' : 'enabled'}>
            Tenant-scoped: {status.tenant_scoped}
          </span>
          <span className={status.platform_break_glass === 'DISABLED' ? 'disabled' : 'enabled'}>
            Platform break-glass: {status.platform_break_glass}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Intent list ────────────────────────────────────────────────────────────────

function IntentList({
  state,
}: {
  state: SourceState<CommandListResponse>;
}) {
  const { status, data, error } = state;

  if (status === 'LOADING' && !data) {
  return (
      <div className="mc-loading-source">Loading intent projections…</div>
    );
  }

  if ((status === 'UNAVAILABLE' || status === 'ERROR') && !data) {
    return (
      <div className="mc-source-unavailable">
        <AlertTriangle />
        Intent projection source is unavailable.
        {error ? ` ${error}` : ''}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    // Only show "No intents recorded" when the source is AVAILABLE and returned an empty list.
    if (status === 'AVAILABLE') {
      return (
        <div className="mc-empty">
          No intents recorded. Commands submitted through the governed ingestion layer will appear here.
        </div>
      );
    }
    // STALE with no data — don't claim empty
    return (
      <div className="mc-source-stale">
        <AlertTriangle />
        Intent data is stale and no prior data is available.
      </div>
    );
  }

  return (
    <>
      {status === 'STALE' && (
        <div className="mc-source-warning stale">
          <AlertTriangle /> Showing prior intent data — source refresh failed.
        </div>
      )}
      <table className="mc-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>State</th>
            <th>Target</th>
            <th>Created</th>
            <th>Events</th>
            <th>Receipts</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((cmd) => (
            <tr key={cmd.id}>
              <td>{cmd.command_type}</td>
              <td className={`mc-state ${cmd.state.toLowerCase()}`}>{cmd.state}</td>
              <td>
                {cmd.target_type}:{cmd.target_id}
              </td>
              <td>{cmd.created_at ? new Date(cmd.created_at).toLocaleString() : '—'}</td>
              <td>{cmd.event_count}</td>
              <td>{cmd.receipt_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ── Run control list ───────────────────────────────────────────────────────────

function RunControlListSection({
  state,
}: {
  state: SourceState<RunControlListResponse>;
}) {
  const { status, data, error } = state;

  if (status === 'LOADING' && !data) {
    return (
      <div className="mc-loading-source">Loading run-control projections…</div>
    );
  }

  if ((status === 'UNAVAILABLE' || status === 'ERROR') && !data) {
    return (
      <div className="mc-source-unavailable">
        <AlertTriangle />
        Run-control projection source is unavailable.
        {error ? ` ${error}` : ''}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    if (status === 'AVAILABLE') {
      return (
        <div className="mc-empty">
          No run-control projections. Active workflow controls will appear here when the execution
          layer connects.
        </div>
      );
    }
    return (
      <div className="mc-source-stale">
        <AlertTriangle />
        Run-control data is stale and no prior data is available.
      </div>
    );
  }

  return (
    <>
      {status === 'STALE' && (
        <div className="mc-source-warning stale">
          <AlertTriangle /> Showing prior run-control data — source refresh failed.
        </div>
      )}
      <table className="mc-table">
        <thead>
          <tr>
            <th>Workflow</th>
            <th>State</th>
            <th>Version</th>
            <th>Snapshot</th>
            <th>Created</th>
            <th>Events</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((rc) => (
            <tr key={rc.id}>
              <td>{rc.workflow_id}</td>
              <td className={`mc-state ${rc.state.toLowerCase()}`}>{rc.state}</td>
              <td>v{rc.state_version}</td>
              <td>{rc.workflow_status_snapshot}</td>
              <td>{rc.created_at ? new Date(rc.created_at).toLocaleString() : '—'}</td>
              <td>{rc.event_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function MissionControlHome() {
  const [summaryState, setSummaryState] = useState<SourceState<MissionControlSummary>>(
    initialSourceState(),
  );
  const [intentsState, setIntentsState] = useState<SourceState<CommandListResponse>>(
    initialSourceState(),
  );
  const [runControlsState, setRunControlsState] = useState<SourceState<RunControlListResponse>>(
    initialSourceState(),
  );
  const [sigmaState, setSigmaState] = useState<SourceState<CancellationControlStatus>>(
    initialSourceState(),
  );
  const [realTimeMetricsState, setRealTimeMetricsState] = useState<SourceState<RealTimeMetrics>>(
    initialSourceState(),
  );

  const refresh = useCallback(async () => {
    // Fire all requests in parallel; each source gets independent error handling.
    // We use Promise.allSettled so one failure does not mask others.

    // Summary
    setSummaryState((prev) => ({
      status: 'LOADING',
      data: prev.data,
      error: null,
      freshness: prev.freshness,
    }));
    getMissionControlSummary()
      .then((data) => {
        setSummaryState({ status: 'AVAILABLE', data, error: null, freshness: null });
      })
      .catch((err: unknown) => {
        setSummaryState((prev) => ({
          status: prev.data ? 'STALE' : 'UNAVAILABLE',
          data: prev.data,
          error: err instanceof Error ? err.message : 'Summary request failed',
          freshness: prev.freshness,
        }));
      });

    // Intents
    setIntentsState((prev) => ({
      status: 'LOADING',
      data: prev.data,
      error: null,
      freshness: prev.freshness,
    }));
    listIntents({ limit: 20 })
      .then((data) => {
        setIntentsState({
          status: 'AVAILABLE',
          data,
          error: null,
          freshness: data.freshness ?? null,
        });
      })
      .catch((err: unknown) => {
        setIntentsState((prev) => ({
          status: prev.data ? 'STALE' : 'UNAVAILABLE',
          data: prev.data,
          error: err instanceof Error ? err.message : 'Intent request failed',
          freshness: prev.freshness,
        }));
      });

    // Run controls
    setRunControlsState((prev) => ({
      status: 'LOADING',
      data: prev.data,
      error: null,
      freshness: prev.freshness,
    }));
    listRunControls({ limit: 20 })
      .then((data) => {
        setRunControlsState({
          status: 'AVAILABLE',
          data,
          error: null,
          freshness: data.freshness ?? null,
        });
      })
      .catch((err: unknown) => {
        setRunControlsState((prev) => ({
          status: prev.data ? 'STALE' : 'UNAVAILABLE',
          data: prev.data,
          error: err instanceof Error ? err.message : 'Run-control request failed',
          freshness: prev.freshness,
        }));
      });

    // Sigma gate
    setSigmaState((prev) => ({
      status: 'LOADING',
      data: prev.data,
      error: null,
      freshness: prev.freshness,
    }));
    getCancellationStatus()
      .then((data) => {
        setSigmaState({ status: 'AVAILABLE', data, error: null, freshness: null });
      })
      .catch((err: unknown) => {
        setSigmaState((prev) => ({
          status: prev.data ? 'STALE' : 'UNAVAILABLE',
          data: prev.data,
          error: err instanceof Error ? err.message : 'Sigma-gate request failed',
          freshness: prev.freshness,
        }));
      });

    // Real-time metrics
    setRealTimeMetricsState((prev) => ({
      status: 'LOADING',
      data: prev.data,
      error: null,
      freshness: prev.freshness,
    }));
    getRealTimeMetrics()
      .then((data) => {
        setRealTimeMetricsState({ status: 'AVAILABLE', data, error: null, freshness: null });
      })
      .catch((err: unknown) => {
        setRealTimeMetricsState((prev) => ({
          status: prev.data ? 'STALE' : 'UNAVAILABLE',
          data: prev.data,
          error: err instanceof Error ? err.message : 'Real-time metrics request failed',
          freshness: prev.freshness,
        }));
      });
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const summary = summaryState.data;
  const connection =
    summaryState.status === 'AVAILABLE'
      ? summary?.health === 'healthy'
        ? 'live'
        : 'degraded'
      : summaryState.status === 'STALE'
        ? 'degraded'
        : 'offline';

  const metrics = summary ?? {
    active_agents: unavailable,
    active_runs: unavailable,
    pending_decisions: unavailable,
    open_incidents: unavailable,
    daily_spend_usd: unavailable,
    kill_switch: unavailable,
    evidence_items: unavailable,
    scheduled_jobs: unavailable,
  };

  return (
    <div className="mc-home">
      <div className="mc-statusbar" role="status" aria-live="polite">
        <div>
          <Radio className={connection} /> Telemetry <strong>{connection}</strong>
        </div>
        <div>
          Environment <strong>{summary?.environment ?? 'unknown'}</strong>
        </div>
        <div>
          Updated{' '}
          <strong>
            {summary ? new Date(summary.telemetry_updated_at).toLocaleTimeString() : 'not connected'}
          </strong>
        </div>
        <button onClick={refresh} aria-label="Refresh telemetry">
          <RefreshCw /> Refresh
        </button>
      </div>
      {summaryState.status === 'UNAVAILABLE' && (
        <div className="mc-warning">
          <ShieldAlert /> Telemetry endpoint is unavailable. No operational values are being inferred.
        </div>
      )}
      {summaryState.status === 'STALE' && (
        <div className="mc-warning">
          <ShieldAlert /> Telemetry refresh failed. Showing prior data — values may be outdated.
        </div>
      )}

      <SigmaGateBanner status={sigmaState.data} loadState={sigmaState.status} />
      {sigmaState.status === 'STALE' && (
        <div className="mc-source-warning stale">
          <AlertTriangle /> Sigma-gate data is stale — prior status shown but may be outdated.
        </div>
      )}

      <section className="mc-command-strip" aria-label="Command controls">
        <div>
          <p className="mc-eyebrow">COMMAND AUTHORITY</p>
          <h2>Human control remains active</h2>
          <p>
            Mutating controls stay locked until their permission-checked APIs and audit receipts are
            connected.
          </p>
        </div>
        <div className="mc-command-actions">
          {['Create task', 'Start governed run', 'Assign agent', 'Pause all', 'Emergency stop'].map(
            (command) => (
              <button key={command} disabled title="Governed command API not connected">
                <LockKeyhole /> {command}
              </button>
            ),
          )}
          <a href="/mission-control/operations">
            <Activity /> Open Operations
          </a>
        </div>
      </section>

      <section>
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">VERIFIED READ MODEL</p>
            <h2>Operational posture</h2>
          </div>
          <span>Source: {summary?.telemetry_source ?? 'unavailable'}</span>
        </div>
        <div className="mc-metrics">
          <MetricCard label="Active agents" metric={metrics.active_agents} />
          <MetricCard label="Active runs" metric={metrics.active_runs} />
          <MetricCard label="Pending decisions" metric={metrics.pending_decisions} />
          <MetricCard label="Open incidents" metric={metrics.open_incidents} />
          <MetricCard label="Evidence items" metric={metrics.evidence_items} />
          <MetricCard label="Scheduled jobs" metric={metrics.scheduled_jobs} />
          <MetricCard label="Daily spend" metric={metrics.daily_spend_usd} format={(v) => `$${v}`} />
          <MetricCard label="Kill switch" metric={metrics.kill_switch} />
        </div>
      </section>

      <section>
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">PHASE 3C: COMMAND AUTHORITY</p>
            <h2>Agent Parliament & Cancellation Bus</h2>
          </div>
          <span>
            {realTimeMetricsState.status === 'AVAILABLE' ? 'Live telemetry' : 'Connecting...'}
          </span>
        </div>
        <SourceStatusBanner status={realTimeMetricsState.status} error={realTimeMetricsState.error} />
        
        {realTimeMetricsState.data && (
          <div className="mc-metrics parliament-metrics">
            <article className="mc-metric">
              <div className="mc-metric-label">Parliament Instances</div>
              <div className="mc-metric-value">{realTimeMetricsState.data.parliament.total_instances}</div>
              <div className="mc-parliament-types">
                {Object.entries(realTimeMetricsState.data.parliament.agent_types).map(([type, count]) => (
                  <span key={type}>{type}: {count}</span>
                ))}
              </div>
            </article>
            
            <article className="mc-metric">
              <div className="mc-metric-label">System Load</div>
              <div className="mc-metric-value">
                {(realTimeMetricsState.data.parliament.system_load * 100).toFixed(1)}%
              </div>
              <div className="mc-load-bar">
                <div 
                  className="mc-load-fill" 
                  style={{ width: `${realTimeMetricsState.data.parliament.system_load * 100}%` }}
                />
              </div>
            </article>

            <article className="mc-metric">
              <div className="mc-metric-label">Active Cancellations</div>
              <div className="mc-metric-value">{realTimeMetricsState.data.cancellation_bus.active_signals}</div>
              <div className="mc-source verified">
                <CheckCircle2 /> Priority Bus
              </div>
            </article>

            <article className="mc-metric">
              <div className="mc-metric-label">Queued Signals</div>
              <div className="mc-metric-value">{realTimeMetricsState.data.cancellation_bus.queued_signals}</div>
              <div className="mc-source verified">
                <Activity /> Real-time
              </div>
            </article>
          </div>
        )}
      </section>

      <section>
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">INTENT PROJECTION</p>
            <h2>Command ledger</h2>
          </div>
          <span>
            {intentsState.data ? `${intentsState.data.total} total` : '—'}
            {intentsState.freshness && <FreshnessBadge freshness={intentsState.freshness} />}
          </span>
        </div>
        <SourceStatusBanner status={intentsState.status} error={intentsState.error} />
        <IntentList state={intentsState} />
      </section>

      <section>
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">EXECUTION-STATE PROJECTION</p>
            <h2>Run controls</h2>
          </div>
          <span>
            {runControlsState.data ? `${runControlsState.data.total} total` : '—'}
            {runControlsState.freshness && <FreshnessBadge freshness={runControlsState.freshness} />}
          </span>
        </div>
        <SourceStatusBanner status={runControlsState.status} error={runControlsState.error} />
        <RunControlListSection state={runControlsState} />
      </section>

      <section className="mc-systems">
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">OBSERVATION</p>
            <h2>Subsystem health</h2>
          </div>
        </div>
        {summary
          ? Object.entries(summary.subsystems).map(([name, state]) => (
              <div className="mc-system-row" key={name}>
                <span className={`mc-health-dot ${state.status}`} />
                <strong>{name.replace('_', ' ')}</strong>
                <span>{state.status}</span>
              </div>
            ))
          : 'Connect the Portal API to inspect subsystem telemetry.'}
      </section>
    </div>
  );
}