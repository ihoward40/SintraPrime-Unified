import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Archive, Bot, Building2, CircleDollarSign, Landmark, Radio,
  Scale, Shield, Sparkles, Users, Wrench,
} from 'lucide-react';
import {
  getCancellationStatus,
  getMissionControlSummary,
  getPrincipalBrief,
  MissionControlSummary,
  PrincipalBrief,
  CancellationControlStatus,
} from '../../api/missionControl';
import './MissionControlTown.css';
import { chooseGraphicsPreset, type GraphicsPreset } from './three/townWorld';
import { projectMissionControlToTown } from './three/missionControlTownAdapter';

const Town3DRenderer = lazy(() => import('./three/Town3DRenderer'));

type District = {
  id: string;
  name: string;
  subtitle: string;
  icon: typeof Building2;
  x: number;
  y: number;
  size: 'sm' | 'md' | 'lg' | 'xl';
  state: 'governed' | 'observed' | 'locked';
};

const districts: District[] = [
  { id: 'citadel', name: 'Command Citadel', subtitle: 'Principal command deck', icon: Landmark, x: 50, y: 28, size: 'xl', state: 'governed' },
  { id: 'town-hall', name: 'Town Hall', subtitle: 'Council & agent assembly', icon: Users, x: 50, y: 58, size: 'lg', state: 'governed' },
  { id: 'constitution', name: 'Constitutional Chamber', subtitle: 'Authority & restraint', icon: Scale, x: 23, y: 34, size: 'lg', state: 'locked' },
  { id: 'agents', name: 'Agent Quarter', subtitle: 'Workers & directors', icon: Bot, x: 77, y: 35, size: 'lg', state: 'observed' },
  { id: 'evidence', name: 'Evidence Vault', subtitle: 'Receipts & provenance', icon: Archive, x: 20, y: 70, size: 'md', state: 'governed' },
  { id: 'build', name: 'Build Lab', subtitle: 'Engineering floor', icon: Wrench, x: 80, y: 70, size: 'md', state: 'observed' },
  { id: 'finance', name: 'Financial District', subtitle: 'Cost & treasury observatory', icon: CircleDollarSign, x: 34, y: 84, size: 'sm', state: 'locked' },
  { id: 'creative', name: 'Creative Studio', subtitle: 'Media & design', icon: Sparkles, x: 66, y: 84, size: 'sm', state: 'observed' },
];

type TownMetricKey = 'active_agents' | 'evidence_items';

function metricValue(summary: MissionControlSummary | null, key: TownMetricKey): string | number {
  const value = summary?.[key].value;
  return value ?? '—';
}

