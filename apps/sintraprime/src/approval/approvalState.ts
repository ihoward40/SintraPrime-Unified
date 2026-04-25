import fs from "node:fs";
import path from "node:path";

export type ApprovalState = {
  execution_id: string;
  created_at: string;
  status: "awaiting_approval" | "rejected";
  rejected_at?: string;
  rejection_reason?: string;
  plan_hash: string;
  // Tier-X: record skills lock hash for deterministic governance on resume.
  skills_lock_sha256?: string;
  // Tier-X: record skill-gate decision inputs/outputs for audit and deterministic resume checks.
  skills_checked?: string[];
  skills_gate_decision?: "ALLOW" | "DENY" | "APPROVAL_REQUIRED";
  skills_gate_reasons?: { code: "SKILL_REVOKED" | "SKILL_DISABLED" | "SKILL_EXPERIMENTAL"; skill: string; detail?: string }[];
  // Tier-20/21: store the originating command for deterministic policy re-checks.
  command?: string;
  // Tier-21: domain context for scoped approvals.
  domain_id?: string;
  // Tier-21: audit-friendly original command when wrapped (e.g. "/domain X ...").
  original_command?: string;
  // Optional signal for Tier-10.6 batch approvals.
  kind?: "ApprovalRequiredBatch";
  // Enough information to deterministically resume without re-planning.
  mode: "phased" | "legacy";
  plan: unknown;
  // Tier-10.6: batch execution after one approval.
  pending_step_ids?: string[];
  prestates?: Record<string, { snapshot: unknown; fingerprint: string }>;
  phases_planned?: string[];
  phases_executed?: string[];
  next_phase_id?: string | null;
  artifacts?: unknown;
  resolved_capabilities?: Record<string, string>;
  steps?: unknown[];
  started_at?: string;
};

function approvalsDir() {
  return path.join(process.cwd(), "runs", "approvals");
}

export function approvalStatePath(executionId: string) {
  return path.join(approvalsDir(), `${executionId}.json`);
}

export function writeApprovalState(state: ApprovalState) {
  fs.mkdirSync(approvalsDir(), { recursive: true });
  fs.writeFileSync(approvalStatePath(state.execution_id), JSON.stringify(state, null, 2), {
    encoding: "utf8",
  });
}

export function readApprovalState(executionId: string): ApprovalState {
  const p = approvalStatePath(executionId);
  const text = fs.readFileSync(p, "utf8");
  return JSON.parse(text) as ApprovalState;
}
