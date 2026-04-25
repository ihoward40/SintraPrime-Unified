import { createHash } from "node:crypto";
import type { ArtifactRef } from "../artifacts/writeBrowserEvidence.js";

function sha256Hex(s: string): string {
  return createHash("sha256").update(s, "utf8").digest("hex");
}

export function evidenceRollupSha256(evidence: ArtifactRef[]): string {
  const stable = [...evidence]
    .map((e) => ({ kind: e.kind, path: e.path, sha256: e.sha256, mime: e.mime, bytes: e.bytes }))
    .sort((a, b) => {
      const ka = `${a.path}|${a.sha256}|${a.mime}|${a.bytes}`;
      const kb = `${b.path}|${b.sha256}|${b.mime}|${b.bytes}`;
      return ka.localeCompare(kb);
    });
  return sha256Hex(JSON.stringify(stable));
}
