import { normalizeCommand } from "../dsl/normalizeCommand.js";
import { parseDomainPrefix } from "../domains/parseDomainPrefix.js";

import {
  listLatestDelegatedClasses,
  readLatestDelegatedClassDefinition,
  writeDelegatedClassDefinition,
} from "../delegated/delegatedClassStore.js";
import {
  getDelegationStatus,
  writeDelegatedApproval,
  writeDelegatedRevocation,
} from "../delegated/delegatedApprovalStore.js";
import type {
  DelegatedApprovalRecord,
  DelegatedClassDefinition,
  DelegatedRevocationRecord,
} from "../delegated/delegatedTypes.js";
import { promotionsDir, readPromotion } from "../autonomy/promotionStore.js";
import fs from "node:fs";
import path from "node:path";
import { patternMatchesCommand } from "../delegated/patternMatch.js";
import { nowIso as fixedNowIso } from "../utils/clock.js";
import { enforceCliCredits } from "../credits/enforceCliCredits.js";

function isRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function getArgCommand() {
  const raw = process.argv.slice(2).join(" ").trim();
  if (!raw) throw new Error("Missing command argument");
  return raw;
}

function nowIso() {
  return new Date().toISOString();
}

function parseJsonFromTail(text: string): any {
  const trimmed = text.trim();
  const i = trimmed.indexOf("{");
  if (i === -1) throw new Error("Missing JSON object input");
  const jsonText = trimmed.slice(i);
  return JSON.parse(jsonText);
}

function listPromotionMatchesForClass(pattern: string) {
  const dir = promotionsDir();
  if (!fs.existsSync(dir)) return 0;
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  let n = 0;
  for (const f of files) {
    const fp = f.replace(/\.json$/i, "");
    const rec = readPromotion(fp);
    const cmd = typeof (rec as any)?.command === "string" ? String((rec as any).command) : "";
    if (!cmd) continue;
    if (patternMatchesCommand(pattern, cmd)) n += 1;
  }
  return n;
}

