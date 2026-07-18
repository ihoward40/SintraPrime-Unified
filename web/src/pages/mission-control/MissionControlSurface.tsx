import { useParams } from 'react-router-dom';
import { LockKeyhole, Radio } from 'lucide-react';
import { missionControlSections } from './sections';

export default function MissionControlSurface() {
  const { surface = '' } = useParams();
  const label = missionControlSections.find(([path]) => path === surface)?.[1] ?? 'Control Surface';
  return (
    <div className="mc-surface">
      <div>
        <p className="mc-eyebrow">MISSION CONTROL / {label.toUpperCase()}</p>
        <h2>{label}</h2>
        <p>This route is preserved in the unified shell. Its authoritative data adapter is not connected yet.</p>
      </div>
      <div className="mc-empty-state">
        <Radio />
        <h3>No fabricated operational data</h3>
        <p>Mission Control will populate this surface only from typed telemetry, governance, and evidence APIs.</p>
        <span><LockKeyhole /> Commands unavailable until server-side authorization and audit events are active.</span>
      </div>
    </div>
  );
}
