import fs from "node:fs";
import path from "node:path";

export function writeRollbackArtifact(input: {
  execution_id: string;
  rolled_back_execution_id: string;
  plan_hash: string;
  started_at: string;
  finished_at: string;
  compensation_plan: any;
  result: any;
}) {
  const dir = "runs/rollback";
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${input.execution_id}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        rolled_back_execution_id: input.rolled_back_execution_id,
        plan_hash: input.plan_hash,
        started_at: input.started_at,
        finished_at: input.finished_at,
        compensation_plan: input.compensation_plan,
        result: input.result,
      },
      null,
      2
    )
  );

  return file;
}
