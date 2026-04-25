import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
import { sha256HexUtf8 } from "./stableJson.js";

export const AutoPrimeModeSchema = z.enum(["SAFE", "SANDBOX_RISKY"]);
export type AutoPrimeMode = z.infer<typeof AutoPrimeModeSchema>;

// Used by the context loader.
const ContextTypeSchema = z.enum(["file", "text"]);

export const WorkspaceContextSchema = z.object({
  name: z.string().min(1),
  type: ContextTypeSchema,
  path: z.string().min(1).optional(),
  text: z.string().optional(),
  max_chars: z.number().int().positive().optional(),
});

export type WorkspaceContext = z.infer<typeof WorkspaceContextSchema>;

export const ManifestDocSchema = z.object({
  id: z.string().min(1),
  path: z.string().min(1),
  max_chars: z.number().int().positive().optional(),
});

export type ManifestDoc = z.infer<typeof ManifestDocSchema>;

export const WorkspaceManifestV1Schema = z.object({
  version: z.string().min(1),
  defaults: z
    .object({
      mode: AutoPrimeModeSchema.default("SAFE"),
      context_budget_max_chars: z.number().int().positive().default(24000),
    })
    .default({ mode: "SAFE", context_budget_max_chars: 24000 }),
  context: z.object({
    docs: z.array(ManifestDocSchema).default([]),
    allowlists: z.record(z.string(), z.array(z.string().min(1))).default({}),
  }),
});

export const ContextGroupSchema = z.object({
  id: z.string().min(1),
  include: z.array(z.string().min(1)).default([]),
  exclude: z.array(z.string().min(1)).default([]),
  max_chars_per_file: z.number().int().positive().optional(),
});

export type ContextGroup = z.infer<typeof ContextGroupSchema>;

export const WorkspaceManifestV2Schema = z.object({
  version: z.string().min(1),
  defaults: z
    .object({
      mode: AutoPrimeModeSchema.default("SAFE"),
      context_budget_max_chars: z.number().int().positive().default(24000),
      max_files: z.number().int().positive().default(80),
      max_total_bytes: z.number().int().positive().default(750_000),
    })
    .default({ mode: "SAFE", context_budget_max_chars: 24000, max_files: 80, max_total_bytes: 750_000 }),
  context_roots: z.array(z.string().min(1)).default(["."]),
  contexts: z.array(ContextGroupSchema).default([]),
  command_allowlists: z.record(z.string(), z.array(z.string().min(1))).default({}),
});

// Back-compat: accept the earlier manifest_version=1 format we introduced.
const LegacyWorkspaceContextSchema = WorkspaceContextSchema;

const LegacyCommandProfileSchema = z.object({
  match: z.string().min(1),
  allowed_contexts: z.array(z.string().min(1)).default([]),
  mode: AutoPrimeModeSchema.optional(),
});

const LegacyManifestSchema = z.object({
  manifest_version: z.literal(1),
  defaults: z
    .object({
      mode: AutoPrimeModeSchema.default("SAFE"),
      context_budget_max_chars: z.number().int().positive().default(24000),
    })
    .default({ mode: "SAFE", context_budget_max_chars: 24000 }),
  contexts: z.array(LegacyWorkspaceContextSchema).default([]),
  commands: z.array(LegacyCommandProfileSchema).default([]),
});

export type NormalizedManifest = {
  manifestPath: string;
  exists: boolean;
  manifest_sha256: string;
  defaults: {
    mode: AutoPrimeMode;
    context_budget_max_chars: number;
    max_files: number;
    max_total_bytes: number;
  };
  context_roots: string[];
  contexts: ContextGroup[];
  command_allowlists: Record<string, string[]>;
};

