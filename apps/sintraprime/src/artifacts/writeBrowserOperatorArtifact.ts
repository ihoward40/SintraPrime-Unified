import fs from "node:fs";
import path from "node:path";

export function writeBrowserOperatorArtifact(input: {
  execution_id: string;
  step_id: string;
  url: string;
  mode: "offline" | "network";
  http_status: number;
  outputs: Record<string, unknown>;
  screenshots: Array<{
    system: string;
    path: string;
    sha256: string;
    captured_at: string;
  }>;
}) {
  const dir = "runs/browser-operator";
  fs.mkdirSync(dir, { recursive: true });

  const file = path.join(dir, `${input.execution_id}.${input.step_id}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        tool: "browser.operator",
        execution_id: input.execution_id,
        step_id: input.step_id,
        mode: input.mode,
        url: input.url,
        http_status: input.http_status,
        outputs: input.outputs,
        screenshots: input.screenshots,
        screenshots_count: input.screenshots.length,
        written_at: new Date().toISOString(),
      },
      null,
      2
    ) + "\n",
    "utf8"
  );

  return file;
}
