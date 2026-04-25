import fs from "node:fs";
import path from "node:path";

export function writeIntakeArtifact(params: {
  execution_id: string;
  threadId: string;
  intakePath: string;
  files: unknown[];
  started_at: string;
  finished_at: string;
  plan_version?: string;
}) {
  const dir = path.join(process.cwd(), "runs", "intake");
  fs.mkdirSync(dir, { recursive: true });

  const out = {
    execution_id: params.execution_id,
    threadId: params.threadId,
    path: params.intakePath,
    files: params.files,
    started_at: params.started_at,
    finished_at: params.finished_at,
    plan_version: params.plan_version,
  };

  const file = path.join(dir, `${params.execution_id}.json`);
  fs.writeFileSync(file, JSON.stringify(out, null, 2), { encoding: "utf8" });
  return file;
}
