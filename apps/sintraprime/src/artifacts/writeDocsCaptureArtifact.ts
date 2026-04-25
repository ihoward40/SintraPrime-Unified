import fs from "node:fs";
import path from "node:path";

export function writeDocsCaptureArtifact(input: {
  execution_id: string;
  step_id: string;
  url: string;
  http_status: number;
  content_type: string | null;
  sha256_hex: string;
  body_bytes: Buffer;
}) {
  const dir = "runs/docs-capture";
  fs.mkdirSync(dir, { recursive: true });

  // Write metadata file
  const metaFile = path.join(dir, `${input.execution_id}.${input.step_id}.meta.json`);
  fs.writeFileSync(
    metaFile,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        step_id: input.step_id,
        url: input.url,
        http_status: input.http_status,
        content_type: input.content_type,
        sha256_hex: input.sha256_hex,
        byte_length: input.body_bytes.length,
        captured_at: new Date().toISOString(),
      },
      null,
      2
    )
  );

  // Write body file
  const bodyFile = path.join(dir, `${input.execution_id}.${input.step_id}.body`);
  fs.writeFileSync(bodyFile, input.body_bytes);

  return {
    metaFile,
    bodyFile,
  };
}
