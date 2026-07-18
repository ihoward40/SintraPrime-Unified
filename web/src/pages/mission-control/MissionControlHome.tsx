import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, LockKeyhole, Radio, RefreshCw, ShieldAlert } from 'lucide-react';
import { getMissionControlSummary, MissionControlSummary, MissionMetric } from '../../api/missionControl';

const unavailable: MissionMetric = { value: null, status: 'unavailable' };

function MetricCard({ label, metric, format }: { label: string; metric: MissionMetric; format?: (value: string | number) => string }) {
  const display = metric.value === null ? '—' : format ? format(metric.value) : String(metric.value);
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

export default function MissionControlHome() {
  const [summary, setSummary] = useState<MissionControlSummary | null>(null);
  const [connection, setConnection] = useState<'live' | 'degraded' | 'offline'>('offline');
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const next = await getMissionControlSummary();
      setSummary(next);
      setConnection(next.health === 'healthy' ? 'live' : 'degraded');
      setError('');
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
    active_agents: unavailable, active_runs: unavailable, pending_decisions: unavailable,
    open_incidents: unavailable, daily_spend_usd: unavailable, kill_switch: unavailable,
    evidence_items: unavailable, scheduled_jobs: unavailable,
  };

  return (
    <div className="mc-home">
      <div className="mc-statusbar" role="status" aria-live="polite">
        <div><Radio className={connection} /> Telemetry <strong>{connection}</strong></div>
        <div>Environment <strong>{summary?.environment ?? 'unknown'}</strong></div>
        <div>Updated <strong>{summary ? new Date(summary.telemetry_updated_at).toLocaleTimeString() : 'not connected'}</strong></div>
        <button onClick={refresh} aria-label="Refresh telemetry"><RefreshCw /> Refresh</button>
      </div>
      {error && <div className="mc-warning"><ShieldAlert /> {error}</div>}

      <section className="mc-command-strip" aria-label="Command controls">
        <div>
          <p className="mc-eyebrow">COMMAND AUTHORITY</p>
          <h2>Human control remains active</h2>
          <p>Mutating controls stay locked until their permission-checked APIs and audit receipts are connected.</p>
        </div>
        <div className="mc-command-actions">
          {['Create task', 'Start governed run', 'Assign agent', 'Pause all', 'Emergency stop'].map((command) => (
            <button key={command} disabled title="Governed command API not connected">
              <LockKeyhole /> {command}
            </button>
          ))}
          <a href="/mission-control/operations"><Activity /> Open Operations</a>
        </div>
      </section>

      <section>
        <div className="mc-section-title"><div><p className="mc-eyebrow">VERIFIED READ MODEL</p><h2>Operational posture</h2></div><span>Source: {summary?.telemetry_source ?? 'unavailable'}</span></div>
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

      <section className="mc-systems">
        <div className="mc-section-title"><div><p className="mc-eyebrow">OBSERVATION</p><h2>Subsystem health</h2></div></div>
        {summary ? Object.entries(summary.subsystems).map(([name, state]) => (
          <div className="mc-system-row" key={name}>
            <span className={`mc-health-dot ${state.status}`} />
            <strong>{name.replace('_', ' ')}</strong>
            <span>{state.status}</span>
          </div>
        )) : <div className="mc-empty">Connect the Portal API to inspect subsystem telemetry.</div>}
      </section>
    </div>
  );
}
