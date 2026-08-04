import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { LockKeyhole, Radio } from 'lucide-react';
import {
  listIntents,
  listRunControls,
  getCancellationStatus,
  getCausationChain,
  CommandListResponse,
  RunControlListResponse,
  CancellationControlStatus,
  CausationChain,
} from '../../api/missionControl';
import { missionControlSections } from './sections';

type SurfaceData =
  | { kind: 'intents'; data: CommandListResponse }
  | { kind: 'run-controls'; data: RunControlListResponse }
  | { kind: 'cancellation'; data: CancellationControlStatus }
  | { kind: 'causation'; data: CausationChain }
  | { kind: 'empty' }
  | { kind: 'error'; message: string };

function CausationChainView({ chain }: { chain: CausationChain }) {
  return (
    <div className="mc-causation-chain">
      <div className="mc-chain-header">
        <strong>{chain.command_type}</strong>
        <span className={`mc-state ${chain.command_state.toLowerCase()}`}>{chain.command_state}</span>
      </div>
      <ol className="mc-chain-links">
        {chain.links.map((link, i) => (
          <li key={`${link.source_type}-${link.source_id}`} className="mc-chain-link">
            <span className="mc-chain-seq">{i + 1}</span>
            <span className="mc-chain-type">{link.source_type}</span>
            <span className="mc-chain-event">{link.event_type}</span>
            <span className="mc-chain-state">{link.state}</span>
            <span className="mc-chain-hash" title={link.hash}>
              {link.hash.slice(0, 12)}…
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function MissionControlSurface() {
  const { surface = '' } = useParams();
  const [data, setData] = useState<SurfaceData>({ kind: 'empty' });
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      if (surface === 'operations' || surface === 'runs' || surface === 'tasks') {
        const intents = await listIntents({ limit: 50 });
        setData({ kind: 'intents', data: intents });
      } else if (surface === 'agents') {
        const controls = await listRunControls({ limit: 50 });
        setData({ kind: 'run-controls', data: controls });
      } else if (surface === 'governance' || surface === 'incidents') {
        const status = await getCancellationStatus();
        setData({ kind: 'cancellation', data: status });
      } else if (surface === 'activity') {
        const intents = await listIntents({ limit: 50 });
        setData({ kind: 'intents', data: intents });
      } else {
        setData({ kind: 'empty' });
      }
    } catch {
      setData({ kind: 'error', message: 'Failed to load projection data.' });
    } finally {
      setLoading(false);
    }
  }, [surface]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const label =
    missionControlSections.find(([path]) => path === surface)?.[1] ?? 'Control Surface';

  return (
    <div className="mc-surface">
      <div>
        <p className="mc-eyebrow">MISSION CONTROL / {label.toUpperCase()}</p>
        <h2>{label}</h2>
      </div>

      {loading && <div className="mc-loading">Loading projection data…</div>}

      {data.kind === 'empty' && !loading && (
        <div className="mc-empty-state">
          <Radio />
          <h3>No fabricated operational data</h3>
          <p>
            Mission Control will populate this surface only from typed telemetry, governance, and
            evidence APIs.
          </p>
          <span>
            <LockKeyhole /> Commands unavailable until server-side authorization and audit events are
            active.
          </span>
        </div>
      )}

      {data.kind === 'error' && (
        <div className="mc-error-state">
          <Radio />
          <p>{data.message}</p>
        </div>
      )}

      {data.kind === 'intents' && (
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
            {data.data.items.map((cmd) => (
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
      )}

      {data.kind === 'run-controls' && (
        <table className="mc-table">
          <thead>
            <tr>
              <th>Workflow</th>
              <th>State</th>
              <th>Version</th>
              <th>Snapshot</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {data.data.items.map((rc) => (
              <tr key={rc.id}>
                <td>{rc.workflow_id}</td>
                <td className={`mc-state ${rc.state.toLowerCase()}`}>{rc.state}</td>
                <td>v{rc.state_version}</td>
                <td>{rc.workflow_status_snapshot}</td>
                <td>{rc.created_at ? new Date(rc.created_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {data.kind === 'cancellation' && (
        <div className="mc-cancellation-status">
          <div className={`mc-sigma-banner ${data.data.gate.state === 'BLOCKED' ? 'blocked' : 'satisfied'}`}>
            <strong>{data.data.gate.gate_id}</strong>
            <span> — {data.data.gate.state}</span>
            <p>{data.data.reason}</p>
            <div className="mc-cancellation-controls">
              <span className={data.data.execution_scoped === 'DISABLED' ? 'disabled' : 'enabled'}>
                Execution-scoped: {data.data.execution_scoped}
              </span>
              <span className={data.data.tenant_scoped === 'DISABLED' ? 'disabled' : 'enabled'}>
                Tenant-scoped: {data.data.tenant_scoped}
              </span>
              <span
                className={data.data.platform_break_glass === 'DISABLED' ? 'disabled' : 'enabled'}
              >
                Platform break-glass: {data.data.platform_break_glass}
              </span>
            </div>
          </div>
          <div className="mc-sigma-criteria">
            <h4>Sigma criteria (ADR-002 Section 2.5)</h4>
            <ol>
              {data.data.gate.criteria.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}