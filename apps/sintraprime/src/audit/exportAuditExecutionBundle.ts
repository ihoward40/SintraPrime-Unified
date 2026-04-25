import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { redactJson } from "./redact.js";

const require = createRequire(import.meta.url);
// yazl is CommonJS
const yazl = require("yazl");

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
  const candidates = [row?.finished_at, row?.started_at, row?.created_at, row?.timestamp, row?.at];
  for (const c of candidates) {
    const t = parseIsoOrNull(c);
    if (t !== null) return t;
  }
  return null;
}

function sanitizeFilePart(value: string) {
  const s = String(value ?? "");
  const cleaned = s.replace(/[\\/<>:\"|?*\x00-\x1F]/g, "_");
  return cleaned.slice(0, 160);
}

function generateUniquePath(baseAbsPath: string) {
  if (!fs.existsSync(baseAbsPath)) return baseAbsPath;
  for (let i = 2; i <= 9999; i += 1) {
    const candidate = `${baseAbsPath}_${i}`;
    if (!fs.existsSync(candidate)) return candidate;
  }
  throw new Error("Unable to allocate unique export path");
}

function readLastReceiptForExecutionId(execution_id: string): any | null {
  const receiptsPath = path.join(process.cwd(), "runs", "receipts.jsonl");
  if (!fs.existsSync(receiptsPath)) return null;
  const lines = fs.readFileSync(receiptsPath, "utf8").split(/\r?\n/).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    try {
      const json = JSON.parse(lines[i]!);
      if (json?.execution_id === execution_id) return json;
    } catch {
      // ignore
    }
  }
  return null;
}

function readJsonIfExists(absPath: string) {
  if (!fs.existsSync(absPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(absPath, "utf8"));
  } catch {
    return null;
  }
}

function listMatchingFilesInDir(dirAbs: string, predicate: (name: string) => boolean) {
  if (!fs.existsSync(dirAbs)) return [] as string[];
  const out: string[] = [];
  for (const name of fs.readdirSync(dirAbs)) {
    if (!predicate(name)) continue;
    const abs = path.join(dirAbs, name);
    try {
      if (fs.statSync(abs).isFile()) out.push(abs);
    } catch {
      // ignore
    }
  }
  return out;
}

function listExecutionArtifactsUnderRuns(execution_id: string) {
  const runsDir = path.join(process.cwd(), "runs");
  if (!fs.existsSync(runsDir)) return [] as string[];

  const out: string[] = [];
  for (const ent of fs.readdirSync(runsDir, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue;
    const dir = ent.name;
    if (dir === "approvals" || dir === "prestate") continue;

    const dirAbs = path.join(runsDir, dir);
    const matches = listMatchingFilesInDir(dirAbs, (name) => name.startsWith(`${execution_id}.`) || name === `${execution_id}.json`);
    out.push(...matches);
  }

  return out.sort((a, b) => a.localeCompare(b));
}

function writeJsonFile(absPath: string, value: unknown, opts: { redact: boolean }) {
  mkdirp(path.dirname(absPath));
  const out = opts.redact ? redactJson(value) : value;
  fs.writeFileSync(absPath, stableJsonStringify(out), "utf8");
}

function copyFile(absSrc: string, absDst: string, opts: { redact: boolean }) {
  mkdirp(path.dirname(absDst));

  const lower = path.basename(absSrc).toLowerCase();
  if (opts.redact && lower.endsWith(".json")) {
    const parsed = readJsonIfExists(absSrc);
    if (parsed !== null) {
      writeJsonFile(absDst, parsed, opts);
      return;
    }
  }

  fs.copyFileSync(absSrc, absDst);
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

function writeVerifyScript(absPath: string) {
  const text = [
    "import fs from 'node:fs';",
    "import path from 'node:path';",
    "import crypto from 'node:crypto';",
    "",
    "function sha256(buf){return crypto.createHash('sha256').update(buf).digest('hex');}",
    "function sha256File(p){return sha256(fs.readFileSync(p));}",
    "function stableJsonStringify(value){",
    "  const stable=(v)=>{",
    "    if(v===null||v===undefined) return v;",
    "    if(Array.isArray(v)) return v.map(stable);",
    "    if(typeof v!=='object') return v;",
    "    const keys=Object.keys(v).sort();",
    "    const out={};",
    "    for(const k of keys) out[k]=stable(v[k]);",
    "    return out;",
    "  };",
    "  return JSON.stringify(stable(value), null, 2) + '\\n';",
    "}",
    "function toPosixRel(p){return String(p).replace(/\\\\/g,'/');}",
    "function listFilesRecursive(dirAbs){",
    "  const out=[];",
    "  const walk=(abs,rel)=>{",
    "    for(const ent of fs.readdirSync(abs,{withFileTypes:true})){",
    "      const childAbs=path.join(abs,ent.name);",
    "      const childRel=rel?(`${rel}/${ent.name}`):ent.name;",
    "      if(ent.isDirectory()) walk(childAbs,childRel);",
    "      else if(ent.isFile()) out.push(childRel);",
    "    }",
    "  };",
    "  walk(dirAbs,'');",
    "  return out.map(toPosixRel).sort((a,b)=>a.localeCompare(b));",
    "}",
    "",
    "function usage(msg){",
    "  if(msg) console.error('Error: '+msg);",
    "  console.error('Usage: node verify.js [bundle_dir] [--strict] [--json]');",
    "  console.error('Exit codes: 0 ok | 2 usage | 3 verify failed | 1 internal');",
    "}",
    "",
    "const args=process.argv.slice(2);",
    "let strict=false;",
    "let jsonOnly=false;",
    "let dirArg=null;",
    "for(let i=0;i<args.length;i+=1){",
    "  const a=args[i];",
    "  if(a==='--strict'){strict=true;continue;}",
    "  if(a==='--json'){jsonOnly=true;continue;}",
    "  if(a && a.startsWith('--')){usage('Unknown flag: '+a);process.exit(2);}",
    "  if(!dirArg){dirArg=a;continue;}",
    "  usage('Unexpected arg: '+a);process.exit(2);",
    "}",
    "",
    "const root=path.resolve(process.cwd(),dirArg||'.');",
    "const hashesPath=path.join(root,'hashes.json');",
    "const manifestPath=path.join(root,'manifest.json');",
    "const roothashPath=path.join(root,'roothash.txt');",
    "",
    "const result={",
    "  kind:'AuditBundleVerification',",
    "  ok:false,",
    "  bundle_root: toPosixRel(root),",
    "  execution_id:null,",
    "  schema_version:null,",
    "  roothash_file: null,",
    "  roothash_computed: null,",
    "  roothash_ok: null,",
    "  files_expected:0,",
    "  files_checked:0,",
    "  missing:[],",
    "  mismatched:[],",
    "  extra:[],",
    "  errors:[],",
    "};",
    "",
    "try{",
    "  if(!fs.existsSync(root) || !fs.statSync(root).isDirectory()){",
    "    usage('Not a directory: '+root);",
    "    process.exit(2);",
    "  }",
    "  if(!fs.existsSync(hashesPath)) result.errors.push('Missing hashes.json');",
    "  if(!fs.existsSync(manifestPath)) result.errors.push('Missing manifest.json');",
    "  if(result.errors.length){",
    "    if(!jsonOnly) console.error('[FAIL] '+result.errors.join('; '));",
    "    console.log(JSON.stringify(result));",
    "    process.exit(3);",
    "  }",
    "  const hashes=JSON.parse(fs.readFileSync(hashesPath,'utf8'));",
    "  const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));",
    "  result.execution_id = (manifest && typeof manifest.execution_id==='string') ? manifest.execution_id : null;",
    "  result.schema_version = (manifest && typeof manifest.schema_version==='string') ? manifest.schema_version : null;",
    "  if(!hashes || typeof hashes!=='object' || Array.isArray(hashes)){",
    "    result.errors.push('hashes.json must be an object mapping relPath -> sha256:HEX');",
    "  }",
    "  const expectedFiles = Object.keys(hashes||{}).sort((a,b)=>a.localeCompare(b));",
    "  result.files_expected = expectedFiles.length;",
    "  for(const rel of expectedFiles){",
    "    const exp = String(hashes[rel]||'');",
    "    const abs = path.join(root, String(rel).replace(/\\//g, path.sep));",
    "    if(!fs.existsSync(abs) || !fs.statSync(abs).isFile()){result.missing.push(rel);continue;}",
    "    const m = exp.match(/^sha256:([0-9a-fA-F]{64})$/);",
    "    if(!m){result.errors.push('Invalid hash format for '+rel+': '+exp);continue;}",
    "    const got = sha256File(abs);",
    "    result.files_checked += 1;",
    "    if(got.toLowerCase() !== m[1].toLowerCase()){",
    "      result.mismatched.push({rel, expected: 'sha256:'+m[1].toLowerCase(), got: 'sha256:'+got.toLowerCase()});",
    "    }",
    "  }",
    "  if(strict){",
    "    const present = new Set(listFilesRecursive(root));",
    "    for(const rel of expectedFiles) present.delete(rel);",
    "    // hashes.json is intentionally excluded from hashes",
    "    present.delete('hashes.json');",
    "    // roothash.txt is an anchoring convenience and is NOT part of hashes.json",
    "    present.delete('roothash.txt');",
    "    const extra = Array.from(present).sort((a,b)=>a.localeCompare(b));",
    "    if(extra.length) result.extra = extra;",
    "  }",
    "  if(fs.existsSync(roothashPath) && fs.statSync(roothashPath).isFile()){",
    "    try{",
    "      const file = String(fs.readFileSync(roothashPath,'utf8')||'').trim();",
    "      result.roothash_file = file || null;",
    "      const computed = sha256(Buffer.from(stableJsonStringify({ manifest, hashes }), 'utf8'));",
    "      result.roothash_computed = computed;",
    "      result.roothash_ok = (file && file.toLowerCase() === computed.toLowerCase()) ? true : false;",
    "      if(file && result.roothash_ok === false){",
    "        result.errors.push('roothash.txt mismatch');",
    "      }",
    "    }catch(e){",
    "      result.errors.push('Failed to verify roothash.txt: '+String(e&&e.message||e));",
    "    }",
    "  }",
    "  result.ok = result.errors.length===0 && result.missing.length===0 && result.mismatched.length===0 && (!strict || result.extra.length===0);",
    "  if(!jsonOnly){",
    "    console.error('['+(result.ok?'OK':'FAIL')+'] audit bundle verify');",
    "    console.error('  files_checked: '+result.files_checked+'/'+result.files_expected);",
    "    if(result.missing.length) console.error('  missing: '+result.missing.length);",
    "    if(result.mismatched.length) console.error('  mismatched: '+result.mismatched.length);",
    "    if(strict && result.extra.length) console.error('  extra: '+result.extra.length);",
    "    if(result.errors.length) console.error('  errors: '+result.errors.join('; '));",
    "  }",
    "  console.log(JSON.stringify(result));",
    "  process.exit(result.ok ? 0 : 3);",
    "}catch(e){",
    "  if(!jsonOnly) console.error('Internal error:', String(e&&e.stack||e));",
    "  result.errors.push(String(e&&e.message||e));",
    "  console.log(JSON.stringify(result));",
    "  process.exit(1);",
    "}",
    "",
  ].join("\n");

  fs.writeFileSync(absPath, text, "utf8");
}

async function writeZipFromDirectory(opts: { dirAbs: string; zipAbs: string }) {
  const zipfile = new yazl.ZipFile();

  // Deterministic entry ordering and timestamps.
  const fixedDate = new Date("2000-01-01T00:00:00.000Z");

  const files = listFilesRecursive(opts.dirAbs)
    .map((abs) => ({
      abs,
      rel: path.relative(opts.dirAbs, abs).replace(/\\/g, "/"),
    }))
    .sort((a, b) => a.rel.localeCompare(b.rel));

  for (const f of files) {
    zipfile.addFile(f.abs, f.rel, { mtime: fixedDate, mode: 0o644 });
  }

  await new Promise<void>((resolve, reject) => {
    mkdirp(path.dirname(opts.zipAbs));
    const out = fs.createWriteStream(opts.zipAbs);
    zipfile.outputStream.pipe(out);
    zipfile.outputStream.on("error", reject);
    out.on("error", reject);
    out.on("close", () => resolve());
    zipfile.end();
  });
}

export type AuditExecutionExportResult = {
  kind: "AuditExecutionExportResult";
  schema_version: "15.1";
  execution_id: string;
  export_dir: string;
  zip_path: string;
  redact: boolean;
  files_hashed: number;
};

export async function exportAuditExecutionBundle(opts: { execution_id: string; redact?: boolean }): Promise<AuditExecutionExportResult> {
  const execution_id = String(opts.execution_id || "").trim();
  if (!execution_id) throw new Error("execution_id required");

  const redact = opts.redact === false ? false : true;

  const receipt = readLastReceiptForExecutionId(execution_id);
  const approvalAbs = path.join(process.cwd(), "runs", "approvals", `${execution_id}.json`);
  const approval = readJsonIfExists(approvalAbs);

  const rollbackAbs = path.join(process.cwd(), "runs", "rollback", `${execution_id}.json`);
  const rollback = readJsonIfExists(rollbackAbs);

  const started_at = (receipt && (receipt.started_at || receipt.created_at)) || (approval && approval.started_at) || null;
  const finished_at = (receipt && receipt.finished_at) || null;
  const status = (receipt && receipt.status) || (approval && approval.status) || "unknown";

  const plan_hash = (receipt && receipt.plan_hash) || (approval && approval.plan_hash) || null;

  const includes = {
    approval: Boolean(approval),
    rollback: Boolean(rollback),
    autonomy: false,
  };

  const baseRoot = path.resolve(process.cwd(), "exports", "audit_exec");
  mkdirp(baseRoot);

  const rootName = `audit_${sanitizeFilePart(execution_id)}`;
  const exportDirAbs = generateUniquePath(path.join(baseRoot, rootName));
  mkdirp(exportDirAbs);

  // Core bundle files
  const manifest = {
    execution_id,
    plan_hash,
    started_at,
    finished_at,
    status,
    includes,
  };
  writeJsonFile(path.join(exportDirAbs, "manifest.json"), manifest, { redact: false });

  writeJsonFile(path.join(exportDirAbs, "receipt.json"), receipt ?? { kind: "ReceiptNotFound", execution_id }, { redact });

  if (approval) {
    writeJsonFile(path.join(exportDirAbs, "approvals.json"), approval, { redact });
    const plan = (approval as any)?.plan ?? null;
    writeJsonFile(
      path.join(exportDirAbs, "plan.json"),
      plan ?? { kind: "PlanUnavailable", reason: "approval.plan missing", execution_id },
      { redact }
    );
  } else {
    writeJsonFile(
      path.join(exportDirAbs, "approvals.json"),
      {
        kind: "ApprovalNotFound",
        reason: "No runs/approvals/<execution_id>.json present",
        execution_id,
      },
      { redact }
    );
    writeJsonFile(
      path.join(exportDirAbs, "plan.json"),
      {
        kind: "PlanUnavailable",
        reason: "No runs/approvals/<execution_id>.json; engine does not persist plans for non-approved runs",
        execution_id,
      },
      { redact }
    );
  }

  writeJsonFile(
    path.join(exportDirAbs, "policy.json"),
    {
      kind: "PolicySummary",
      execution_id,
      policy_code: receipt?.policy_code ?? null,
      policy_denied: receipt?.policy_denied ?? null,
      approval_required: receipt?.approval_required ?? null,
    },
    { redact }
  );

  // Rollback / compensation (optional)
  if (rollback) {
    writeJsonFile(path.join(exportDirAbs, "rollback.json"), rollback, { redact });
  }

  // Prestate
  const prestateOutDir = path.join(exportDirAbs, "prestate");
  const prestateDirAbs = path.join(process.cwd(), "runs", "prestate");
  const prestateFiles = listMatchingFilesInDir(prestateDirAbs, (n) => n.startsWith(`${execution_id}.`) && n.endsWith(".json"));
  for (const abs of prestateFiles.sort((a, b) => a.localeCompare(b))) {
    const relName = path.basename(abs);
    copyFile(abs, path.join(prestateOutDir, relName), { redact });
  }

  // Artifacts under runs/**/<execution_id>*
  const artifactsOutDir = path.join(exportDirAbs, "artifacts");
  const artifacts = listExecutionArtifactsUnderRuns(execution_id);
  for (const abs of artifacts) {
    const relUnderRuns = path.relative(path.join(process.cwd(), "runs"), abs).replace(/\\/g, "/");
    copyFile(abs, path.join(artifactsOutDir, relUnderRuns), { redact });
  }

  // Verifier
  writeVerifyScript(path.join(exportDirAbs, "verify.js"));

  // Hashes (exclude hashes.json itself)
  const allFiles = listFilesRecursive(exportDirAbs)
    .map((abs) => path.relative(exportDirAbs, abs).replace(/\\/g, "/"))
    .filter((rel) => rel !== "hashes.json")
    .sort((a, b) => a.localeCompare(b));

  const hashes: Record<string, string> = {};
  for (const rel of allFiles) {
    const abs = path.join(exportDirAbs, rel.replace(/\//g, path.sep));
    hashes[rel] = `sha256:${sha256File(abs)}`;
  }

  fs.writeFileSync(path.join(exportDirAbs, "hashes.json"), stableJsonStringify(hashes), "utf8");

  // Root hash (hash-of-hashes) for easy anchoring.
  // Intentionally written after hashes.json so roothash.txt is NOT included in hashes.json.
  const rootHash = sha256(Buffer.from(stableJsonStringify({ manifest, hashes }), "utf8"));
  fs.writeFileSync(path.join(exportDirAbs, "roothash.txt"), rootHash + "\n", "utf8");

  // Zip
  const zipAbs = generateUniquePath(path.join(baseRoot, `${rootName}.zip`));
  await writeZipFromDirectory({ dirAbs: exportDirAbs, zipAbs });

  return {
    kind: "AuditExecutionExportResult",
    schema_version: "15.1",
    execution_id,
    export_dir: exportDirAbs.replace(/\\/g, "/"),
    zip_path: zipAbs.replace(/\\/g, "/"),
    redact,
    files_hashed: Object.keys(hashes).length,
  };
}
