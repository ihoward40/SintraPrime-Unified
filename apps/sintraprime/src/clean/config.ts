import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";

export type ControlConfig = {
  watch_mode?: {
    enabled?: boolean;
    record_video?: boolean;
    record_screenshots?: boolean;
    slow_mo_ms?: number;
    headless?: boolean;
    redact_secrets?: boolean;
  };
  [k: string]: unknown;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

export function loadControlConfig(cwd: string): ControlConfig {
  const filePath = path.join(cwd, "control", "config.yaml");
  try {
    if (!fs.existsSync(filePath)) return {};
    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = YAML.parse(raw);
    return isRecord(parsed) ? (parsed as ControlConfig) : {};
  } catch {
    return {};
  }
}

export function loadSecretsEnv(cwd: string): Record<string, string> {
  const filePath = path.join(cwd, "control", "secrets.env");
  if (!fs.existsSync(filePath)) return {};

  const raw = fs.readFileSync(filePath, "utf8");
  const out: Record<string, string> = {};

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1);
    if (!key) continue;
    out[key] = value;
  }

  return out;
}

export function applySecretsToProcessEnv(secrets: Record<string, string>) {
  for (const [k, v] of Object.entries(secrets)) {
    if (process.env[k] === undefined) process.env[k] = v;
  }
}
