import { POLICY_CODES } from "../policy/policyCodes.js";

export type PolicyExplainOutput = {
  kind: "PolicyExplain";
  code: string;
  title: string;
  severity: "deny" | "require_approval" | "throttle" | "allow";
  meaning: string;
  how_to_fix: string[];
  related_codes: string[];
  docs_ref: string | null;
};

export function explainPolicyCode(command: string): PolicyExplainOutput {
  // command: "/policy explain <CODE>"
  const parts = String(command ?? "").trim().split(/\s+/);
  const code = parts.slice(2).join(" ").trim();

  if (!code) {
    return {
      kind: "PolicyExplain",
      code: "",
      title: "Missing policy code",
      severity: "deny",
      meaning: "Usage: /policy explain <CODE>",
      how_to_fix: ["Provide a policy denial code, e.g. /policy explain NOTION_LIVE_REQUIRES_READ_ONLY"],
      related_codes: [],
      docs_ref: null,
    };
  }

  const entry = POLICY_CODES[code];
  if (!entry) {
    return {
      kind: "PolicyExplain",
      code,
      title: "Unknown policy code",
      severity: "deny",
      meaning: "This policy code is not registered in the local registry.",
      how_to_fix: [
        "Check spelling/case",
        "Search logs/receipts for the exact code",
        "If this is a new code, add it to src/policy/policyCodes.ts",
      ],
      related_codes: [],
      docs_ref: null,
    };
  }

  return {
    kind: "PolicyExplain",
    code: entry.code,
    title: entry.title,
    severity: entry.severity,
    meaning: entry.meaning,
    how_to_fix: entry.how_to_fix,
    related_codes: Array.isArray(entry.related_codes) ? entry.related_codes : [],
    docs_ref: typeof entry.docs_ref === "string" ? entry.docs_ref : null,
  };
}
