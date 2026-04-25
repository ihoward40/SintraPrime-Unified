import fs from "node:fs";
import path from "node:path";

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);

}

function sanitizeFilenamePart(v: string): string {
  return v.replace(/[\\\/:*?"<>|]/g, "_");
}

export function writeNotionWriteArtifact(params: {
  execution_id: string;
  threadId: string;
  action: string;
  step_id: string;
  approved_at?: string;
  requested_at: string;
  finished_at: string;
  request_payload: unknown;
  response: unknown;
}) {
  const dir = path.join(process.cwd(), "runs", "notion-write");
    fs.mkdirSync(dir, { recursive: true });

    const safeStepId = sanitizeFilenamePart(String(params.step_id));
    const responseRecord = isRecord(params.response) ? params.response : null;
    const title = responseRecord && typeof responseRecord.title === "string" ? responseRecord.title : null;
    const updated =
      responseRecord && typeof responseRecord.updated === "boolean" ? responseRecord.updated : null;

    const payload = {
      execution_id: params.execution_id,
      threadId: params.threadId,
      action: params.action,
      step_id: params.step_id,
      approved_at: params.approved_at,
      requested_at: params.requested_at,
      finished_at: params.finished_at,
      request_payload: params.request_payload,
      updated,
      title,
      response: params.response,
    };

    const file = path.join(dir, `${params.execution_id}.${safeStepId}.json`);
    fs.writeFileSync(file, JSON.stringify(payload, null, 2), "utf8");
    return file;
  }
