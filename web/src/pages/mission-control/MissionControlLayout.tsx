import { NavLink, Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import { missionControlSections } from './sections';

export default function MissionControlLayout() {
  return (
    <section className="mc-shell" aria-label="Mission Control">
      <header className="mc-masthead">
        <div>
          <p className="mc-eyebrow">SINTRAPRIME / CONTROL PLANE</p>
          <h1>Mission Control</h1>
          <p>Authorized work. Verifiable outcomes.</p>
        </div>
        <div className="mc-doctrine">
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
