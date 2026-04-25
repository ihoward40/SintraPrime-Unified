export type PolicySeverity = "deny" | "require_approval" | "throttle" | "allow";

export type PolicyExplainEntry = {
  code: string;
  title: string;
  severity: PolicySeverity;
  meaning: string;
  how_to_fix: string[];
  related_codes?: string[];
  docs_ref?: string;
};

// Locked registry: stable codes, stable titles.
export const POLICY_CODES: Record<string, PolicyExplainEntry> = {
  NOTION_LIVE_REQUIRES_READ_ONLY: {
    code: "NOTION_LIVE_REQUIRES_READ_ONLY",
    title: "Live Notion operations must be read-only",
    severity: "deny",
    meaning:
      "This plan targets a live Notion adapter and includes a step that is not marked read_only=true.",
    how_to_fix: [
      "Mark the step as read_only:true and use notion.live.read.* actions",
      "If this is a write, route it through ApprovalRequired and use the write adapter explicitly",
      "Ensure method is GET/HEAD for read-only operations",
    ],
    related_codes: ["APPROVAL_REQUIRED", "DOMAIN_NOT_ALLOWED"],
    docs_ref: "docs/policy-codes.md#NOTION_LIVE_REQUIRES_READ_ONLY",
  },
  PROD_WRITE_CONFIRMATION_REQUIRED: {
    code: "PROD_WRITE_CONFIRMATION_REQUIRED",
    title: "Production writes require explicit confirmation",
    severity: "deny",
    meaning:
      "The environment is production and a write-like method/step was requested without CONFIRM_PROD=1.",
    how_to_fix: [
      "Set CONFIRM_PROD=1 only for the single run you intend to execute",
      "Prefer approval-gated writes rather than direct writes in production",
      "Use /policy simulate first to confirm the plan outcome",
    ],
    related_codes: ["APPROVAL_REQUIRED"],
    docs_ref: "docs/policy-codes.md#PROD_WRITE_CONFIRMATION_REQUIRED",
  },
  CONFIDENCE_TOO_LOW: {
    code: "CONFIDENCE_TOO_LOW",
    title: "Confidence too low to execute write-capable steps",
    severity: "deny",
    meaning: "The fingerprint's confidence score is at or below the enforcement threshold, so write-capable steps are blocked.",
    how_to_fix: [
      "Run in READ_ONLY_AUTONOMY and ensure all steps are marked read_only:true",
      "Investigate recent policy denials, throttles, or rollbacks that reduced confidence",
      "If this is expected, requalify the fingerprint via operator controls",
    ],
    related_codes: ["PROBATION_READ_ONLY_ENFORCED", "REQUALIFICATION_BLOCKED", "AUTONOMY_APPROVAL_REQUIRED"],
    docs_ref: "docs/policy-codes.md#CONFIDENCE_TOO_LOW",
  },
  PROBATION_READ_ONLY_ENFORCED: {
    code: "PROBATION_READ_ONLY_ENFORCED",
    title: "Probation enforces read-only execution",
    severity: "deny",
    meaning:
      "The fingerprint is in PROBATION requalification state, so every step must be explicitly marked read_only:true.",
    how_to_fix: [
      "Mark every step as read_only:true",
      "Use read-only adapters/actions during probation to accumulate clean successes",
      "Wait for requalification to recommend ELIGIBLE, then activate via /autonomy requalify activate <fingerprint>",
    ],
    related_codes: ["REQUALIFICATION_BLOCKED", "CONFIDENCE_TOO_LOW"],
    docs_ref: "docs/policy-codes.md#PROBATION_READ_ONLY_ENFORCED",
  },
};
