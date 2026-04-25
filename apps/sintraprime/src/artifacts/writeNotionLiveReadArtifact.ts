import fs from "node:fs";
import path from "node:path";

export function writeNotionLiveReadArtifact(input: {
  execution_id: string;
  step_id: string;
  notion_path: string;
  http_status: number;
  response: any;
}) {
  const dir = "runs/notion-live-read";
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${input.execution_id}.${input.step_id}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        step_id: input.step_id,
        notion_path: input.notion_path,
        http_status: input.http_status,
        response: input.response,
        captured_at: new Date().toISOString(),
      },
      null,
      2
    )
  );

  return file;
}
