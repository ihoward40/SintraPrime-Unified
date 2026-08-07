import { NavLink, Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import { missionControlSections } from './sections';

export default function MissionControlLayout() {
  return (
    <section className="mc-shell" aria-label="Mission Control">
      <header className="mc-masthead">
        <div>
          <p className="mc-eyebrow">SINTRAPRIME / CONTROL PLANE</p>
          <h1>Principal Command</h1>
          <p>Unified orchestration. Autonomous integrity.</p>
        </div>
        <div className="mc-doctrine">
          <span className="god-mode-tag">GOD MODE ACTIVE</span>
          <span>GOVERNANCE FIRST</span>
          <span>EVIDENCE REQUIRED</span>
        </div>
      </header>
      <nav className="mc-subnav" aria-label="Mission Control sections">
        <NavLink end to="/mission-control" className={({ isActive }) => clsx(isActive && 'active')}>Overview</NavLink>
        {missionControlSections.map(([path, label]) => (
          <NavLink key={path} to={`/mission-control/${path}`} className={({ isActive }) => clsx(isActive && 'active')}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </section>
  );
}
