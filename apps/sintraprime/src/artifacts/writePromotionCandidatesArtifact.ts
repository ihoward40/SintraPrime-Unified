import fs from "node:fs";
import path from "node:path";

function safeFilePart(part: string) {
  return String(part ?? "")
    .trim()
    .replace(/[^a-zA-Z0-9._-]+/g, "_")
    .slice(0, 120);
}

export function writePromotionCandidatesArtifact(params: {
  now_iso: string;
  candidates: unknown;
}) {
  const dir = path.join(process.cwd(), "runs", "autonomy-promotion-candidates");
  fs.mkdirSync(dir, { recursive: true });

  const ts = new Date(params.now_iso).toISOString().replace(/[:.]/g, "-");
  const file = path.join(dir, `${safeFilePart(ts)}.json`);
  fs.writeFileSync(file, JSON.stringify(params.candidates, null, 2) + "\n", { encoding: "utf8" });
  return { dir, file };
}
