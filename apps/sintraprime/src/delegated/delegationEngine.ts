import fs from "node:fs";
import path from "node:path";

import type { ExecutionPlan } from "../schemas/ExecutionPlan.schema.js";
import { normalizeCommand as normalizeDslCommand } from "../dsl/normalizeCommand.js";
import { isDemoted, readPromotion, promotionsDir } from "../autonomy/promotionStore.js";

import type { DelegationDecision, DelegatedApprovalScope, DelegatedClassDefinition } from "./delegatedTypes.js";
import { listLatestDelegatedClasses, readLatestDelegatedClassDefinition } from "./delegatedClassStore.js";
import { getDelegationStatus } from "./delegatedApprovalStore.js";
import { patternMatchesCommand } from "./patternMatch.js";

function normalizeCaps(caps: string[]): string[] {
  const uniq = new Set<string>();
  for (const c of caps ?? []) {
    const v = String(c ?? "").trim();
    if (v) uniq.add(v);
  }
  return Array.from(uniq).sort((a, b) => a.localeCompare(b));
}

function planMeta(plan: ExecutionPlan): {
  capability_set: string[];
  adapter_type: string;
  write: boolean;
} {
  const requiredCaps = Array.isArray((plan as any).required_capabilities)
    ? (plan as any).required_capabilities.filter((c: any) => typeof c === "string")
    : [];
  const adapters = Array.from(new Set(plan.steps.map((s: any) => String(s?.adapter ?? "").trim()).filter(Boolean))).sort();
  const adapter_type = adapters.length ? adapters.join("+") : "unknown";
  const write = plan.steps.some((s: any) => (s as any).read_only !== true);
  return { capability_set: normalizeCaps(requiredCaps), adapter_type, write };
}

function listPromotionRecords(): Array<{ fingerprint: string; record: any }> {
  const dir = promotionsDir();
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  const out: Array<{ fingerprint: string; record: any }> = [];
  for (const f of files) {
    const fp = f.replace(/\.json$/i, "");
    const rec = readPromotion(fp);
    if (rec) out.push({ fingerprint: fp, record: rec as any });
  }
  return out;
}

function promotionsMatchingClass(def: DelegatedClassDefinition): Array<{ fingerprint: string; confidence_avg: number; command: string }> {
  const promotions = listPromotionRecords();
  const out: Array<{ fingerprint: string; confidence_avg: number; command: string }> = [];
  for (const p of promotions) {
    const cmd = typeof p.record?.command === "string" ? p.record.command : "";
    if (!cmd) continue;
    if (!patternMatchesCommand(def.pattern, cmd)) continue;
    if (isDemoted(p.fingerprint)) continue;
    const avg = Number(p.record?.criteria?.confidence_avg);
    out.push({ fingerprint: p.fingerprint, confidence_avg: Number.isFinite(avg) ? avg : 0, command: cmd });
  }
  out.sort((a, b) => {
    if (b.confidence_avg !== a.confidence_avg) return b.confidence_avg - a.confidence_avg;
    return a.fingerprint.localeCompare(b.fingerprint);
  });
  return out;
}

