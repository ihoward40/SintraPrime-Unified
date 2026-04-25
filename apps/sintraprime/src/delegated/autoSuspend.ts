import fs from "node:fs";
import path from "node:path";

import { evaluateDelegationForCommandPatternOnly } from "./delegationEngine.js";
import { writeDelegatedSuspension, getDelegationStatus } from "./delegatedApprovalStore.js";
import { patternMatchesCommand } from "./patternMatch.js";

function readJsonSafe(p: string): any | null {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

function listConfidenceChecks(): Array<{ file: string; data: any }> {
  const dir = path.join(process.cwd(), "runs", "confidence-checks");
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  const out: Array<{ file: string; data: any }> = [];
  for (const f of files) {
    const full = path.join(dir, f);
    const data = readJsonSafe(full);
    if (data && typeof data === "object") out.push({ file: f, data });
  }
  return out;
}

function confidenceRegressionEvidence(pattern: string) {
  const checks = listConfidenceChecks();
  for (const item of checks) {
    const d = item.data;
    const reg = d?.regression;
    const regressed = Boolean(reg?.regressed);
    const acknowledged = Boolean(reg?.acknowledged);
    if (!regressed || acknowledged) continue;

    const cmd =
      typeof d?.command === "string"
        ? String(d.command)
        : typeof d?.baseline?.command === "string"
          ? String(d.baseline.command)
          : "";
    if (!cmd) continue;
    if (!patternMatchesCommand(pattern, cmd)) continue;

    return {
      kind: "CONFIDENCE_REGRESSION" as const,
      details: {
        evidence_file: item.file,
        command: cmd,
        regression: reg,
      },
    };
  }
  return null;
}

export function autoSuspendDelegationsForCommand(command: string) {
  const matches = evaluateDelegationForCommandPatternOnly({ command });
  if (!matches.length) return [] as Array<{ class_id: string; suspended: boolean; reason: string }>;

  const out: Array<{ class_id: string; suspended: boolean; reason: string }> = [];

  for (const m of matches) {
    const status = getDelegationStatus(m.class_id);
    if (status.reason === "SUSPENDED") {
      out.push({ class_id: m.class_id, suspended: true, reason: status.suspension?.reason ?? "SUSPENDED" });
      continue;
    }

    const regression = confidenceRegressionEvidence(m.pattern);
    if (regression) {
      writeDelegatedSuspension({
        class_id: m.class_id,
        suspended_at: new Date().toISOString(),
        reason: regression.kind,
        details: regression.details,
      });
      out.push({ class_id: m.class_id, suspended: true, reason: regression.kind });
      continue;
    }

    out.push({ class_id: m.class_id, suspended: false, reason: "NONE" });
  }

  return out;
}
