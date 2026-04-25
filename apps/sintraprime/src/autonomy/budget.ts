import fs from 'node:fs';
import path from 'node:path';

function todayKeyUTC() {
  const d = new Date();
  return d.toISOString().slice(0, 10); // YYYY-MM-DD
}

export function enforceMaxRunsPerDay() {
  const dir = process.env.AUTONOMY_STATE_DIR || 'runs/autonomy/state';
  fs.mkdirSync(dir, { recursive: true });

  const key = todayKeyUTC();
  const f = path.join(dir, `runs-${key}.json`);

  const maxRuns = Number(process.env.POLICY_MAX_RUNS_PER_DAY || 50);
  const state = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : { count: 0 };

  if (state.count >= maxRuns) {
    return {
      kind: 'PolicyDenied',
      code: 'BUDGET_MAX_RUNS_PER_DAY_EXCEEDED',
      reason: `Max runs/day reached (${state.count}/${maxRuns})`
    };
  }

  state.count += 1;
  fs.writeFileSync(f, JSON.stringify(state, null, 2));
  return null;
}
