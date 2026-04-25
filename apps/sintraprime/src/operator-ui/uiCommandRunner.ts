import path from "node:path";
import { spawnSync } from "node:child_process";

export type UiCliRunResult = {
  exitCode: number;
  stdout: string;
  stderr: string;
  json: unknown | null;
};

export function runEngineCliForUi(command: string): UiCliRunResult {
  const trimmed = String(command ?? "").trim();

  const entry = /^(\/queue\b|\/run\b)/i.test(trimmed)
    ? path.join(process.cwd(), "src", "cli", "run-console.ts")
    : /^\/scheduler\b/i.test(trimmed)
      ? path.join(process.cwd(), "src", "cli", "run-scheduler.ts")
      : /^\/policy\b/i.test(trimmed)
        ? path.join(process.cwd(), "src", "cli", "run-policy.ts")
        : /^\/delegate\b/i.test(trimmed)
          ? path.join(process.cwd(), "src", "cli", "run-delegate.ts")
          : /^\/operator-ui\b/i.test(trimmed)
            ? path.join(process.cwd(), "src", "cli", "run-operator-ui.ts")
            : /^\/operator\b/i.test(trimmed)
              ? path.join(process.cwd(), "src", "cli", "run-operator.ts")
              : path.join(process.cwd(), "src", "cli", "run-command.ts");

  const tsxNodeEntrypoint = path.join(process.cwd(), "node_modules", "tsx", "dist", "cli.mjs");

  const res = spawnSync(process.execPath, [tsxNodeEntrypoint, entry, command], {
    env: process.env,
    encoding: "utf8",
    windowsHide: true,
  });

  if (res.error) throw new Error(res.error.message);

  const stdout = String(res.stdout ?? "").trim();
  const stderr = String(res.stderr ?? "").trim();

  let json: unknown | null = null;
  if (stdout) {
    try {
      json = JSON.parse(stdout);
    } catch {
      json = null;
    }
  }

  return { exitCode: res.status ?? 0, stdout, stderr, json };
}
