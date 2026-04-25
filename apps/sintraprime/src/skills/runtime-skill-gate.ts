import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export type SkillGateDecision = "ALLOW" | "DENY" | "APPROVAL_REQUIRED";

export type SkillGateReason = {
  code: "SKILL_REVOKED" | "SKILL_DISABLED" | "SKILL_EXPERIMENTAL";
  skill: string;
  detail?: string;
};

export type SkillGateMetaReason = {
  code:
    | "SKILLS_LOCK_MISSING"
    | "SKILLS_LOCK_REQUIRED"
    | "SKILLS_LOCK_INVALID"
    | "SKILLS_LOCK_AMBIGUOUS"
    | "SKILL_NOT_IN_LOCK";
  detail: string;
  skill?: string;
};

export type RuntimeSkillGateResult = {
  decision: SkillGateDecision;
  checked: string[];
  reasons: SkillGateReason[];
  skills_lock_sha256?: string;
  meta?: SkillGateMetaReason[];
};

type SkillsLockEntry = {
  name?: unknown;
  status?: unknown;
  revoked?: unknown;
  disabled?: unknown;
};

type SkillsLockFile = {
  skills?: unknown;
};

function sha256Hex(buf: Buffer) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function normalizeStatus(entry: SkillsLockEntry): "trusted" | "experimental" | "revoked" | "disabled" | "unknown" {
  const raw = typeof entry.status === "string" ? entry.status.toLowerCase().trim() : "";
  const revoked = entry.revoked === true || raw === "revoked";
  const disabled = entry.disabled === true || raw === "disabled";
  if (revoked) return "revoked";
  if (disabled) return "disabled";
  if (raw === "trusted") return "trusted";
  if (raw === "experimental") return "experimental";
  return "unknown";
}

function toName(x: unknown): string | null {
  if (typeof x !== "string") return null;
  const s = x.trim();
  return s ? s : null;
}

function readSkillsLock(rootDir: string): { lock: SkillsLockFile; sha256: string } {
  const lockPath = path.join(rootDir, "skills.lock.json");
  const buf = fs.readFileSync(lockPath);
  const sha = sha256Hex(buf);
  const parsed = JSON.parse(buf.toString("utf8")) as SkillsLockFile;
  return { lock: parsed, sha256: sha };
}

function getLockEntries(lock: SkillsLockFile): SkillsLockEntry[] {
  const skills = (lock as any)?.skills;
  return Array.isArray(skills) ? (skills as SkillsLockEntry[]) : [];
}

export function runtimeSkillGate(args: {
  required_capabilities: string[];
  resolved_capabilities: Record<string, string>;
  is_approved_execution: boolean;
  rootDir?: string;
  skills_lock_required?: boolean;
  allow_experimental?: boolean;
}): RuntimeSkillGateResult {
  const rootDir = args.rootDir ?? process.cwd();
  const lockPath = path.join(rootDir, "skills.lock.json");

  const usedSkills: string[] = [];
  const reasons: SkillGateReason[] = [];
  const meta: SkillGateMetaReason[] = [];

  for (const cap of args.required_capabilities) {
    const provider = args.resolved_capabilities?.[cap];
    if (typeof provider === "string" && provider.trim()) {
      usedSkills.push(provider.trim());
    }
  }

  const usedUnique = Array.from(new Set(usedSkills)).sort();

  if (!fs.existsSync(lockPath)) {
    if (args.skills_lock_required === true || process.env.SKILLS_LOCK_REQUIRED === "1") {
      return {
        decision: "DENY",
        checked: usedUnique,
        reasons: [],
        meta: [
          {
            code: "SKILLS_LOCK_REQUIRED",
            detail: "skills.lock.json not found (set SKILLS_LOCK_REQUIRED=0 to allow without lock)",
          },
        ],
      };
    }

    return {
      decision: "ALLOW",
      checked: usedUnique,
      reasons: [],
      meta: [
        {
          code: "SKILLS_LOCK_MISSING",
          detail: "skills.lock.json not found; runtime skill gate is not enforcing statuses",
        },
      ],
    };
  }

  let lock: SkillsLockFile;
  let sha: string;
  try {
    const read = readSkillsLock(rootDir);
    lock = read.lock;
    sha = read.sha256;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      decision: "DENY",
      checked: usedUnique,
      reasons: [],
      meta: [{ code: "SKILLS_LOCK_INVALID", detail: `skills.lock.json unreadable/invalid: ${msg}` }],
    };
  }

  const entries = getLockEntries(lock);

  const byName = new Map<string, SkillsLockEntry[]>();
  for (const ent of entries) {
    const name = toName((ent as any)?.name);
    if (!name) continue;
    const arr = byName.get(name) ?? [];
    arr.push(ent);
    byName.set(name, arr);
  }

  let hasDeny = false;
  let needsApproval = false;

  for (const provider of usedUnique) {
    const matches = byName.get(provider) ?? [];

    if (matches.length === 0) {
      meta.push({
        code: "SKILL_NOT_IN_LOCK",
        detail: `provider '${provider}' not present in skills.lock.json`,
        skill: provider,
      });
      continue;
    }

    if (matches.length > 1) {
      hasDeny = true;
      meta.push({
        code: "SKILLS_LOCK_AMBIGUOUS",
        detail: `multiple lock entries match provider '${provider}'`,
        skill: provider,
      });
      continue;
    }

    const status = normalizeStatus(matches[0]!);

    if (status === "revoked") {
      hasDeny = true;
      reasons.push({
        code: "SKILL_REVOKED",
        skill: provider,
        detail: `provider '${provider}' is revoked`,
      });
      continue;
    }

    if (status === "disabled") {
      hasDeny = true;
      reasons.push({
        code: "SKILL_DISABLED",
        skill: provider,
        detail: `provider '${provider}' is disabled`,
      });
      continue;
    }

    if (status === "experimental") {
      const allowExperimental = args.allow_experimental === true || process.env.SKILLS_ALLOW_EXPERIMENTAL === "1";
      if (!allowExperimental && !args.is_approved_execution) {
        needsApproval = true;
        reasons.push({
          code: "SKILL_EXPERIMENTAL",
          skill: provider,
          detail: `provider '${provider}' is experimental and requires approval`,
        });
      } else {
        reasons.push({
          code: "SKILL_EXPERIMENTAL",
          skill: provider,
          detail: `provider '${provider}' is experimental`,
        });
      }
      continue;
    }
  }

  const decision: SkillGateDecision = hasDeny ? "DENY" : needsApproval ? "APPROVAL_REQUIRED" : "ALLOW";

  return {
    decision,
    reasons,
    skills_lock_sha256: sha,
    checked: usedUnique,
    meta: meta.length ? meta : undefined,
  };
}
