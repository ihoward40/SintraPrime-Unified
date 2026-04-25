export type GuardIssue = {
  severity?: string; // "ERROR" | "WARN" | "INFO" | ...
  ruleId?: string;
  file?: string;
  line?: number;
  col?: number;
  message?: string;
};

const SEV_RANK: Record<string, number> = {
  ERROR: 3,
  FAIL: 3,
  WARN: 2,
  WARNING: 2,
  INFO: 1,
  NOTICE: 1,
  HINT: 0,
};

function normSev(s?: string) {
  const key = (s ?? "INFO").toUpperCase().trim();
  return SEV_RANK[key] ?? 1;
}

function s(x?: string) {
  return (x ?? "").toString();
}

function n(x?: number) {
  return Number.isFinite(x as number) ? (x as number) : 0;
}

/**
 * Deterministically sort issues (highest severity first), then take max.
 * This prevents non-deterministic receipts/PR comments and “why did it change?” drama.
 */
export function capIssuesDeterministic(issues: GuardIssue[], max = 12): GuardIssue[] {
  return [...issues]
    .sort((a, b) => {
      // Higher severity first
      const sev = normSev(b.severity) - normSev(a.severity);
      if (sev) return sev;

      // Stable tie-breakers
      const rule = s(a.ruleId).localeCompare(s(b.ruleId));
      if (rule) return rule;

      const file = s(a.file).localeCompare(s(b.file));
      if (file) return file;

      const line = n(a.line) - n(b.line);
      if (line) return line;

      const col = n(a.col) - n(b.col);
      if (col) return col;

      const msg = s(a.message).localeCompare(s(b.message));
      if (msg) return msg;

      return 0;
    })
    .slice(0, Math.max(0, max));
}
