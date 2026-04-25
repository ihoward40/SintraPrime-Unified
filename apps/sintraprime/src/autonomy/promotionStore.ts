import fs from "node:fs";
import path from "node:path";

export type PromotionRecord = {
  fingerprint: string;
  command: string;
  promoted_at: string;
  criteria: {
    confidence_avg: number;
    runs_observed: number;
    regressions: number;
  };
  previous_mode: string;
  new_mode: "AUTO_RUN";
};

export type DemotionRecord = {
  fingerprint: string;
  demoted_at: string;
  reason: string;
  details?: Record<string, unknown> | null;
};

export function promotionsDir() {
  return path.join(process.cwd(), "runs", "autonomy-promotions");
}

export function demotionsDir() {
  return path.join(process.cwd(), "runs", "autonomy-demotions");
}

export function promotionPath(fingerprint: string) {
  return path.join(promotionsDir(), `${fingerprint}.json`);
}

export function hasPromotion(fingerprint: string) {
  return fs.existsSync(promotionPath(fingerprint));
}

export function readPromotion(fingerprint: string): PromotionRecord | null {
  try {
    const p = promotionPath(fingerprint);
    if (!fs.existsSync(p)) return null;
    const json = JSON.parse(fs.readFileSync(p, "utf8"));
    return json as PromotionRecord;
  } catch {
    return null;
  }
}

export function writePromotion(record: PromotionRecord) {
  fs.mkdirSync(promotionsDir(), { recursive: true });
  const p = promotionPath(record.fingerprint);
  if (fs.existsSync(p)) {
    throw new Error(`Promotion already exists for fingerprint '${record.fingerprint}' (append-only)`);
  }
  fs.writeFileSync(p, JSON.stringify(record, null, 2) + "\n", { encoding: "utf8" });
  return p;
}

export function listDemotionsForFingerprint(fingerprint: string) {
  const dir = demotionsDir();
  if (!fs.existsSync(dir)) return [] as string[];
  const files = fs.readdirSync(dir).filter((f) => f.startsWith(`${fingerprint}.`) && f.endsWith(".json"));
  files.sort();
  return files.map((f) => path.join(dir, f));
}

export function isDemoted(fingerprint: string) {
  return listDemotionsForFingerprint(fingerprint).length > 0;
}

export function writeDemotion(params: {
  fingerprint: string;
  reason: string;
  demoted_at?: string;
  details?: Record<string, unknown> | null;
}) {
  fs.mkdirSync(demotionsDir(), { recursive: true });
  const ts = new Date(params.demoted_at ?? new Date().toISOString()).toISOString().replace(/[:.]/g, "-");
  const file = path.join(demotionsDir(), `${params.fingerprint}.${ts}.json`);
  const rec: DemotionRecord = {
    fingerprint: params.fingerprint,
    demoted_at: params.demoted_at ?? new Date().toISOString(),
    reason: params.reason,
    details: params.details ?? null,
  };
  fs.writeFileSync(file, JSON.stringify(rec, null, 2) + "\n", { encoding: "utf8" });
  return file;
}
