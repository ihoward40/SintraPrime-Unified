import fs from "node:fs";

export function writeAutonomySummary(input: {
  execution_id: string;
  mode: string;
  steps_executed: string[];
  started_at?: string;
  finished_at?: string;
}) {
  const dir = "runs/autonomy";
  fs.mkdirSync(dir, { recursive: true });
  const file = `${dir}/${input.execution_id}.summary.json`;
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        execution_id: input.execution_id,
        mode: input.mode,
        steps_executed: input.steps_executed,
        started_at: input.started_at,
        finished_at: input.finished_at,
        timestamp: new Date().toISOString(),
      },
      null,
      2
    ),
    { encoding: "utf8" }
  );

  return file;
}
