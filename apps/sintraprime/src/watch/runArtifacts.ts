import fs from "node:fs";
import path from "node:path";

function mkdirp(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

export function runRoot(executionId: string) {
  return path.join(process.cwd(), "runs", executionId);
}

export function ensureRunDirs(executionId: string) {
  const root = runRoot(executionId);
  const screenDir = path.join(root, "screen");
  const screenshotsDir = path.join(screenDir, "screenshots");
  const tourDir = path.join(screenDir, "tour");
  const stepsDir = path.join(screenDir, "steps");
  const planDir = path.join(root, "plan");
  const applyDir = path.join(root, "apply");
  mkdirp(screenDir);
  mkdirp(screenshotsDir);
  mkdirp(tourDir);
  mkdirp(stepsDir);
  mkdirp(planDir);
  mkdirp(applyDir);
  return { root, screenDir, screenshotsDir, tourDir, stepsDir, planDir, applyDir };
}

export function appendRunLedgerLine(executionId: string, entry: Record<string, unknown>) {
  const root = runRoot(executionId);
  mkdirp(root);
  const file = path.join(root, "ledger.jsonl");
  fs.appendFileSync(file, JSON.stringify(entry) + "\n", "utf8");
}

export function writePlanSummary(executionId: string, md: string) {
  const { planDir } = ensureRunDirs(executionId);
  const abs = path.join(planDir, "summary.md");
  fs.writeFileSync(abs, md.endsWith("\n") ? md : md + "\n", "utf8");
}

export function writeApplyJson(executionId: string, fileName: string, value: unknown) {
  const { applyDir } = ensureRunDirs(executionId);
  const abs = path.join(applyDir, fileName);
  fs.writeFileSync(abs, JSON.stringify(value, null, 2) + "\n", "utf8");
}