export default function MissionControlTown() {
  const [summary, setSummary] = useState<MissionControlSummary | null>(null);
  const [brief, setBrief] = useState<PrincipalBrief | null>(null);
  const [gate, setGate] = useState<CancellationControlStatus | null>(null);
  const [selected, setSelected] = useState('town-hall');
  const [telemetry, setTelemetry] = useState<'loading' | 'live' | 'degraded'>('loading');
  const [show3D, setShow3D] = useState(false);
  const [graphicsPreset, setGraphicsPreset] = useState<GraphicsPreset>('lite');

  useEffect(() => {
    const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
    setGraphicsPreset(chooseGraphicsPreset({
      hardwareConcurrency: navigator.hardwareConcurrency,
      deviceMemoryGb: memory,
      renderer: '',
    }));
  }, []);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      getMissionControlSummary(),
      getPrincipalBrief(),
      getCancellationStatus(),
    ]).then(([summaryResult, briefResult, gateResult]) => {
      if (!mounted) return;
      if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value);
      if (briefResult.status === 'fulfilled') setBrief(briefResult.value);
      if (gateResult.status === 'fulfilled') setGate(gateResult.value);
      setTelemetry(summaryResult.status === 'fulfilled' ? 'live' : 'degraded');
    });
    return () => { mounted = false; };
  }, []);

  const selectedDistrict = useMemo(
    () => districts.find((district) => district.id === selected) ?? districts[0],
    [selected],
  );
  const SelectedIcon = selectedDistrict.icon;
  const world = useMemo(
    () => projectMissionControlToTown(summary, brief, graphicsPreset),
    [summary, brief, graphicsPreset],
  );

  if (show3D) {
    return (
      <Suspense fallback={<div className="mc3d-loading">Preparing governed 3D projection…</div>}>
        <Town3DRenderer world={world} preset={graphicsPreset} onExit={() => setShow3D(false)} />
      </Suspense>
    );
  }

  return (
    <div className="mc-town-shell">
      <section className="mc-town-hero">
        <div>
          <p className="mc-town-kicker">SP-MC3D-001 / OBSERVATION LAYER</p>
          <h2>SintraPrime <span>Command Town</span></h2>
          <p className="mc-town-doctrine">Observability should increase faster than authority.</p>
        </div>
        <div className="mc-town-live">
          <button className="mc-town-enter3d" type="button" onClick={() => setShow3D(true)}>
            ENTER 3D · {graphicsPreset.toUpperCase()}
          </button>
          <Radio className={telemetry} />
          <div><small>TELEMETRY</small><strong>{telemetry.toUpperCase()}</strong></div>
        </div>
      </section>

      <section className="mc-town-hud" aria-label="Town telemetry">
        <div><small>ACTIVE AGENTS</small><strong>{metricValue(summary, 'active_agents')}</strong></div>
        <div><small>ACTIVE MISSIONS</small><strong>{brief?.active_missions?.length ?? '—'}</strong></div>
        <div><small>BLOCKED AGENTS</small><strong>{brief?.blocked_agents?.length ?? '—'}</strong></div>
        <div><small>EVIDENCE ITEMS</small><strong>{metricValue(summary, 'evidence_items')}</strong></div>
        <div><small>AUTHORITY GATE</small><strong>{gate?.gate.state ?? 'UNKNOWN'}</strong></div>
      </section>

      <section className="mc-town-world" aria-label="SintraPrime governed town">
        <div className="mc-town-sky" />
        <div className="mc-town-grid" />
        <div className="mc-town-avenue avenue-a" />
        <div className="mc-town-avenue avenue-b" />
        <div className="mc-town-core-glow" />

        {districts.map((district, index) => {
          const Icon = district.icon;
          return (
            <motion.button
              key={district.id}
              className={`mc-building ${district.size} ${district.state} ${selected === district.id ? 'selected' : ''}`}
              style={{ left: `${district.x}%`, top: `${district.y}%` }}
              initial={{ opacity: 0, y: 18, scale: .94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: index * .055, duration: .45 }}
              onClick={() => setSelected(district.id)}
              aria-pressed={selected === district.id}
            >
              <span className="mc-building-crown"><Icon /></span>
              <span className="mc-building-face">
                <b>{district.name}</b>
                <small>{district.subtitle}</small>
              </span>
              <span className="mc-building-state">{district.state}</span>
            </motion.button>
          );
        })}

        <div className="mc-town-principal">
          <Shield />
          <span>PRINCIPAL</span>
        </div>
      </section>

      <section className="mc-town-inspector">
        <div className="mc-town-inspector-title">
          <SelectedIcon />
          <div>
            <small>SELECTED DISTRICT</small>
            <h3>{selectedDistrict.name}</h3>
            <p>{selectedDistrict.subtitle}</p>
          </div>
        </div>
        <div className="mc-town-inspector-grid">
          <div><small>MODE</small><strong>READ-ONLY PROJECTION</strong></div>
          <div><small>AUTHORITY</small><strong>{selectedDistrict.state.toUpperCase()}</strong></div>
          <div><small>EXECUTION</small><strong>NOT GRANTED BY VIEW</strong></div>
          <div><small>EVIDENCE</small><strong>RECEIPT-ORIENTED</strong></div>
        </div>
        {selectedDistrict.id === 'town-hall' && (
          <div className="mc-townhall-panel">
            <Users />
            <div>
              <strong>Town Hall Assembly</strong>
              <p>
                Designed for Principal-led council sessions. Agent attendance and statements are
                observable here; attendance never grants authority and proposals never become approvals.
              </p>
            </div>
          </div>
        )}
      </section>

      <footer className="mc-town-footer">
        <Activity />
        <span>VISUALIZATION CONSUMES GOVERNED STATE. IT DOES NOT CREATE EXECUTION AUTHORITY.</span>
      </footer>
    </div>
  );
}
