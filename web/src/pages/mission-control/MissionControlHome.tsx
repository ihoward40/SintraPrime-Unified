import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  LockKeyhole,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldX,
} from 'lucide-react';
import {
  getMissionControlSummary,
  getCancellationStatus,
  listIntents,
  listRunControls,
  MissionControlSummary,
  MissionMetric,
  CommandListResponse,
  RunControlListResponse,
  CancellationControlStatus,
} from '../../api/missionControl';

const unavailable: MissionMetric = { value: null, status: 'unavailable' };

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

function SigmaGateBanner({ status }: { status: CancellationControlStatus | null }) {
  if (!status) return null;
  const blocked = status.gate.state === 'BLOCKED';
  return (
    <div className={`mc-sigma-banner ${blocked ? 'blocked' : 'satisfied'}`}>
      <ShieldX />
      <div>
        <strong>{status.gate.gate_id}</strong>
        <span> — {status.gate.state}</span>
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

function IntentList({ intents }: { intents: CommandListResponse | null }) {
  if (!intents || intents.items.length === 0) {
    return (
      <div className="mc-empty">
        No intents recorded. Commands submitted through the governed ingestion layer will appear here.
      </div>
    );
  }
  return (
    <table className="mc-table">
      <thead>
        <tr>
          <th>Type</th>
          <th>State</th>
          <th>Target</th>
          <th>Created</th>
          <th>Events</th>
        </tr>
      </thead>
      <tbody>
        {intents.items.map((cmd) => (
          <tr key={cmd.id}>
            <td>{cmd.command_type}</td>
            <td className={`mc-state ${cmd.state.toLowerCase()}`}>{cmd.state}</td>
            <td>
              {cmd.target_type}:{cmd.target_id}
            </td>
            <td>{cmd.created_at ? new Date(cmd.created_at).toLocaleString() : '—'}</td>
            <td>{cmd.events.length}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RunControlList({ controls }: { controls: RunControlListResponse | null }) {
  if (!controls || controls.items.length === 0) {
    return (
      <div className="mc-empty">
        No run-control projections. Active workflow controls will appear here when the execution
        layer connects.
      </div>
    );
  }
  return (
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
        {controls.items.map((rc) => (
          <tr key={rc.id}>
            <td>{rc.workflow_id}</td>
            <td className={`mc-state ${rc.state.toLowerCase()}`}>{rc.state}</td>
            <td>v{rc.state_version}</td>
            <td>{rc.workflow_status_snapshot}</td>
            <td>{rc.created_at ? new Date(rc.created_at).toLocaleString() : '—'}</td>
            <td>{rc.events.length}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MissionControlHome() {
  const [summary, setSummary] = useState<MissionControlSummary | null>(null);
  const [connection, setConnection] = useState<'live' | 'degraded' | 'offline'>('offline');
  const [error, setError] = useState('');
  const [intents, setIntents] = useState<CommandListResponse | null>(null);
  const [runControls, setRunControls] = useState<RunControlListResponse | null>(null);
  const [cancellationStatus, setCancellationStatus] =
    useState<CancellationControlStatus | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextSummary, nextIntents, nextRunControls, nextCancellation] = await Promise.allSettled([
        getMissionControlSummary(),
        listIntents({ limit: 20 }),
        listRunControls({ limit: 20 }),
        getCancellationStatus(),
      ]);

      if (nextSummary.status === 'fulfilled') {
        setSummary(nextSummary.value);
        setConnection(nextSummary.value.health === 'healthy' ? 'live' : 'degraded');
        setError('');
      } else {
        setConnection('offline');
        setError('Telemetry endpoint is unavailable. No operational values are being inferred.');
      }

      if (nextIntents.status === 'fulfilled') setIntents(nextIntents.value);
      if (nextRunControls.status === 'fulfilled') setRunControls(nextRunControls.value);
      if (nextCancellation.status === 'fulfilled') setCancellationStatus(nextCancellation.value);
    } catch {
      setConnection('offline');
      setError('Telemetry endpoint is unavailable. No operational values are being inferred.');
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

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
      {error && (
        <div className="mc-warning">
          <ShieldAlert /> {error}
        </div>
      )}

      <SigmaGateBanner status={cancellationStatus} />

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
            <p className="mc-eyebrow">INTENT PROJECTION</p>
            <h2>Command ledger</h2>
          </div>
          <span>{intents ? `${intents.total} total` : '—'}</span>
        </div>
        <IntentList intents={intents} />
      </section>

      <section>
        <div className="mc-section-title">
          <div>
            <p className="mc-eyebrow">EXECUTION-STATE PROJECTION</p>
            <h2>Run controls</h2>
          </div>
          <span>{runControls ? `${runControls.total} total` : '—'}</span>
        </div>
        <RunControlList controls={runControls} />
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