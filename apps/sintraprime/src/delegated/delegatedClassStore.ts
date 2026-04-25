import fs from "node:fs";
import path from "node:path";

import type { DelegatedClassDefinition } from "./delegatedTypes.js";

function ensureDir(p: string) {
  fs.mkdirSync(p, { recursive: true });
  return p;
}

function readJsonSafe(p: string): any | null {
  try {
    if (!fs.existsSync(p)) return null;
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

function parseTsFromFilename(file: string): number {
  // <id>.YYYY-MM-DDTHH-MM-SS-sssZ.json (colons/dots replaced)
  const m = file.match(/\.(\d{4}-\d{2}-\d{2}T[^.]+Z)\.json$/i);
  if (!m) return -1;
  const iso = m[1]!.replace(/-/g, ":").replace(/Z$/, "Z");
  // We can't reliably reverse the replacement, so treat filename order as fallback.
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? t : -1;
}

export function delegatedClassesDir() {
  return ensureDir(path.join(process.cwd(), "runs", "delegated-classes"));
}

export function listDelegatedClassFiles(): string[] {
  const dir = delegatedClassesDir();
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  files.sort((a, b) => a.localeCompare(b));
  return files.map((f) => path.join(dir, f));
}

export function listDelegatedClassIds(): string[] {
  const files = listDelegatedClassFiles();
  const ids = new Set<string>();
  for (const full of files) {
    const base = path.basename(full);
    const m = base.match(/^(.+?)(?:\.[0-9]{4}-[0-9]{2}-[0-9]{2}T.+Z)?\.json$/i);
    if (m?.[1]) ids.add(m[1]);
  }
  return Array.from(ids).sort((a, b) => a.localeCompare(b));
}

export function readLatestDelegatedClassDefinition(class_id: string): DelegatedClassDefinition | null {
  const dir = delegatedClassesDir();
  const candidates = fs
    .readdirSync(dir)
    .filter((f) => f === `${class_id}.json` || (f.startsWith(`${class_id}.`) && f.endsWith(".json")))
    .map((f) => path.join(dir, f));

  if (!candidates.length) return null;

  const parsed = candidates
    .map((p) => ({ p, json: readJsonSafe(p) }))
    .filter((x) => x.json && typeof x.json === "object")
    .map((x) => {
      const createdAt = typeof x.json.created_at === "string" ? x.json.created_at : "";
      const t = new Date(createdAt).getTime();
      const tf = parseTsFromFilename(path.basename(x.p));
      return { p: x.p, json: x.json as DelegatedClassDefinition, t: Number.isFinite(t) ? t : tf };
    });

  if (!parsed.length) return null;

  parsed.sort((a, b) => {
    if (a.t !== b.t) return a.t - b.t;
    return a.p.localeCompare(b.p);
  });

  return parsed.slice(-1)[0]!.json;
}

export function listLatestDelegatedClasses(): DelegatedClassDefinition[] {
  const ids = listDelegatedClassIds();
  const out: DelegatedClassDefinition[] = [];
  for (const id of ids) {
    const def = readLatestDelegatedClassDefinition(id);
    if (def) out.push(def);
  }
  out.sort((a, b) => a.class_id.localeCompare(b.class_id));
  return out;
}

export function writeDelegatedClassDefinition(args: { record: DelegatedClassDefinition; override: boolean }) {
  const dir = delegatedClassesDir();
  const canonical = path.join(dir, `${args.record.class_id}.json`);

  if (!args.override) {
    if (fs.existsSync(canonical)) {
      return { path: canonical, wrote: false };
    }
    fs.writeFileSync(canonical, JSON.stringify(args.record, null, 2) + "\n", "utf8");
    return { path: canonical, wrote: true };
  }

  const ts = args.record.created_at.replace(/[:.]/g, "-");
  const versioned = path.join(dir, `${args.record.class_id}.${ts}.json`);
  fs.writeFileSync(versioned, JSON.stringify(args.record, null, 2) + "\n", "utf8");
  return { path: versioned, wrote: true };
}