export function evaluateDelegationForPlan(params: {
  plan: ExecutionPlan;
  command: string;
  autonomy_mode: string;
  // Whether this fingerprint is already promoted (exact).
  promoted: boolean;
}): DelegationDecision {
  const normalizedCommand = normalizeDslCommand(params.command);
  const classes = listLatestDelegatedClasses();

  const meta = planMeta(params.plan);

  const candidates = classes.filter((c) => {
    if (!patternMatchesCommand(c.pattern, normalizedCommand)) return false;
    if (c.adapter !== meta.adapter_type) return false;
    if (Boolean(c.write) !== Boolean(meta.write)) return false;
    const classCaps = normalizeCaps(c.capabilities);
    if (classCaps.length !== meta.capability_set.length) return false;
    for (let i = 0; i < classCaps.length; i += 1) {
      if (classCaps[i] !== meta.capability_set[i]) return false;
    }
    return true;
  });

  if (!candidates.length) {
    return {
      kind: "DelegationDecision",
      matched: false,
      class_id: null,
      active: false,
      inherited: false,
      reason: "NO_MATCH",
      scope: null,
      evidence: { promotions_matching: 0, promotions_meeting_confidence: 0 },
      suspension: { active: false, suspended_at: null, reason: null },
    };
  }

  // Deterministic selection: lexicographically smallest class_id.
  candidates.sort((a, b) => a.class_id.localeCompare(b.class_id));
  const def = candidates[0]!;

  const status = getDelegationStatus(def.class_id);
  const approval = status.approval;

  const scope: DelegatedApprovalScope | null = approval ? approval.scope : null;

  const promos = promotionsMatchingClass(def);
  const promotions_matching = promos.length;
  const confidence_min = scope ? Number(scope.confidence_min) : 0;
  const promotions_meeting_confidence = promos.filter((p) => p.confidence_avg >= confidence_min).length;

  const suspended = status.reason === "SUSPENDED";

  if (!approval) {
    return {
      kind: "DelegationDecision",
      matched: true,
      class_id: def.class_id,
      active: false,
      inherited: false,
      reason: "NOT_APPROVED",
      scope: null,
      evidence: { promotions_matching, promotions_meeting_confidence },
      suspension: {
        active: Boolean(status.suspension),
        suspended_at: status.suspension?.suspended_at ?? null,
        reason: status.suspension?.reason ?? null,
      },
    };
  }

  if (status.reason === "REVOKED") {
    return {
      kind: "DelegationDecision",
      matched: true,
      class_id: def.class_id,
      active: false,
      inherited: false,
      reason: "REVOKED",
      scope,
      evidence: { promotions_matching, promotions_meeting_confidence },
      suspension: {
        active: Boolean(status.suspension),
        suspended_at: status.suspension?.suspended_at ?? null,
        reason: status.suspension?.reason ?? null,
      },
    };
  }

  if (suspended) {
    return {
      kind: "DelegationDecision",
      matched: true,
      class_id: def.class_id,
      active: false,
      inherited: false,
      reason: "SUSPENDED",
      scope,
      evidence: { promotions_matching, promotions_meeting_confidence },
      suspension: {
        active: true,
        suspended_at: status.suspension?.suspended_at ?? null,
        reason: status.suspension?.reason ?? null,
      },
    };
  }

  if (scope && String(scope.autonomy_mode) !== String(params.autonomy_mode)) {
    return {
      kind: "DelegationDecision",
      matched: true,
      class_id: def.class_id,
      active: false,
      inherited: false,
      reason: "MODE_MISMATCH",
      scope,
      evidence: { promotions_matching, promotions_meeting_confidence },
      suspension: {
        active: Boolean(status.suspension),
        suspended_at: status.suspension?.suspended_at ?? null,
        reason: status.suspension?.reason ?? null,
      },
    };
  }

  if (scope?.promotion_required) {
    if (promotions_matching === 0) {
      return {
        kind: "DelegationDecision",
        matched: true,
        class_id: def.class_id,
        active: false,
        inherited: false,
        reason: "PROMOTION_REQUIRED_MISSING",
        scope,
        evidence: { promotions_matching, promotions_meeting_confidence },
        suspension: {
          active: Boolean(status.suspension),
          suspended_at: status.suspension?.suspended_at ?? null,
          reason: status.suspension?.reason ?? null,
        },
      };
    }

    if (promotions_meeting_confidence === 0) {
      return {
        kind: "DelegationDecision",
        matched: true,
        class_id: def.class_id,
        active: false,
        inherited: false,
        reason: "CONFIDENCE_TOO_LOW",
        scope,
        evidence: { promotions_matching, promotions_meeting_confidence },
        suspension: {
          active: Boolean(status.suspension),
          suspended_at: status.suspension?.suspended_at ?? null,
          reason: status.suspension?.reason ?? null,
        },
      };
    }
  }

  // Delegation only matters when the fingerprint isn't already promoted.
  const inherited = !params.promoted;

  return {
    kind: "DelegationDecision",
    matched: true,
    class_id: def.class_id,
    active: true,
    inherited,
    reason: "OK",
    scope,
    evidence: { promotions_matching, promotions_meeting_confidence },
    suspension: {
      active: Boolean(status.suspension),
      suspended_at: status.suspension?.suspended_at ?? null,
      reason: status.suspension?.reason ?? null,
    },
  };
}

export function evaluateDelegationForCommandPatternOnly(params: { command: string }): Array<{ class_id: string; pattern: string }> {
  const normalized = normalizeDslCommand(params.command);
  const classes = listLatestDelegatedClasses();
  const out: Array<{ class_id: string; pattern: string }> = [];
  for (const c of classes) {
    if (patternMatchesCommand(c.pattern, normalized)) {
      out.push({ class_id: c.class_id, pattern: c.pattern });
    }
  }
  out.sort((a, b) => a.class_id.localeCompare(b.class_id));
  return out;
}

export function readDelegatedClassDefinition(class_id: string) {
  return readLatestDelegatedClassDefinition(class_id);
}
