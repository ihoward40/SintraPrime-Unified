import fs from "node:fs";
import path from "node:path";

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

export function writeNotionReadArtifact(params: {
  execution_id: string;
  threadId: string;
  action: string;
  step_id: string;
  requested_at: string;
  finished_at: string;
  response: unknown;
}) {
  const dir = path.join(process.cwd(), "runs", "notion");
  fs.mkdirSync(dir, { recursive: true });

  const safeStepId = String(params.step_id).replace(/[\\/:*?"<>|]/g, "_");
  const responseRecord = isRecord(params.response) ? params.response : null;
  const id = responseRecord && typeof responseRecord.id === "string" ? responseRecord.id : null;
  const properties = responseRecord && isRecord(responseRecord.properties) ? responseRecord.properties : null;

  const out = {
    execution_id: params.execution_id,
    threadId: params.threadId,
    adapter: "notion",
    action: params.action,
    step_id: params.step_id,
    requested_at: params.requested_at,
    finished_at: params.finished_at,
    id,
    properties,
    response: params.response,
  };

  const file = path.join(dir, `${params.execution_id}.${params.step_id}.json`);
  fs.writeFileSync(file, JSON.stringify(out, null, 2), { encoding: "utf8" });
  return file;
}
