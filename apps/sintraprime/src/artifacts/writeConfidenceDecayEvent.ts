import fs from "node:fs";
import path from "node:path";

function safeFilePart(input: string): string {
  const s = String(input ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 120);
}

export function writeConfidenceDecayEvent(input: {
  fingerprint: string;
  from: string;
  to: string;
  reason: string;
  timestamp: string;
}) {
  const dir = path.join(process.cwd(), "runs", "confidence", "events");
  fs.mkdirSync(dir, { recursive: true });

  const ts = new Date(input.timestamp).getTime();
  const safeTs = Number.isFinite(ts) ? ts : Date.now();

  const file = path.join(dir, `${safeFilePart(input.fingerprint)}.${safeTs}.json`);

  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        fingerprint: input.fingerprint,
        from: input.from,
        to: input.to,
        reason: input.reason,
        timestamp: input.timestamp,
      },
      null,
      2
    ) + "\n",
    { encoding: "utf8" }
  );

  return file;
}
