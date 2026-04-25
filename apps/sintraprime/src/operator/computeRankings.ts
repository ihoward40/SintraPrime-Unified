import fs from "node:fs";
import path from "node:path";

type Receipt = {
  execution_id?: string;
  threadId?: string;
  status?: string;
  kind?: string;
  policy_denied?: { code?: string } | null;
  started_at?: string;
  finished_at?: string;
};

export type RankingSignals = {
  successes: number;
  rollbacks: number;
  policy_denials: number;
  throttles: number;
  approvals: number;
};

export type OperatorRanking = {
  kind: "OperatorRanking";
  operator: string;
  score: number; // 0..100
  confidence: number; // 0..1
  signals: RankingSignals;
  computed_at: string;
};

export type FingerprintRanking = {
  kind: "FingerprintRanking";
  fingerprint: string;
  score: number;
  confidence: number;
  signals: RankingSignals;
  computed_at: string;
};

export type DomainRanking = {
  kind: "DomainRanking";
  domain: string;
  score: number;
  confidence: number;
  signals: RankingSignals;
  computed_at: string;
};

export type RankingsBundle = {
  kind: "RankingsComputed";
  window_days: number;
  operators: OperatorRanking[];
  fingerprints: FingerprintRanking[];
  domains: DomainRanking[];
};

const RECEIPTS_FILE = path.join("runs", "receipts.jsonl");

export function computeRankings(opts: { windowDays: number }): RankingsBundle {
  const windowDays = opts.windowDays;
  const nowIso = new Date().toISOString();
  const cutoff = Date.now() - windowDays * 24 * 60 * 60 * 1000;

  const receipts = readReceiptsJsonl(RECEIPTS_FILE).filter((r) => within(r, cutoff));

  // group keys: operator, fingerprint, domain
  // NOTE: operator is derived from threadId prefix if present (operator:xxx|thread) else "unknown"
  const byOperator = new Map<string, RankingSignals>();
  const byFingerprint = new Map<string, RankingSignals>();
  const byDomain = new Map<string, RankingSignals>();

  for (const r of receipts) {
    const sig = receiptToSignals(r);

    const operator = deriveOperator(r.threadId);
    mergeSignals(byOperator, operator, sig);

    const fp = deriveFingerprint(r);
    mergeSignals(byFingerprint, fp, sig);

    const domain = deriveDomain(r);
    mergeSignals(byDomain, domain, sig);
  }

  const operators: OperatorRanking[] = [];
  for (const [operator, signals] of byOperator.entries()) {
    const confidence = readConfidenceForKey(operator, "operator");
    const score = scoreSignals(signals, confidence);
    operators.push({ kind: "OperatorRanking", operator, score, confidence, signals, computed_at: nowIso });
  }

  const fingerprints: FingerprintRanking[] = [];
  for (const [fingerprint, signals] of byFingerprint.entries()) {
    const confidence = readConfidenceForKey(fingerprint, "fingerprint");
    const score = scoreSignals(signals, confidence);
    fingerprints.push({
      kind: "FingerprintRanking",
      fingerprint,
      score,
      confidence,
      signals,
      computed_at: nowIso,
    });
  }

  const domains: DomainRanking[] = [];
  for (const [domain, signals] of byDomain.entries()) {
    const confidence = readConfidenceForKey(domain, "domain");
    const score = scoreSignals(signals, confidence);
    domains.push({ kind: "DomainRanking", domain, score, confidence, signals, computed_at: nowIso });
  }

  // stable sort
  operators.sort((a, b) => b.score - a.score || a.operator.localeCompare(b.operator));
  fingerprints.sort((a, b) => b.score - a.score || a.fingerprint.localeCompare(b.fingerprint));
  domains.sort((a, b) => b.score - a.score || a.domain.localeCompare(b.domain));

  return {
    kind: "RankingsComputed",
    window_days: windowDays,
    operators,
    fingerprints,
    domains,
  };
}

function readReceiptsJsonl(p: string): Receipt[] {
  if (!fs.existsSync(p)) return [];
  const lines = fs.readFileSync(p, "utf8").split(/\r?\n/).filter(Boolean);
  const out: Receipt[] = [];
  for (const line of lines) {
    try {
      out.push(JSON.parse(line));
    } catch {
      /* ignore */
    }
  }
  return out;
}

function within(r: Receipt, cutoffMs: number): boolean {
  const t = Date.parse(r.finished_at ?? r.started_at ?? "");
  if (!Number.isFinite(t)) return true;
  return t >= cutoffMs;
}

function receiptToSignals(r: Receipt): RankingSignals {
  const k = (r.kind ?? "").toLowerCase();
  const status = (r.status ?? "").toLowerCase();
  const denyCode = (r.policy_denied?.code ?? "").toUpperCase();
  return {
    successes: status === "success" ? 1 : 0,
    rollbacks: k === "rollbackrecorded" ? 1 : 0,
    policy_denials: k === "policydenied" || !!denyCode ? 1 : 0,
    throttles: k === "throttled" ? 1 : 0,
    approvals: k === "approvalrequired" || status === "awaiting_approval" ? 1 : 0,
  };
}

function mergeSignals(map: Map<string, RankingSignals>, key: string, add: RankingSignals) {
  const cur = map.get(key) ?? { successes: 0, rollbacks: 0, policy_denials: 0, throttles: 0, approvals: 0 };
  map.set(key, {
    successes: cur.successes + add.successes,
    rollbacks: cur.rollbacks + add.rollbacks,
    policy_denials: cur.policy_denials + add.policy_denials,
    throttles: cur.throttles + add.throttles,
    approvals: cur.approvals + add.approvals,
  });
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function scoreSignals(s: RankingSignals, confidence: number): number {
  // stable + explainable
  let score = 100;
  score -= s.rollbacks * 20;
  score -= s.policy_denials * 10;
  score -= s.throttles * 5;
  score += s.successes * 2;
  score = clamp(score, 0, 100);
  score = Math.round(score * clamp(confidence, 0, 1));
  return score;
}

function deriveOperator(threadId?: string): string {
  // supports "operator:alice|local_test_001" convention; otherwise unknown
  if (!threadId) return "unknown";
  const m = threadId.match(/^operator:([^|]+)\|/i);
  return m?.[1] ?? "unknown";
}

function deriveFingerprint(r: Receipt): string {
  // minimal deterministic fallback (you can later enrich from plan metadata)
  return r.kind ? `kind:${r.kind}` : "kind:unknown";
}

function deriveDomain(r: Receipt): string {
  // deterministic fallback without parsing plans (good enough for Tier-17)
  const code = (r.policy_denied?.code ?? "").toUpperCase();
  if (code.includes("NOTION")) return "notion";
  if (code.includes("DOMAIN")) return "policy";
  return "general";
}

function readConfidenceForKey(key: string, kind: "operator" | "fingerprint" | "domain"): number {
  // Optional: if absent, defaults to 1.0
  const p = path.join("runs", "confidence", kind, `${safeFile(key)}.json`);
  if (!fs.existsSync(p)) return 1.0;
  try {
    const j = JSON.parse(fs.readFileSync(p, "utf8"));
    const v = typeof j?.score === "number" ? j.score : 1.0;
    return clamp(v, 0, 1);
  } catch {
    return 1.0;
  }
}

function safeFile(s: string) {
  return s.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 160);
}
