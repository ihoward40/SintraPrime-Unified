import fg from "fast-glob";
import path from "node:path";
import fs from "node:fs";

import type { ContextGroup, NormalizedManifest } from "./manifest.js";

function toPosix(p: string) {
  return p.replace(/\\/g, "/");
}

function resolveInsideCwd(cwd: string, rel: string): string {
  const root = path.resolve(cwd);
  const abs = path.resolve(cwd, rel);
  const rootWithSep = root.endsWith(path.sep) ? root : root + path.sep;
  if (!(abs + path.sep).startsWith(rootWithSep) && abs !== root) {
    throw new Error(`Resolved path escapes workspace root: ${rel}`);
  }
  return abs;
}

export type ResolvedContextFile = {
  context_id: string;
  relPath: string;
  absPath: string;
  max_chars_per_file?: number;
};

export async function resolveContextFiles(params: {
  cwd: string;
  manifest: NormalizedManifest;
  allowlist: string[]; // context group ids
}): Promise<{ files: ResolvedContextFile[]; warnings: string[] }> {
  const warnings: string[] = [];

  const groupsById = new Map<string, ContextGroup>();
  for (const g of params.manifest.contexts ?? []) groupsById.set(g.id, g);

  const out: ResolvedContextFile[] = [];
  const seen = new Set<string>();

  const roots = params.manifest.context_roots?.length ? params.manifest.context_roots : ["."];

  for (const groupId of params.allowlist) {
    const g = groupsById.get(groupId);
    if (!g) {
      warnings.push(`CONTEXT_GROUP_MISSING:${groupId}`);
      continue;
    }

    const include = (g.include ?? []).filter(Boolean);
    if (!include.length) {
      warnings.push(`CONTEXT_GROUP_EMPTY:${groupId}`);
      continue;
    }

    const exclude = (g.exclude ?? []).filter(Boolean);

    const includePatterns: string[] = [];
    const ignorePatterns: string[] = [];

    for (const r of roots) {
      const rootPrefix = r === "." ? "" : `${toPosix(r).replace(/\/$/, "")}/`;
      for (const p of include) includePatterns.push(`${rootPrefix}${p}`);
      for (const p of exclude) ignorePatterns.push(`${rootPrefix}${p}`);
    }

    const matches: string[] = await fg(includePatterns, {
      cwd: params.cwd,
      onlyFiles: true,
      dot: true,
      unique: true,
      followSymbolicLinks: false,
      ignore: ignorePatterns,
      suppressErrors: true,
    });

    const sorted = matches.map(toPosix).sort((a: string, b: string) => a.localeCompare(b));

    for (const relPath of sorted) {
      if (seen.has(relPath)) continue;
      seen.add(relPath);

      const absPath = resolveInsideCwd(params.cwd, relPath);
      try {
        const st = fs.statSync(absPath);
        if (!st.isFile()) continue;
      } catch {
        warnings.push(`CONTEXT_FILE_MISSING:${relPath}`);
        continue;
      }

      out.push({
        context_id: groupId,
        relPath,
        absPath,
        max_chars_per_file: g.max_chars_per_file,
      });
    }
  }

  // Global deterministic ordering.
  out.sort((a, b) => a.relPath.localeCompare(b.relPath));

  return { files: out, warnings };
}
