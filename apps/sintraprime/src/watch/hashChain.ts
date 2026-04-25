import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

import { appendRunLedgerLine, runRoot } from "./runArtifacts.js";

const prevByExecutionId = new Map<string, string | null>();

function sha256Hex(buf: Buffer | string) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function sha256FileHex(filePath: string) {
  const buf = fs.readFileSync(filePath);
  return sha256Hex(buf);
}

export function isRunHashChainEnabled(env: NodeJS.ProcessEnv = process.env) {
  return String(env.RUN_HASH_CHAIN ?? "0").trim() === "1";
}

export function maybeAppendHashChainArtifact(params: {
  execution_id: string;
  artifact_relpath: string;
  artifact_abspath?: string;
  env?: NodeJS.ProcessEnv;
}) {
  const env = params.env ?? process.env;
  if (!isRunHashChainEnabled(env)) return null;

  const executionId = String(params.execution_id);
  const rel = String(params.artifact_relpath).replace(/\\/g, "/");

  const abs =
    typeof params.artifact_abspath === "string" && params.artifact_abspath
      ? params.artifact_abspath
      : path.join(runRoot(executionId), rel);

  if (!fs.existsSync(abs)) return null;

  const artifactSha256 = sha256FileHex(abs);
  const prev = prevByExecutionId.has(executionId) ? prevByExecutionId.get(executionId)! : null;

  // Chain hash is derived from (prev, relpath, artifact sha256).
  const chainHash = sha256Hex(`${prev ?? ""}|${rel}|${artifactSha256}`);
  prevByExecutionId.set(executionId, chainHash);

  appendRunLedgerLine(executionId, {
    at: new Date().toISOString(),
    kind: "hash_chain",
    artifact: rel,
    sha256: artifactSha256,
    prev,
    head: chainHash,
  });

  return { sha256: artifactSha256, prev, head: chainHash, artifact: rel };
}

export function appendHashChainGroup(params: {
  execution_id: string;
  scope: "apply" | "postapply";
  count: number;
  head: string | null;
}) {
  appendRunLedgerLine(String(params.execution_id), {
    at: new Date().toISOString(),
    kind: "hash_chain_group",
    scope: params.scope,
    count: params.count,
    head: params.head,
  });
}
