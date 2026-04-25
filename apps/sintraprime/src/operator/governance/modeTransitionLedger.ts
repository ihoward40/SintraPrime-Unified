import fs from "node:fs";
import path from "node:path";

function parseCsv(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function nowIsoUtc() {
  return new Date().toISOString();
}

type ModeEnvSnapshot = {
  mode: string;
  active_limbs: string;
  declaration_path: string;
};

function readJsonFileOrNull<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJsonFileAtomic(filePath: string, value: unknown) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2) + "\n", "utf8");
  fs.renameSync(tmp, filePath);
}

function appendLine(filePath: string, line: string) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.appendFileSync(filePath, line.endsWith("\n") ? line : line + "\n", "utf8");
}

function normalizeLimbsCsv(limbsCsv: string | undefined): string {
  const limbs = parseCsv(limbsCsv);
  const uniqueSorted = Array.from(new Set(limbs)).sort((a, b) => a.localeCompare(b));
  return uniqueSorted.join(",");
}

export type ModeTransitionLedgerParams = {
  ledgerPath?: string;
  snapshotPath?: string;
  env?: NodeJS.ProcessEnv;
};

/**
 * Optional, minimal scribe.
 *
 * Enabled only when SINTRAPRIME_MODE_TRANSITION_LEDGER_AUTO=1 and called after validation approval.
 * Writes a single append-only line iff the declared mode/limbs/declaration path changed.
 */
export function maybeAppendModeTransitionLedger(params: ModeTransitionLedgerParams = {}) {
  const env = params.env ?? process.env;
  if (env.SINTRAPRIME_MODE_TRANSITION_LEDGER_AUTO !== "1") return;

  const mode = String(env.SINTRAPRIME_MODE ?? "").trim();
  const declaration_path = String(env.SINTRAPRIME_MODE_DECLARATION_PATH ?? "").trim();
  const active_limbs = normalizeLimbsCsv(env.SINTRAPRIME_ACTIVE_LIMBS);

  // Require a declared posture; otherwise do not write.
  if (!mode || !declaration_path) return;

  const snapshotPath =
    params.snapshotPath ?? path.join("runs", "governance", "_mode_env_snapshot.json");
  const ledgerPath =
    params.ledgerPath ?? path.join("runs", "governance", "mode-transition-ledger.v1.log");

  const prev = readJsonFileOrNull<ModeEnvSnapshot>(snapshotPath);
  const curr: ModeEnvSnapshot = { mode, active_limbs, declaration_path };

  const changed =
    !prev ||
    prev.mode !== curr.mode ||
    prev.active_limbs !== curr.active_limbs ||
    prev.declaration_path !== curr.declaration_path;

  if (!changed) return;

  const fromMode = prev?.mode ? prev.mode : "ANY";
  const toMode = curr.mode;
  const limbs = curr.active_limbs || "none";

  const line = `${nowIsoUtc()} | ${fromMode} → ${toMode} | ${limbs} | AUTH=VALIDATION | STATUS=DECLARED`;

  appendLine(ledgerPath, line);
  writeJsonFileAtomic(snapshotPath, curr);
}

/**
 * Optional: record validation-triggered halt.
 *
 * This is intended to be called when validation denies and we want an append-only marker.
 */
export function appendSilentHaltLedgerLine(params: ModeTransitionLedgerParams = {}) {
  const env = params.env ?? process.env;
  if (env.SINTRAPRIME_MODE_TRANSITION_LEDGER_AUTO !== "1") return;

  const snapshotPath =
    params.snapshotPath ?? path.join("runs", "governance", "_mode_env_snapshot.json");
  const ledgerPath =
    params.ledgerPath ?? path.join("runs", "governance", "mode-transition-ledger.v1.log");

  const prev = readJsonFileOrNull<ModeEnvSnapshot>(snapshotPath);
  const fromMode = prev?.mode ? prev.mode : "ANY";

  const line = `${nowIsoUtc()} | ${fromMode} → SILENT_HALT | none | AUTH=VALIDATION | STATUS=TRIGGERED`;

  appendLine(ledgerPath, line);

  // Persist the halt marker as the last observed state.
  const curr: ModeEnvSnapshot = {
    mode: "SILENT_HALT",
    active_limbs: "",
    declaration_path: String(env.SINTRAPRIME_MODE_DECLARATION_PATH ?? "").trim(),
  };
  writeJsonFileAtomic(snapshotPath, curr);
}
