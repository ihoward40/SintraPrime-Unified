import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { redactJson } from "./redact.js";

function mkdirp(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

function sha256(buf: Buffer) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function sha256File(p: string) {
  return sha256(fs.readFileSync(p));
}

function stableJsonStringify(value: unknown) {
  // Stable key ordering for objects.
  const stable = (v: any): any => {
    if (v === null || v === undefined) return v;
    if (Array.isArray(v)) return v.map(stable);
    if (typeof v !== "object") return v;
    const keys = Object.keys(v).sort();
    const out: any = {};
    for (const k of keys) out[k] = stable(v[k]);
    return out;
  };
  return JSON.stringify(stable(value), null, 2) + "\n";
}

function parseIsoOrNull(value: unknown): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const t = Date.parse(value);
  return Number.isFinite(t) ? t : null;
}

function receiptTimestampMs(row: any): number | null {
  // Prefer the common receipt fields.
  const candidates = [
    row?.finished_at,
    row?.started_at,
    row?.timestamp,
    row?.generated_at,
    row?.ran_at,
    row?.at,
  ];
  for (const c of candidates) {
    const t = parseIsoOrNull(c);
    if (t !== null) return t;
  }
  return null;
}

function copyDir(src: string, dst: string, opts: { redact: boolean }) {
  if (!fs.existsSync(src)) return;
  mkdirp(dst);
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const ent of entries) {
    const s = path.join(src, ent.name);
    const t = path.join(dst, ent.name);
    if (ent.isDirectory()) {
      copyDir(s, t, opts);
      continue;
    }
    if (!ent.isFile()) continue;

    if (opts.redact && ent.name.toLowerCase().endsWith(".json")) {
      try {
        const raw = JSON.parse(fs.readFileSync(s, "utf8"));
        const red = redactJson(raw);
        fs.writeFileSync(t, stableJsonStringify(red), "utf8");
      } catch {
        // Fall back to raw copy if JSON is unreadable.
        fs.copyFileSync(s, t);
      }
      continue;
    }

    fs.copyFileSync(s, t);
  }
}

function listFilesRecursive(rootDir: string): string[] {
  const out: string[] = [];
  const stack: string[] = [rootDir];
  while (stack.length) {
    const cur = stack.pop()!;
    const entries = fs.readdirSync(cur, { withFileTypes: true });
    for (const ent of entries) {
      const p = path.join(cur, ent.name);
      if (ent.isDirectory()) stack.push(p);
      else if (ent.isFile()) out.push(p);
    }
  }
  return out;
}

function generateExportDir(baseDir: string) {
  if (!fs.existsSync(baseDir)) return baseDir;
  for (let i = 2; i <= 9999; i += 1) {
    const candidate = `${baseDir}_${i}`;
    if (!fs.existsSync(candidate)) return candidate;
  }
  throw new Error("Unable to allocate unique audit export directory");
}

export type AuditExportResult = {
  kind: "AuditExportResult";
  export_dir: string;
  export_id: string;
  manifest_hash: string;
  files: number;
};

