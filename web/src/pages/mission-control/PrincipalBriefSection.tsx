import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ShieldQuestion } from 'lucide-react';
import { getPrincipalBrief, PrincipalBrief as PrincipalBriefData } from '../../api/missionControl';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; brief: PrincipalBriefData };

/**
 * Principal Brief section (SP-GOD0-MISSION-CONTROL-001).
 *
 * Read-only view over sp-principal-brief-v1. Recommendations are displayed
 * as proposals with provenance — this component has no approve action and
 * no way to convert a recommendation into an approval. Approvals flow only
 * through the governed approval service.
 */
export function PrincipalBriefSection() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getPrincipalBrief()
      .then((brief) => {
        if (!cancelled) setState({ kind: 'loaded', brief });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            kind: 'error',
            message: e instanceof Error ? e.message : 'brief unavailable',
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === 'loading') {
    return <div className="mc-brief-loading">Loading Principal Brief…</div>;
  }
  if (state.kind === 'error') {
    return (
      <div className="mc-brief-error" role="alert">
        <AlertTriangle aria-hidden /> Principal Brief unavailable: {state.message}
      </div>
    );
  }

  const { brief } = state;
  if (!brief.available) {
    return (
      <div className="mc-brief-unavailable" role="status">
        <ShieldQuestion aria-hidden /> Principal Brief unavailable:{' '}
        {brief.unavailable_reason ?? 'no admitted runtime state'}
      </div>
    );
  }

  return (
    <div className="mc-brief">
      <section className="mc-brief-card" aria-label="Decisions required">
        <h3>
          <ShieldQuestion aria-hidden /> Principal decisions required
        </h3>
        {brief.recommended_principal_decisions.length === 0 ? (
          <p className="mc-brief-empty">No decisions require your attention.</p>
        ) : (
          <ul>
            {brief.recommended_principal_decisions.map((rec, i) => (
              <li key={i} className="mc-brief-recommendation">
                {JSON.stringify(rec)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mc-brief-card" aria-label="Active missions">
        <h3>
          <CheckCircle2 aria-hidden /> Active missions
        </h3>
        {brief.active_missions.length === 0 ? (
          <p className="mc-brief-empty">No active missions.</p>
        ) : (
          <ul>
            {brief.active_missions.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="mc-brief-card" aria-label="Pending approvals">
        <h3>Pending approvals</h3>
        <p className="mc-brief-empty">
          {brief.pending_approvals.length === 0
            ? 'No approvals pending.'
            : `${brief.pending_approvals.length} pending — use the governed approval flow.`}
        </p>
      </section>

      <section className="mc-brief-card" aria-label="Security events">
        <h3>Security events</h3>
        <p className="mc-brief-empty">
          {brief.security_events.length === 0
            ? 'No security events.'
            : `${brief.security_events.length} recorded.`}
        </p>
      </section>
    </div>
  );
}
