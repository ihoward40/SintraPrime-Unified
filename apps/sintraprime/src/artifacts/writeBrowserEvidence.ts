import { createHash } from "node:crypto";
import { mkdirSync, statSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

export type ArtifactRef = {
  kind: "artifact";
  path: string;
  sha256: string;
  mime: string;
  bytes: number;
};

function sha256(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("hex");
}

function toPosix(p: string) {
  return p.replace(/\\/g, "/");
}

export function writeArtifactRelative(relPath: string, buf: Buffer, mime: string): ArtifactRef {
  const path = toPosix(relPath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, buf);
  const bytes = statSync(path).size;
  return { kind: "artifact", path, sha256: sha256(buf), mime, bytes };
}
