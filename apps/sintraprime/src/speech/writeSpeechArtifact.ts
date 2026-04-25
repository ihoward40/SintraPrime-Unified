import fs from "node:fs";
import path from "node:path";

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

export function writeSpeechArtifact<T extends Record<string, unknown>>(input: {
  dir: string;
  fingerprint: string;
  timestamp: string;
  suffix?: string;
  payload: T;
}) {
  const artifactDir = path.join(process.cwd(), "runs", input.dir);
  fs.mkdirSync(artifactDir, { recursive: true });

  const ts = new Date(input.timestamp).getTime();
  const safeTs = Number.isFinite(ts) ? ts : Date.now();
  const suffix = input.suffix ? `.${safeFilePart(input.suffix)}` : "";
  const file = path.join(artifactDir, `${safeFilePart(input.fingerprint)}.${safeTs}${suffix}.json`);

  fs.writeFileSync(file, JSON.stringify(input.payload, null, 2) + "\n", { encoding: "utf8" });
  return { file };
}
