import fs from "node:fs";
import path from "node:path";

function parseIntEnv(name: string, fallback: number | null): number | null {
  const raw = typeof process.env[name] === "string" ? process.env[name] : "";
  const trimmed = raw.trim();
  if (!trimmed) return fallback;
  const n = Number.parseInt(trimmed, 10);
  return Number.isFinite(n) ? n : fallback;
}

function utcDayKeyFromIso(nowIso: string) {
  const iso = String(nowIso ?? "").trim();
  return iso.length >= 10 ? iso.slice(0, 10) : "unknown";
}

function readJsonFileOrDefault(filePath: string, fallback: any) {
  try {
    if (!fs.existsSync(filePath)) return fallback;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

function appendJsonl(filePath: string, obj: unknown) {
  const line = JSON.stringify(obj, null, 0) + "\n";
  fs.appendFileSync(filePath, line, "utf8");
}

export type EnforceCliCreditsResultDenied = {
  kind: "CreditDenied";
  code: "CREDITS_DAILY_BUDGET_UNITS_EXCEEDED";
  reason: string;
  budget_units_per_day: number;
  used_units_today: number;
  requested_units: number;
  now_iso: string;
  day_key_utc: string;
};

export function enforceCliCredits(params: {
  now_iso: string;
  threadId: string;
  command: string;
  domain_id: string | null;
}): EnforceCliCreditsResultDenied | null {
  const enabled =
    process.env.CREDITS_MONITOR_ENABLED === "1" || typeof process.env.CREDITS_DAILY_BUDGET_UNITS === "string";
  if (!enabled) return null;

  const now_iso = params.now_iso;
  const day_key_utc = utcDayKeyFromIso(now_iso);

  const requested_units = Math.max(0, parseIntEnv("CREDITS_UNITS_PER_RUN", 1) ?? 1);
  const budget_units_per_day = parseIntEnv("CREDITS_DAILY_BUDGET_UNITS", null);

  const stateDir = process.env.CREDITS_STATE_DIR || path.join("runs", "credits", "state");
  const ledgerDir = process.env.CREDITS_LEDGER_DIR || path.join("runs", "credits");

  fs.mkdirSync(stateDir, { recursive: true });
  fs.mkdirSync(ledgerDir, { recursive: true });

  const stateFile = path.join(stateDir, `units-${day_key_utc}.json`);
  const state = readJsonFileOrDefault(stateFile, { used_units_today: 0 });
  const used_units_today = Number.isFinite(state?.used_units_today) ? state.used_units_today : 0;

  const ledgerFile = path.join(ledgerDir, "ledger.jsonl");

  const baseLedger = {
    ts: now_iso,
    day_key_utc,
    threadId: params.threadId,
    domain_id: params.domain_id,
    command: params.command,
    requested_units,
  };

  if (typeof budget_units_per_day === "number") {
    if (used_units_today + requested_units > budget_units_per_day) {
      const denied: EnforceCliCreditsResultDenied = {
        kind: "CreditDenied",
        code: "CREDITS_DAILY_BUDGET_UNITS_EXCEEDED",
        reason: `Daily credits budget exceeded: used=${used_units_today}, requested=${requested_units}, budget=${budget_units_per_day}`,
        budget_units_per_day,
        used_units_today,
        requested_units,
        now_iso,
        day_key_utc,
      };

      appendJsonl(ledgerFile, {
        ...baseLedger,
        kind: "CreditDenied",
        code: denied.code,
        budget_units_per_day,
        used_units_today,
      });
      return denied;
    }
  }

  // Track usage even if no budget is set (monitoring-only mode).
  const used_after = used_units_today + requested_units;
  fs.writeFileSync(stateFile, JSON.stringify({ used_units_today: used_after }, null, 2) + "\n", "utf8");

  appendJsonl(ledgerFile, {
    ...baseLedger,
    kind: "CreditConsumed",
    used_units_today_before: used_units_today,
    used_units_today_after: used_after,
    budget_units_per_day: typeof budget_units_per_day === "number" ? budget_units_per_day : null,
  });

  return null;
}
