import fs from "node:fs";
import path from "node:path";

const DIR = path.resolve("runs/scheduler-history");

export function historyPath(job_id: string, window_id: string) {
  return path.join(DIR, `${job_id}.${window_id}.json`);
}

export function hasRun(job_id: string, window_id: string): boolean {
  return fs.existsSync(historyPath(job_id, window_id));
}

export function recordRun(data: any) {
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(historyPath(String(data.job_id), String(data.window_id)), JSON.stringify(data, null, 2), {
    encoding: "utf8",
  });
}
