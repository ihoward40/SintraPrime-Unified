import fs from "node:fs";
import path from "node:path";

import { computePromotionFingerprint } from "./promotionFingerprint.js";
import { hasPromotion, isDemoted } from "./promotionStore.js";

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function avg(nums: number[]) {
  if (!nums.length) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function parseIsoMs(s: unknown): number | null {
  if (typeof s !== "string") return null;
  const d = new Date(s);
  const t = d.getTime();
  return Number.isFinite(t) ? t : null;
}

// Minimal deterministic plan builder to extract capability_set + adapter_type.
function planMetaForCommand(command: string): { capability_set: string[]; adapter_type: string } | null {
  const trimmed = String(command ?? "").trim();

  const mDb = trimmed.match(/^\/notion\s+(?:db|database)\s+(\S+)\s*$/i);
  if (mDb) {
    return { capability_set: ["notion.read.database"], adapter_type: "NotionAdapter" };
  }

  const mSet = trimmed.match(/^\/notion\s+set\s+(\S+)\s+([^=\s]+)=(.+)$/i);
  if (mSet) {
    return { capability_set: ["notion.write.page_property"], adapter_type: "NotionAdapter" };
  }

  const mt = trimmed.match(/^\/template\s+run\s+(\S+)\s+([\s\S]+)$/i);
  if (mt) {
    const name = mt[1]!;
    const regPath = path.join(process.cwd(), "templates", "registry.json");
    if (!fs.existsSync(regPath)) return null;
    try {
      const registry = JSON.parse(fs.readFileSync(regPath, "utf8"));
      const tpl = registry?.templates?.[name]?.plan;
      const required = Array.isArray(tpl?.required_capabilities)
        ? tpl.required_capabilities.filter((c: any) => typeof c === "string")
        : [];
      // Adapter type: best-effort from first step.
      const steps = Array.isArray(tpl?.steps)
        ? tpl.steps
        : Array.isArray(tpl?.phases)
          ? tpl.phases.flatMap((p: any) => (Array.isArray(p?.steps) ? p.steps : []))
          : [];
      const adapter = steps.length && typeof steps[0]?.adapter === "string" ? String(steps[0].adapter) : "WebhookAdapter";
      return { capability_set: required, adapter_type: adapter };
    } catch {
      return null;
    }
  }

  return null;
}

function listConfidenceChecks(): any[] {
  const dir = path.join(process.cwd(), "runs", "confidence-checks");
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  const items: any[] = [];
  for (const f of files) {
    try {
      const json = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
      items.push(json);
    } catch {
      // ignore
    }
  }
  return items;
}

export type PromotionCandidate = {
  fingerprint: string;
  command: string;
  confidence_avg: number;
  runs_observed: number;
  regressions: number;
  eligible: boolean;
  state: "NOT_ELIGIBLE" | "ELIGIBLE" | "PROMOTED" | "DEMOTED";
};

export function recommendPromotions(params?: {
  windowRuns?: number;
  minAvgScore?: number;
  minAgeDays?: number;
}) {
  const windowRuns = params?.windowRuns ?? Number(process.env.AUTONOMY_PROMOTION_WINDOW ?? 20);
  const minAvgScore = params?.minAvgScore ?? Number(process.env.AUTONOMY_PROMOTION_MIN_AVG_SCORE ?? 85);
  const minAgeDays = params?.minAgeDays ?? Number(process.env.AUTONOMY_PROMOTION_MIN_AGE_DAYS ?? 7);

  const checks = listConfidenceChecks().filter((c) => isRecord(c) && c.kind === "ConfidenceRegressionCheck");

  // Group by command string (normalized by trimming) to keep determinism.
  const byCmd = new Map<string, any[]>();
  for (const c of checks) {
    const cmd = typeof (c as any).command === "string" ? String((c as any).command).trim() : "";
    if (!cmd) continue;
    const arr = byCmd.get(cmd) ?? [];
    arr.push(c);
    byCmd.set(cmd, arr);
  }

  const nowMs = Date.now();
  const minAgeMs = minAgeDays * 24 * 60 * 60 * 1000;

  const candidates: PromotionCandidate[] = [];

  for (const [command, items] of Array.from(byCmd.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
    // Sort by evaluated_at ascending to allow stable "last N" window.
    items.sort((a, b) => {
      const ta = parseIsoMs((a as any).evaluated_at) ?? 0;
      const tb = parseIsoMs((b as any).evaluated_at) ?? 0;
      if (ta !== tb) return ta - tb;
      return String((a as any).execution_id ?? "").localeCompare(String((b as any).execution_id ?? ""));
    });

    const window = items.slice(-windowRuns);
    const meta = planMetaForCommand(command);
    if (!meta) {
      candidates.push({
        fingerprint: "",
        command,
        confidence_avg: 0,
        runs_observed: window.length,
        regressions: 0,
        eligible: false,
        state: "NOT_ELIGIBLE",
      });
      continue;
    }

    const fingerprint = computePromotionFingerprint({
      command,
      capability_set: meta.capability_set,
      adapter_type: meta.adapter_type,
    });

    const scores: number[] = [];
    let regressions = 0;
    let allAllowed = true;
    let oldestMs: number | null = null;

    for (const w of window) {
      const cur = (w as any).current;
      const score = typeof cur?.score === "number" ? cur.score : null;
      if (typeof score === "number") scores.push(score);

      const regressed = Boolean((w as any)?.regression?.regressed);
      if (regressed) regressions += 1;

      const allowed = Boolean((w as any)?.policy_state_allowed);
      if (!allowed) allAllowed = false;

      const t = parseIsoMs((w as any).evaluated_at);
      if (t !== null) {
        oldestMs = oldestMs === null ? t : Math.min(oldestMs, t);
      }
    }

    const confidence_avg = Math.round(avg(scores));
    const hasWindow = window.length >= windowRuns;
    const oldEnough = oldestMs !== null ? nowMs - oldestMs >= minAgeMs : false;

    const promoted = hasPromotion(fingerprint);
    const demoted = isDemoted(fingerprint);

    const eligible =
      !promoted &&
      !demoted &&
      hasWindow &&
      oldEnough &&
      allAllowed &&
      regressions === 0 &&
      confidence_avg >= minAvgScore;

    const state: PromotionCandidate["state"] = demoted
      ? "DEMOTED"
      : promoted
        ? "PROMOTED"
        : eligible
          ? "ELIGIBLE"
          : "NOT_ELIGIBLE";

    candidates.push({
      fingerprint,
      command,
      confidence_avg,
      runs_observed: window.length,
      regressions,
      eligible,
      state,
    });
  }

  // Keep only candidates with a fingerprint (i.e., supported commands)
  const filtered = candidates.filter((c) => c.fingerprint);

  // Deterministic ordering: eligible first, higher avg, then command.
  filtered.sort((a, b) => {
    if (a.eligible !== b.eligible) return a.eligible ? -1 : 1;
    if (b.confidence_avg !== a.confidence_avg) return b.confidence_avg - a.confidence_avg;
    return a.command.localeCompare(b.command);
  });

  return {
    kind: "PromotionCandidates",
    window_runs: windowRuns,
    min_avg_score: minAvgScore,
    min_age_days: minAgeDays,
    candidates: filtered,
  };
}