export function exportAuditCourtPacket(opts: {
  since_iso: string;
  redact: boolean;
  include_artifacts: boolean;
}): AuditExportResult {
  const sinceMs = Date.parse(opts.since_iso);
  if (!Number.isFinite(sinceMs)) {
    throw new Error("since_iso must be a valid ISO timestamp");
  }

  const ts = new Date().toISOString().replace(/[-:]/g, "").replace(/\./g, "");
  const export_id = `AUDIT_${ts}`;

  const baseRoot = path.resolve(process.cwd(), "exports", "audit");
  mkdirp(baseRoot);
  const outDir = generateExportDir(path.join(baseRoot, export_id));

  const exhibitsDir = path.join(outDir, "EXHIBITS");
  const hashesDir = path.join(outDir, "HASHES");
  const verifyDir = path.join(outDir, "VERIFY");
  const redactionDir = path.join(outDir, "REDACTION");
  const approvalsOutDir = path.join(outDir, "approvals");
  const schedulerHistoryOutDir = path.join(outDir, "scheduler-history");
  const autonomyOutDir = path.join(outDir, "autonomy");
  const artifactsOutDir = path.join(outDir, "artifacts");

  mkdirp(exhibitsDir);
  mkdirp(hashesDir);
  mkdirp(verifyDir);
  mkdirp(redactionDir);

  const runsDir = path.resolve(process.cwd(), "runs");
  const receiptsPath = path.join(runsDir, "receipts.jsonl");
  const approvalsDir = path.join(runsDir, "approvals");
  const schedulerHistoryDir = path.join(runsDir, "scheduler-history");
  const autonomyDir = path.join(runsDir, "autonomy");
  const constitutionPath = path.resolve(process.cwd(), "docs", "CONSTITUTION.v1.md");

  // Exhibit A: receipts filtered by since.
  const outReceipts = path.join(exhibitsDir, "A_receipts.jsonl");
  if (!fs.existsSync(receiptsPath)) {
    fs.writeFileSync(outReceipts, "", "utf8");
  } else {
    const raw = fs.readFileSync(receiptsPath, "utf8");
    const lines = raw.split(/\r?\n/).filter(Boolean);
    const kept: string[] = [];
    for (const line of lines) {
      try {
        const row = JSON.parse(line);
        const t = receiptTimestampMs(row);
        if (t === null || t < sinceMs) continue;
        const value = opts.redact ? redactJson(row) : row;
        kept.push(JSON.stringify(value));
      } catch {
        // skip malformed line
      }
    }
    fs.writeFileSync(outReceipts, kept.length ? kept.join("\n") + "\n" : "", "utf8");
  }

  // Copy ledgers/directories (redacted JSON where possible).
  copyDir(approvalsDir, approvalsOutDir, { redact: opts.redact });
  copyDir(schedulerHistoryDir, schedulerHistoryOutDir, { redact: opts.redact });
  copyDir(autonomyDir, autonomyOutDir, { redact: opts.redact });

  if (opts.include_artifacts && fs.existsSync(runsDir)) {
    mkdirp(artifactsOutDir);
    for (const ent of fs.readdirSync(runsDir, { withFileTypes: true })) {
      const name = ent.name;
      if (name === "approvals" || name === "scheduler-history" || name === "autonomy" || name === "receipts.jsonl") {
        continue;
      }
      const src = path.join(runsDir, name);
      const dst = path.join(artifactsOutDir, name);
      if (ent.isDirectory()) copyDir(src, dst, { redact: opts.redact });
      else if (ent.isFile()) fs.copyFileSync(src, dst);
    }
  }

  // Exhibit B: artifacts list (paths only; deterministic ordering).
  const artifactsListPath = path.join(exhibitsDir, "B_artifacts_list.json");
  const artifactsListed = fs.existsSync(artifactsOutDir)
    ? listFilesRecursive(artifactsOutDir)
        .map((abs) => path.relative(outDir, abs).replace(/\\/g, "/"))
        .sort((a, b) => a.localeCompare(b))
    : [];
  fs.writeFileSync(
    artifactsListPath,
    stableJsonStringify({ kind: "ArtifactsList", include_artifacts: opts.include_artifacts, files: artifactsListed }),
    "utf8"
  );

  // Exhibit C: approvals index
  const approvalsIndexPath = path.join(exhibitsDir, "C_approvals.json");
  const approvalsFiles = fs.existsSync(approvalsOutDir)
    ? listFilesRecursive(approvalsOutDir)
        .map((abs) => path.relative(outDir, abs).replace(/\\/g, "/"))
        .sort((a, b) => a.localeCompare(b))
    : [];
  fs.writeFileSync(approvalsIndexPath, stableJsonStringify({ kind: "ApprovalsIndex", files: approvalsFiles }), "utf8");

  // Exhibit D: policy snapshot
  const policySnapPath = path.join(exhibitsDir, "D_policy_snapshot.json");
  fs.writeFileSync(
    policySnapPath,
    stableJsonStringify({
      kind: "PolicySnapshot",
      generated_at: new Date().toISOString(),
      AUTONOMY_MODE: process.env.AUTONOMY_MODE || "OFF",
      ALLOWED_DOMAINS: process.env.ALLOWED_DOMAINS || "",
      POLICY_MAX_STEPS: process.env.POLICY_MAX_STEPS || "",
      POLICY_MAX_RUNTIME_MS: process.env.POLICY_MAX_RUNTIME_MS || "",
      POLICY_MAX_RUNS_PER_DAY: process.env.POLICY_MAX_RUNS_PER_DAY || "",
    }),
    "utf8"
  );

  // Exhibit E: constitution
  const constitutionOutPath = path.join(exhibitsDir, "E_constitution.md");
  if (fs.existsSync(constitutionPath)) {
    fs.copyFileSync(constitutionPath, constitutionOutPath);
  } else {
    fs.writeFileSync(constitutionOutPath, "# CONSTITUTION.v1 missing\n", "utf8");
  }

  // Cover + index
  fs.writeFileSync(
    path.join(outDir, "COVER.md"),
    [
      "# Audit Export (Court Packet)",
      "",
      `- export_id: ${export_id}`,
      `- generated_at: ${new Date().toISOString()}`,
      `- since: ${opts.since_iso}`,
      `- redact: ${opts.redact}`,
      `- include_artifacts: ${opts.include_artifacts}`,
      "",
      "This bundle is designed to be verified offline using the included verifier.",
    ].join("\n") + "\n",
    "utf8"
  );

  fs.writeFileSync(
    path.join(outDir, "INDEX.md"),
    [
      "# Index",
      "",
      "- EXHIBITS/A_receipts.jsonl — receipts ledger (filtered)",
      "- EXHIBITS/B_artifacts_list.json — artifacts list", 
      "- EXHIBITS/C_approvals.json — approvals index",
      "- EXHIBITS/D_policy_snapshot.json — policy snapshot",
      "- EXHIBITS/E_constitution.md — constitution v1",
      "",
      "Verification:",
      "- See VERIFY/VERIFY_INSTRUCTIONS.md",
    ].join("\n") + "\n",
    "utf8"
  );

  // Redaction rules record (documented even if redact=false)
  fs.writeFileSync(
    path.join(redactionDir, "redaction_rules.json"),
    stableJsonStringify({
      kind: "RedactionRules",
      redact_enabled: opts.redact,
      rules: [
        { match: "Authorization", action: "replace", value: "[REDACTED]" },
        { match: "X-Webhook-Secret", action: "replace", value: "[REDACTED]" },
        { match: "NOTION_TOKEN", action: "replace", value: "[REDACTED]" },
        { match: "SSN", action: "mask" },
      ],
    }),
    "utf8"
  );

  // Verifier (CommonJS so it runs without a package.json)
  fs.writeFileSync(
    path.join(verifyDir, "verify.cjs"),
    [
      "const fs = require('node:fs');",
      "const path = require('node:path');",
      "const crypto = require('node:crypto');",
      "",
      "function sha256(buf){return crypto.createHash('sha256').update(buf).digest('hex');}",
      "const root = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();",
      "const manifestPath = path.join(root, 'HASHES', 'manifest.json');",
      "const manifestHashPath = path.join(root, 'HASHES', 'manifest.sha256');",
      "const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));",
      "const expectedManifestHash = String(fs.readFileSync(manifestHashPath, 'utf8') || '').trim();",
      "const gotManifestHash = sha256(fs.readFileSync(manifestPath));",
      "if (expectedManifestHash && gotManifestHash !== expectedManifestHash) {",
      "  console.error('[FAIL] manifest hash mismatch expected', expectedManifestHash, 'got', gotManifestHash);",
      "  console.log(JSON.stringify({ ok: false, export_id: manifest.export_id, reason: 'MANIFEST_HASH_MISMATCH' }, null, 2));",
      "  process.exit(2);",
      "}",
      "let ok = true;",
      "for (const f of (manifest.files || [])) {",
      "  const abs = path.join(root, f.path);",
      "  const got = sha256(fs.readFileSync(abs));",
      "  if (got !== f.sha256) {",
      "    ok = false;",
      "    console.error('[FAIL]', f.path, 'expected', f.sha256, 'got', got);",
      "  }",
      "}",
      "if (ok) {",
      "  console.log(JSON.stringify({ ok: true, export_id: manifest.export_id, files: (manifest.files || []).length }, null, 2));",
      "  process.exit(0);",
      "}",
      "console.log(JSON.stringify({ ok: false, export_id: manifest.export_id }, null, 2));",
      "process.exit(2);",
      "",
    ].join("\n"),
    "utf8"
  );

  fs.writeFileSync(
    path.join(verifyDir, "VERIFY_INSTRUCTIONS.md"),
    [
      "# Verify This Audit Packet",
      "",
      "Node.js 20+ required.",
      "",
      "Run:",
      "  node VERIFY/verify.cjs .",
      "",
      "Expected:",
      "  { \"ok\": true, ... }",
    ].join("\n") + "\n",
    "utf8"
  );

  // Manifest (exclude manifest files themselves to avoid circularity).
  const manifestPath = path.join(hashesDir, "manifest.json");
  const manifestHashPath = path.join(hashesDir, "manifest.sha256");

  const allFilesAbs = listFilesRecursive(outDir);
  const files = allFilesAbs
    .map((abs) => ({
      abs,
      rel: path.relative(outDir, abs).replace(/\\/g, "/"),
    }))
    .filter((f) => f.rel !== "HASHES/manifest.json" && f.rel !== "HASHES/manifest.sha256")
    .map((f) => ({
      path: f.rel,
      sha256: sha256File(f.abs),
      bytes: fs.statSync(f.abs).size,
    }))
    .sort((a, b) => a.path.localeCompare(b.path));

  const manifestObj = {
    kind: "AuditExportManifest",
    export_id,
    generated_at: new Date().toISOString(),
    since: opts.since_iso,
    redact: opts.redact,
    include_artifacts: opts.include_artifacts,
    files,
  };
  fs.writeFileSync(manifestPath, stableJsonStringify(manifestObj), "utf8");
  const manifestHash = sha256File(manifestPath);
  fs.writeFileSync(manifestHashPath, manifestHash + "\n", "utf8");

  return {
    kind: "AuditExportResult",
    export_dir: outDir.replace(/\\/g, "/"),
    export_id,
    manifest_hash: manifestHash,
    files: files.length,
  };
}
