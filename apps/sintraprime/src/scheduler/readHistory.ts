import fs from "node:fs";
import path from "node:path";

const DIR = path.resolve("runs/scheduler-history");

type HistoryOpts = {
  job_id?: string;
  limit?: number;
  since?: Date;
};

export function readSchedulerHistory(opts: HistoryOpts) {
  if (!fs.existsSync(DIR)) return [];

  const files = fs
    .readdirSync(DIR)
    .filter((f) => f.endsWith(".json"))
    .map((f) => path.join(DIR, f));

  const rows = files.map((f) => JSON.parse(fs.readFileSync(f, "utf8")));

  let filtered = rows;

  if (opts.job_id) {
    filtered = filtered.filter((r: any) => r?.job_id === opts.job_id);
  }

  if (opts.since) {
    const sinceMs = opts.since.getTime();
    filtered = filtered.filter((r: any) => {
      const startedAt = new Date(String(r?.started_at ?? ""));
      return Number.isFinite(sinceMs) && Number.isFinite(startedAt.getTime()) && startedAt.getTime() >= sinceMs;
    });
  }

  filtered.sort((a: any, b: any) => {
    const ams = new Date(String(a?.started_at ?? "")).getTime();
    const bms = new Date(String(b?.started_at ?? "")).getTime();
    return bms - ams;
  });

  if (typeof opts.limit === "number" && Number.isFinite(opts.limit) && opts.limit > 0) {
    filtered = filtered.slice(0, opts.limit);
  }

  return filtered;
}
