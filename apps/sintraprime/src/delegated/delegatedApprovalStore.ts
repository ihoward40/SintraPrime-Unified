import fs from "node:fs";
import path from "node:path";

import type {
  DelegatedApprovalRecord,
  DelegatedRevocationRecord,
  DelegatedSuspensionRecord,
} from "./delegatedTypes.js";

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

function tsForFilename(iso: string) {
  return iso.replace(/[:.]/g, "-");
}

export function delegatedApprovalsDir() {
  return ensureDir(path.join(process.cwd(), "runs", "delegated-approvals"));
}

export function delegatedRevocationsDir() {
  return ensureDir(path.join(process.cwd(), "runs", "delegated-revocations"));
}

export function delegatedSuspensionsDir() {
  return ensureDir(path.join(process.cwd(), "runs", "delegated-suspensions"));
}

export function writeDelegatedApproval(record: DelegatedApprovalRecord) {
  const dir = delegatedApprovalsDir();
  const file = path.join(dir, `${record.class_id}.${tsForFilename(record.approved_at)}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 2) + "\n", "utf8");
  return file;
}

export function writeDelegatedRevocation(record: DelegatedRevocationRecord) {
  const dir = delegatedRevocationsDir();
  const file = path.join(dir, `${record.class_id}.${tsForFilename(record.revoked_at)}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 2) + "\n", "utf8");
  return file;
}

export function writeDelegatedSuspension(record: DelegatedSuspensionRecord) {
  const dir = delegatedSuspensionsDir();
  const file = path.join(dir, `${record.class_id}.${tsForFilename(record.suspended_at)}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 2) + "\n", "utf8");
  return file;
}

function listDirFiles(dir: string, prefix: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.startsWith(`${prefix}.`) && f.endsWith(".json"));
  files.sort((a, b) => a.localeCompare(b));
  return files.map((f) => path.join(dir, f));
}

function latestByTime<T extends { at: string }>(items: T[]): T | null {
  if (!items.length) return null;
  const withT = items
    .map((x) => {
      const t = new Date(x.at).getTime();
      return { x, t: Number.isFinite(t) ? t : -1 };
    })
    .sort((a, b) => {
      if (a.t !== b.t) return a.t - b.t;
      return 0;
    });
  return withT.slice(-1)[0]!.x;
}

export function readLatestDelegatedApproval(class_id: string): DelegatedApprovalRecord | null {
  const files = listDirFiles(delegatedApprovalsDir(), class_id);
  const parsed = files
    .map((p) => ({ p, json: readJsonSafe(p) }))
    .filter((x) => x.json && typeof x.json === "object")
    .map((x) => ({ at: String((x.json as any).approved_at ?? ""), rec: x.json as DelegatedApprovalRecord }));
  const latest = latestByTime(parsed.map((p) => ({ at: p.at, rec: p.rec }))) as any;
  return latest ? (latest.rec as DelegatedApprovalRecord) : null;
}

export function readLatestDelegatedRevocation(class_id: string): DelegatedRevocationRecord | null {
  const files = listDirFiles(delegatedRevocationsDir(), class_id);
  const parsed = files
    .map((p) => ({ p, json: readJsonSafe(p) }))
    .filter((x) => x.json && typeof x.json === "object")
    .map((x) => ({ at: String((x.json as any).revoked_at ?? ""), rec: x.json as DelegatedRevocationRecord }));
  const latest = latestByTime(parsed.map((p) => ({ at: p.at, rec: p.rec }))) as any;
  return latest ? (latest.rec as DelegatedRevocationRecord) : null;
}

export function readLatestDelegatedSuspension(class_id: string): DelegatedSuspensionRecord | null {
  const files = listDirFiles(delegatedSuspensionsDir(), class_id);
  const parsed = files
    .map((p) => ({ p, json: readJsonSafe(p) }))
    .filter((x) => x.json && typeof x.json === "object")
    .map((x) => ({ at: String((x.json as any).suspended_at ?? ""), rec: x.json as DelegatedSuspensionRecord }));
  const latest = latestByTime(parsed.map((p) => ({ at: p.at, rec: p.rec }))) as any;
  return latest ? (latest.rec as DelegatedSuspensionRecord) : null;
}

export function getDelegationStatus(class_id: string): {
  active: boolean;
  reason: "NOT_APPROVED" | "REVOKED" | "SUSPENDED" | "APPROVED";
  approval: DelegatedApprovalRecord | null;
  suspension: DelegatedSuspensionRecord | null;
  revocation: DelegatedRevocationRecord | null;
} {
  const approval = readLatestDelegatedApproval(class_id);
  const revocation = readLatestDelegatedRevocation(class_id);
  const suspension = readLatestDelegatedSuspension(class_id);

  const approvalAt = approval ? new Date(approval.approved_at).getTime() : -1;
  const revokeAt = revocation ? new Date(revocation.revoked_at).getTime() : -1;
  const suspendAt = suspension ? new Date(suspension.suspended_at).getTime() : -1;

  const times = [
    { kind: "approve" as const, t: Number.isFinite(approvalAt) ? approvalAt : -1 },
    { kind: "revoke" as const, t: Number.isFinite(revokeAt) ? revokeAt : -1 },
    { kind: "suspend" as const, t: Number.isFinite(suspendAt) ? suspendAt : -1 },
  ].sort((a, b) => a.t - b.t);

  const last = times.slice(-1)[0];
  if (!approval) {
    return { active: false, reason: "NOT_APPROVED", approval: null, suspension, revocation };
  }
  if (!last || last.t < 0) {
    return { active: true, reason: "APPROVED", approval, suspension: null, revocation: null };
  }
  if (last.kind === "approve") {
    return { active: true, reason: "APPROVED", approval, suspension, revocation };
  }
  if (last.kind === "revoke" && revokeAt >= approvalAt) {
    return { active: false, reason: "REVOKED", approval, suspension, revocation };
  }
  if (last.kind === "suspend" && suspendAt >= approvalAt) {
    return { active: false, reason: "SUSPENDED", approval, suspension, revocation };
  }

  // Fallback: require a live approval newer than revoke/suspend.
  if (approvalAt >= revokeAt && approvalAt >= suspendAt) {
    return { active: true, reason: "APPROVED", approval, suspension, revocation };
  }
  if (suspendAt >= revokeAt) {
    return { active: false, reason: "SUSPENDED", approval, suspension, revocation };
  }
  return { active: false, reason: "REVOKED", approval, suspension, revocation };
}
