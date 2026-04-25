import fs from "node:fs";
import path from "node:path";

function safeFileStamp(iso: string) {
  return iso.replace(/[:.]/g, "-");
}

export function writeSchedulerReceipt(data: any) {
  const dir = path.resolve("runs/scheduler");
  fs.mkdirSync(dir, { recursive: true });

  const startedAt = typeof data?.started_at === "string" ? data.started_at : new Date().toISOString();
  const file = path.join(dir, `${String(data?.job_id ?? "unknown")}.${safeFileStamp(startedAt)}.json`);

  fs.writeFileSync(file, JSON.stringify(data, null, 2), { encoding: "utf8" });
  return { artifact: file.replace(/\\/g, "/"), ...data };
}
