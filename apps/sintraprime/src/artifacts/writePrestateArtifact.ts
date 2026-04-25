import fs from "node:fs";
import path from "node:path";

export function writePrestateArtifact(input: {
  execution_id: string;
  step_id: string;
  resource: { type: string; id: string };
  snapshot: any;
  captured_at: string;
  plan_hash: string;
}) {
  const dir = "runs/prestate";
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${input.execution_id}.${input.step_id}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        step_id: input.step_id,
        resource: input.resource,
        snapshot: input.snapshot,
        captured_at: input.captured_at,
        plan_hash: input.plan_hash,
      },
      null,
      2
    )
  );

  return file;
}