export async function main() {
  const raw = getArgCommand();
  const domainPrefix = parseDomainPrefix(raw);
  const command = domainPrefix?.inner_command ?? raw;
  {
    const threadId = (process.env.THREAD_ID || "local_test_001").trim();
    const now_iso = fixedNowIso();
    const denied = enforceCliCredits({ now_iso, threadId, command: raw, domain_id: domainPrefix?.domain_id ?? null });
    if (denied) {
      console.log(JSON.stringify(denied, null, 0));
      process.exitCode = 1;
      return;
    }
  }
  const trimmed = command.trim();

  try {
    if (/^\/delegate\s+list\s*$/i.test(trimmed)) {
      const classes = listLatestDelegatedClasses();
      const rows = classes.map((c) => {
        const status = getDelegationStatus(c.class_id);
        const matches = listPromotionMatchesForClass(c.pattern);
        return {
          class_id: c.class_id,
          active: status.active,
          status: status.reason,
          matches,
        };
      });
      rows.sort((a, b) => a.class_id.localeCompare(b.class_id));
      console.log(JSON.stringify({ kind: "DelegatedList", classes: rows }, null, 2));
      process.exitCode = 0;
      return;
    }

    const defineMatch = trimmed.match(/^\/delegate\s+class\s+define\s+([\s\S]+)$/i);
    if (defineMatch) {
      const json = parseJsonFromTail(defineMatch[1]!);
      if (!isRecord(json)) throw new Error("Class definition must be a JSON object");

      const record: DelegatedClassDefinition = {
        class_id: String((json as any).class_id ?? "").trim(),
        pattern: normalizeCommand(String((json as any).pattern ?? "")),
        capabilities: Array.isArray((json as any).capabilities)
          ? (json as any).capabilities.map((x: any) => String(x)).filter(Boolean)
          : [],
        adapter: String((json as any).adapter ?? "").trim(),
        write: Boolean((json as any).write),
        created_at: typeof (json as any).created_at === "string" ? String((json as any).created_at) : nowIso(),
      };

      if (!record.class_id) throw new Error("class_id is required");
      if (!record.pattern) throw new Error("pattern is required");
      if (!record.adapter) throw new Error("adapter is required");

      const override = Boolean((json as any).override);
      const wrote = writeDelegatedClassDefinition({ record, override });
      console.log(JSON.stringify({ kind: "DelegatedClassDefined", wrote: wrote.wrote, path: wrote.path, record }, null, 2));
      process.exitCode = wrote.wrote ? 0 : 2;
      return;
    }

    const approveMatch = trimmed.match(/^\/delegate\s+approve\s+(\S+)(?:\s+([\s\S]+))?$/i);
    if (approveMatch) {
      const class_id = String(approveMatch[1] ?? "").trim();
      if (!class_id) throw new Error("Usage: /delegate approve <class_id> [json]");

      const def = readLatestDelegatedClassDefinition(class_id);
      if (!def) throw new Error(`Unknown class_id: ${class_id}`);

      const extra = approveMatch[2] ? JSON.parse(approveMatch[2]) : {};
      const approved_by = typeof extra.approved_by === "string" ? extra.approved_by : "operator@local";
      const scope = isRecord(extra.scope) ? extra.scope : {};

      const rec: DelegatedApprovalRecord = {
        class_id,
        approved_by,
        scope: {
          autonomy_mode: typeof scope.autonomy_mode === "string" ? scope.autonomy_mode : "APPROVAL_GATED_AUTONOMY",
          confidence_min: typeof scope.confidence_min === "number" ? scope.confidence_min : 90,
          promotion_required: scope.promotion_required !== false,
        },
        approved_at: typeof extra.approved_at === "string" ? extra.approved_at : nowIso(),
      };

      const file = writeDelegatedApproval(rec);
      console.log(JSON.stringify({ kind: "DelegatedApproved", path: file, approval: rec }, null, 2));
      process.exitCode = 0;
      return;
    }

    const revokeMatch = trimmed.match(/^\/delegate\s+revoke\s+(\S+)(?:\s+([\s\S]+))?$/i);
    if (revokeMatch) {
      const class_id = String(revokeMatch[1] ?? "").trim();
      if (!class_id) throw new Error("Usage: /delegate revoke <class_id> [json]");

      const extra = revokeMatch[2] ? JSON.parse(revokeMatch[2]) : {};
      const revoked_by = typeof extra.revoked_by === "string" ? extra.revoked_by : "operator@local";
      const reason = typeof extra.reason === "string" ? extra.reason : "operator_revoked";

      const rec: DelegatedRevocationRecord = {
        class_id,
        revoked_by,
        revoked_at: typeof extra.revoked_at === "string" ? extra.revoked_at : nowIso(),
        reason,
      };

      const file = writeDelegatedRevocation(rec);
      console.log(JSON.stringify({ kind: "DelegatedRevoked", path: file, revocation: rec }, null, 2));
      process.exitCode = 0;
      return;
    }

    const showMatch = trimmed.match(/^\/delegate\s+class\s+show\s+(\S+)\s*$/i);
    if (showMatch) {
      const class_id = String(showMatch[1] ?? "").trim();
      const def = readLatestDelegatedClassDefinition(class_id);
      if (!def) throw new Error(`Unknown class_id: ${class_id}`);
      const status = getDelegationStatus(class_id);
      console.log(JSON.stringify({ kind: "DelegatedClass", definition: def, status }, null, 2));
      process.exitCode = 0;
      return;
    }

    throw new Error(
      "Usage: /delegate class define <json> | /delegate class show <class_id> | /delegate approve <class_id> [json] | /delegate revoke <class_id> [json] | /delegate list"
    );
  } catch (err: any) {
    process.exitCode = 1;
    console.error(err?.message ? String(err.message) : String(err));
  }
}

// eslint-disable-next-line @typescript-eslint/no-floating-promises
main();