export function loadWorkspaceManifest(cwd: string): NormalizedManifest {
  const manifestPath = path.join(cwd, "workspace_manifest.json");
  if (!fs.existsSync(manifestPath)) {
    return {
      manifestPath,
      exists: false,
      manifest_sha256: sha256HexUtf8(""),
      defaults: { mode: "SAFE", context_budget_max_chars: 24000, max_files: 80, max_total_bytes: 750_000 },
      context_roots: ["."],
      contexts: [],
      command_allowlists: { "*": [] },
    };
  }

  const rawText = fs.readFileSync(manifestPath, "utf8");
  const rawJson = JSON.parse(rawText);

  // Prefer v2 format (context-groups + globs).
  const parsedV2 = WorkspaceManifestV2Schema.safeParse(rawJson);
  if (parsedV2.success) {
    return {
      manifestPath,
      exists: true,
      manifest_sha256: sha256HexUtf8(rawText),
      defaults: parsedV2.data.defaults,
      context_roots: parsedV2.data.context_roots,
      contexts: parsedV2.data.contexts,
      command_allowlists: parsedV2.data.command_allowlists,
    };
  }

  // Prefer the commandId-keyed format.
  const parsedV1 = WorkspaceManifestV1Schema.safeParse(rawJson);
  if (parsedV1.success) {
    const contexts: ContextGroup[] = (parsedV1.data.context.docs ?? []).map((d) => ({
      id: d.id,
      include: [d.path],
      exclude: [],
      max_chars_per_file: d.max_chars,
    }));
    return {
      manifestPath,
      exists: true,
      manifest_sha256: sha256HexUtf8(rawText),
      defaults: {
        mode: parsedV1.data.defaults.mode,
        context_budget_max_chars: parsedV1.data.defaults.context_budget_max_chars,
        max_files: 80,
        max_total_bytes: 750_000,
      },
      context_roots: ["."],
      contexts,
      command_allowlists: parsedV1.data.context.allowlists,
    };
  }

  // Legacy support (best-effort): treat contexts as docs.
  const legacy = LegacyManifestSchema.parse(rawJson);
  const docs: ManifestDoc[] = legacy.contexts
    .filter((c) => c.type === "file" && typeof c.path === "string" && c.path.trim())
    .map((c) => ({ id: c.name, path: c.path!, max_chars: c.max_chars }));

  const contexts: ContextGroup[] = docs.map((d) => ({
    id: d.id,
    include: [d.path],
    exclude: [],
    max_chars_per_file: d.max_chars,
  }));

  // NOTE: legacy commands are regex matches; they don't map cleanly to commandId.
  // We preserve them as allowlist entries keyed by the regex string (so operators can migrate gradually).
  const allowlists: Record<string, string[]> = { "*": [] };
  for (const cmd of legacy.commands ?? []) {
    allowlists[cmd.match] = cmd.allowed_contexts;
  }

  return {
    manifestPath,
    exists: true,
    manifest_sha256: sha256HexUtf8(rawText),
    defaults: {
      mode: legacy.defaults.mode,
      context_budget_max_chars: legacy.defaults.context_budget_max_chars,
      max_files: 80,
      max_total_bytes: 750_000,
    },
    context_roots: ["."],
    contexts,
    command_allowlists: allowlists,
  };
}

export function resolveAllowlistByCommandId(
  manifest: NormalizedManifest,
  commandId: string
): { allowlist: string[]; matchedKey: string; warnings: string[] } {
  const warnings: string[] = [];
  const allowlists = manifest.command_allowlists ?? {};

  if (commandId === "unknown" && String(process.env.SINTRA_ALLOW_UNKNOWN_COMMANDID ?? "").trim() !== "YES") {
    warnings.push("COMMANDID_UNKNOWN_REFUSED");
    return { allowlist: [], matchedKey: "(refused)", warnings };
  }

  const direct = allowlists[commandId];
  if (Array.isArray(direct)) {
    return { allowlist: direct, matchedKey: commandId, warnings };
  }

  const star = allowlists["*"];
  if (Array.isArray(star)) {
    warnings.push("ALLOWLIST_FALLBACK_STAR");
    return { allowlist: star, matchedKey: "*", warnings };
  }

  warnings.push("ALLOWLIST_MISSING");
  return { allowlist: [], matchedKey: "(none)", warnings };
}
