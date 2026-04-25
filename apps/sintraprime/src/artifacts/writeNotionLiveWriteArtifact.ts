import fs from "node:fs";
import path from "node:path";

export function writeNotionLiveWriteArtifact(input: {
  execution_id: string;
  step_id: string;
  notion_path: string;
  request_properties: any;
  guards?: any[];
  http_status: number;
  response: any;
  approved_at: string;
}) {
  const dir = "runs/notion-live-write";
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${input.execution_id}.${input.step_id}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        step_id: input.step_id,
        notion_path: input.notion_path,
        request_properties: input.request_properties,
        bundle_keys: Object.keys(input.request_properties || {}),
        guards: input.guards || [],
        guard_evaluated_at: input.approved_at ?? null,
        http_status: input.http_status,
        response: input.response,
        approved_at: input.approved_at,
        written_at: new Date().toISOString(),
      },
      null,
      2
    )
  );

  return file;
}
