import type { ExecutionPlan, ExecutionStep } from "../schemas/ExecutionPlan.schema.js";
import fs from "node:fs";
import { computePromotionFingerprint } from "../autonomy/promotionFingerprint.js";
import { isDemoted, readPromotion } from "../autonomy/promotionStore.js";
import { evaluateDelegationForPlan } from "../delegated/delegationEngine.js";
import type { DelegationDecision } from "../delegated/delegatedTypes.js";
import { readDomainOverlay } from "../domains/domainRegistry.js";
import { deriveFingerprint } from "../governor/runGovernor.js";
import { readRequalificationState } from "../requalification/requalification.js";
import { readConfidence } from "../confidence/updateConfidence.js";
import { assertUrlSafeForL0, BrowserL0GuardError } from "../browser/l0/ssrfGuards.js";

export type PolicyDenied = {
  kind: "PolicyDenied";
  code: string;
  reason: string;
};

export type ApprovalRequired = {
  kind: "ApprovalRequired";
  code: string;
  reason: string;
  action: string;
  preview: {
    destination: string;
    summary: string;
  };
};

export type PolicyResult =
  | { allowed: true }
  | { allowed: false; denied: PolicyDenied }
  | { allowed: false; requireApproval: true; approval: ApprovalRequired };

export type PolicyResultMeta = {
  // Tier-19
  promotion_fingerprint?: string | null;
  // Tier-20
  delegation?: DelegationDecision | null;
};

export type PolicyResultWithMeta = PolicyResult & PolicyResultMeta;

export type PolicyMeta = {
  phase_id?: string;
  phases_count?: number;
  total_steps_planned?: number;
  // Tier 5.3: write-time approval gate.
  approved_execution_id?: string;
  execution_id?: string;
  // Tier-19: promotion fingerprint uses the originating command string.
  command?: string;
  // Tier-21: trust domain context.
  domain_id?: string;
  // Tier-21: audit-friendly original command string when wrapped.
  original_command?: string;
};

function getAutonomyMode(env: NodeJS.ProcessEnv): string {
  return env.AUTONOMY_MODE || "OFF";
}

function asInt(v: string | undefined, fallback: number): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function deny(code: string, reason: string): PolicyResult {
  return { allowed: false, denied: { kind: "PolicyDenied", code, reason } };
}

function denyBudget(env: NodeJS.ProcessEnv, defaultCode: string, reason: string): PolicyResult {
  const override = String(env.POLICY_BUDGET_DENY_CODE ?? "").trim();
  const code = override || defaultCode;
  return deny(code, reason);
}

function requireApproval(params: {
  code: string;
  reason: string;
  action: string;
  destination: string;
  summary: string;
}): PolicyResult {
  return {
    allowed: false,
    requireApproval: true,
    approval: {
      kind: "ApprovalRequired",
      code: params.code,
      reason: params.reason,
      action: params.action,
      preview: { destination: params.destination, summary: params.summary },
    },
  };
}

function parseCsv(envValue: string | undefined): string[] {
  if (!envValue) return [];
  return envValue
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function isProd(env: NodeJS.ProcessEnv) {
  const e = String(env.ENVIRONMENT ?? "").toLowerCase();
  const n = String(env.NODE_ENV ?? "").toLowerCase();
  return e === "production" || n === "production";
}

function methodIsWrite(method: ExecutionStep["method"]) {
  return method === "POST" || method === "PUT" || method === "PATCH" || method === "DELETE";
}

function methodIsReadOnly(method: ExecutionStep["method"]) {
  return method === "GET" || method === "HEAD";
}

function uniqueHostsFromSteps(steps: ExecutionStep[]): string[] {
  const hosts = new Set<string>();
  for (const step of steps) {
    try {
      hosts.add(new URL(step.url).hostname);
    } catch {
      // ignore here; URL validity is handled elsewhere
    }
  }
  return Array.from(hosts).sort();
}

function parseNumberEnv(envValue: string | undefined): number | null {
  if (!envValue) return null;
  const n = Number(envValue);
  return Number.isFinite(n) ? n : null;
}

function parseUtcHm(envValue: string | undefined): { hour: number; minute: number } | null {
  if (!envValue) return null;
  const m = String(envValue).trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  const hour = Number(m[1]);
  const minute = Number(m[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  return { hour, minute };
}

export function checkPlanPolicy(plan: any, env: NodeJS.ProcessEnv = process.env) {
  const maxSteps = asInt(env.POLICY_MAX_STEPS, 10);
  const maxRuntimeMs = asInt(env.POLICY_MAX_RUNTIME_MS, 30000);

  const steps = plan?.steps || plan?.phases?.flatMap((p: any) => p.steps) || [];

  if (steps.length > maxSteps) {
    return {
      kind: 'PolicyDenied',
      code: String(env.POLICY_BUDGET_DENY_CODE ?? '').trim() || 'BUDGET_MAX_STEPS_EXCEEDED',
      reason: `Plan has ${steps.length} steps; max is ${maxSteps}`
    };
  }

  // Cap per-step timeout (if present)
  for (const s of steps) {
    const t = s?.timeout_ms;
    if (typeof t === 'number' && t > maxRuntimeMs) {
      return {
        kind: 'PolicyDenied',
        code: String(env.POLICY_BUDGET_DENY_CODE ?? '').trim() || 'BUDGET_MAX_RUNTIME_EXCEEDED',
        reason: `Step timeout ${t}ms exceeds policy cap ${maxRuntimeMs}ms`
      };
    }
  }

  // Autonomy mode enforcement is step-scoped (below), but we also block obvious mixed-mode:
  const mode = getAutonomyMode(env);
  if (mode === 'READ_ONLY_AUTONOMY') {
    const hasWrite = steps.some((s: any) => s?.read_only === false);
    if (hasWrite) {
      return {
        kind: 'PolicyDenied',
        code: 'AUTONOMY_READ_ONLY_VIOLATION',
        reason: 'READ_ONLY_AUTONOMY forbids any step with read_only=false'
      };
    }
  }

  // Optional Mode/Limb governance enforcement (operator-driven).
  // This is intentionally opt-in to avoid breaking existing deployments.
  if (env.SINTRAPRIME_MODE_GOVERNANCE_ENFORCE === "1") {
    const declaredMode = String(env.SINTRAPRIME_MODE ?? "").trim();
    const declarationPath = String(env.SINTRAPRIME_MODE_DECLARATION_PATH ?? "").trim();
    const activeLimbs = new Set(parseCsv(env.SINTRAPRIME_ACTIVE_LIMBS));

    if (!declaredMode) {
      return {
        kind: "PolicyDenied",
        code: "MODE_DECLARATION_MISSING",
        reason: "SINTRAPRIME_MODE_GOVERNANCE_ENFORCE=1 requires SINTRAPRIME_MODE",
      };
    }

    if (!declarationPath) {
      return {
        kind: "PolicyDenied",
        code: "MODE_DECLARATION_MISSING",
        reason: "SINTRAPRIME_MODE_GOVERNANCE_ENFORCE=1 requires SINTRAPRIME_MODE_DECLARATION_PATH",
      };
    }

    try {
      if (!fs.existsSync(declarationPath)) {
        return {
          kind: "PolicyDenied",
          code: "MODE_DECLARATION_NOT_FOUND",
          reason: `Mode declaration sheet not found at: ${declarationPath}`,
        };
      }
    } catch {
      return {
        kind: "PolicyDenied",
        code: "MODE_DECLARATION_NOT_FOUND",
        reason: `Mode declaration sheet not found at: ${declarationPath}`,
      };
    }

    if (declaredMode === "FROZEN") {
      return {
        kind: "PolicyDenied",
        code: "MODE_FROZEN",
        reason: "SINTRAPRIME_MODE=FROZEN denies execution",
      };
    }

    const needsNotionWrite = steps.some((s: any) => typeof s?.action === "string" && s.action.startsWith("notion.write."));
    const needsNotionLiveWrite = steps.some((s: any) => s?.action === "notion.live.write");

    if ((needsNotionWrite || needsNotionLiveWrite) && declaredMode !== "SINGLE_RUN_APPROVED") {
      return {
        kind: "PolicyDenied",
        code: "MODE_WRITE_REQUIRES_SINGLE_RUN_APPROVED",
        reason: "Notion write/live-write requires SINTRAPRIME_MODE=SINGLE_RUN_APPROVED",
      };
    }

    if (needsNotionWrite && !activeLimbs.has("notion.write")) {
      return {
        kind: "PolicyDenied",
        code: "LIMB_INACTIVE",
        reason: "Plan requires Notion write but limb 'notion.write' is not ACTIVE",
      };
    }

    if (needsNotionLiveWrite && !activeLimbs.has("notion.live.write")) {
      return {
        kind: "PolicyDenied",
        code: "LIMB_INACTIVE",
        reason: "Plan requires Notion live write but limb 'notion.live.write' is not ACTIVE",
      };
    }
  }

  return null;
}

export function checkPolicy(plan: ExecutionPlan, env: NodeJS.ProcessEnv, clock: Date): PolicyResult {
  return checkPolicyWithMeta(plan, env, clock, undefined);
}

export function checkPolicyWithMeta(
  plan: ExecutionPlan,
  env: NodeJS.ProcessEnv,
  clock: Date,
  meta: PolicyMeta | undefined
): PolicyResultWithMeta {
  const autonomyMode = getAutonomyMode(env);

  // Tier-16: confidence regression enforcement (pre-execution).
  // If confidence is too low, only allow fully read-only plans.
  {
    const command = typeof meta?.command === "string" ? meta.command : "";
    if (command) {
      const fp = deriveFingerprint({ command, domain_id: meta?.domain_id ?? null });
      const confidence = readConfidence(fp).confidence;
      if (confidence <= 0.4) {
        const hasWrite = plan.steps.some((s: any) => s?.read_only === false || methodIsWrite(s?.method));
        if (hasWrite) {
          return {
            allowed: false,
            denied: {
              kind: "PolicyDenied",
              code: "CONFIDENCE_TOO_LOW",
              reason: "confidence <= 0.4 forbids execution of write-capable steps",
            },
            promotion_fingerprint: null,
            delegation: null,
          };
        }
      }
    }
  }

  // Tier-22.1: probation enforcement (policy-level; no writes / approvals).
  // This runs before approval gating so probation cannot silently restore write power.
  {
    const enabled = env.REQUALIFICATION_ENABLED === "1";
    const command = typeof meta?.command === "string" ? meta.command : "";
    if (enabled && command) {
      const fingerprint = deriveFingerprint({ command, domain_id: meta?.domain_id ?? null });
      const state = readRequalificationState(fingerprint);
      if (state && state.state !== "ACTIVE") {
        if (state.state === "PROBATION") {
          const anyNonReadOnly = plan.steps.some((s: any) => s?.read_only !== true);
          if (anyNonReadOnly) {
            return {
              allowed: false,
              denied: {
                kind: "PolicyDenied",
                code: "PROBATION_READ_ONLY_ENFORCED",
                reason: "probation requires all steps to be explicitly read_only:true",
              },
              promotion_fingerprint: null,
              delegation: null,
            };
          }
        } else {
          const hasWrite = plan.steps.some((s: any) => s?.read_only === false || methodIsWrite(s?.method));
          if (hasWrite) {
            const reason = `requalification state=${state.state} forbids write operations`;
            return {
              allowed: false,
              denied: { kind: "PolicyDenied", code: "REQUALIFICATION_BLOCKED", reason },
              promotion_fingerprint: null,
              delegation: null,
            };
          }
        }
      }
    }
  }

  // Tier-21: domain overlay enforcement (overlay can tighten, never loosen).
  {
    const overlay = readDomainOverlay(meta?.domain_id);
    if (overlay?.deny_write === true) {
      const hasWrite = plan.steps.some((s: any) => s?.read_only === false || methodIsWrite(s?.method));
      if (hasWrite) {
        return {
          allowed: false,
          denied: {
            kind: "PolicyDenied",
            code: "DOMAIN_OVERLAY_DENY_WRITE",
            reason: "domain overlay forbids write operations",
          },
          promotion_fingerprint: null,
          delegation: null,
        };
      }
    }
  }

  const promotionFingerprint = (() => {
    try {
      const requiredCaps = Array.isArray((plan as any).required_capabilities)
        ? (plan as any).required_capabilities.filter((c: any) => typeof c === "string")
        : [];
      const adapters = Array.from(new Set(plan.steps.map((s: any) => String(s?.adapter ?? "").trim()).filter(Boolean))).sort();
      const adapter_type = adapters.length ? adapters.join("+") : "unknown";
      const command = typeof (meta as any)?.command === "string" ? String((meta as any).command) : "";
      if (!command) return null;
      return computePromotionFingerprint({
        command,
        capability_set: requiredCaps,
        adapter_type,
      });
    } catch {
      return null;
    }
  })();

  const isPromotedForThisPlan = (() => {
    if (!promotionFingerprint) return false;
    if (isDemoted(promotionFingerprint)) return false;
    return readPromotion(promotionFingerprint) !== null;
  })();

  const delegationDecision: DelegationDecision | null = (() => {
    try {
      if (autonomyMode !== "APPROVAL_GATED_AUTONOMY") return null;
      const command = typeof (meta as any)?.command === "string" ? String((meta as any).command) : "";
      if (!command) return null;
      return evaluateDelegationForPlan({
        plan,
        command,
        autonomy_mode: autonomyMode,
        promoted: isPromotedForThisPlan,
      });
    } catch {
      return null;
    }
  })();

  const promotionMaySkipApprovalGate =
    isPromotedForThisPlan && !(delegationDecision?.matched === true && delegationDecision?.reason === "SUSPENDED");

  const resultMeta: PolicyResultMeta = {
    promotion_fingerprint: promotionFingerprint,
    delegation: delegationDecision,
  };

  const withMeta = (r: PolicyResult): PolicyResultWithMeta => ({
    ...(r as any),
    ...resultMeta,
  });

  const approved =
    meta?.execution_id && meta?.approved_execution_id && meta.execution_id === meta.approved_execution_id;

  // Tier-13: PROPOSE_ONLY/APPROVAL_GATED autonomy.
  // These modes allow planning + queuing approvals but MUST NOT execute write-capable steps.
  if (autonomyMode === "PROPOSE_ONLY_AUTONOMY" || autonomyMode === "APPROVAL_GATED_AUTONOMY") {
    for (const step of plan.steps) {
      if ((step as any).read_only !== true) {
        // In APPROVAL_GATED_AUTONOMY, allow approved executions to proceed.
        if (
          autonomyMode === "APPROVAL_GATED_AUTONOMY" &&
          (approved ||
            promotionMaySkipApprovalGate ||
            (delegationDecision && delegationDecision.active === true && delegationDecision.reason === "OK"))
        ) {
          continue;
        }
        return withMeta(
          requireApproval({
          code: "AUTONOMY_APPROVAL_REQUIRED",
          reason: `${autonomyMode} forbids execution of write-capable steps (approval required)` ,
          action: typeof (step as any).action === "string" ? String((step as any).action) : "unknown",
          destination: (() => {
            try {
              const u = new URL(step.url);
              return `${u.hostname}${u.pathname}`;
            } catch {
              return String(step.url || "unknown");
            }
          })(),
          summary: `${String(step.method || "GET").toUpperCase()} ${String(step.url || "")}`,
          })
        );
      }
    }
  }

  if (autonomyMode === "READ_ONLY_AUTONOMY") {
    for (const step of plan.steps) {
      // In READ_ONLY_AUTONOMY, every step must be explicitly marked read-only.
      if ((step as any).read_only !== true) {
        return withMeta(
          deny(
          "AUTONOMY_READ_ONLY_VIOLATION",
          "READ_ONLY_AUTONOMY forbids execution of write-capable steps"
          )
        );
      }
    }
  }

  // Tier 5.2: phase-aware budget guards (deterministic, no branching).
  const maxPhases = parseNumberEnv(env.POLICY_MAX_PHASES);
  if (maxPhases !== null && meta?.phases_count !== undefined && meta.phases_count > maxPhases) {
    return withMeta(
      denyBudget(
      env,
      "POLICY_MAX_PHASES",
      `plan has ${meta.phases_count} phases; max ${maxPhases}`
      )
    );
  }

  const maxTotalSteps = parseNumberEnv(env.POLICY_MAX_TOTAL_STEPS);
  if (maxTotalSteps !== null && meta?.total_steps_planned !== undefined && meta.total_steps_planned > maxTotalSteps) {
    return withMeta(
      denyBudget(
      env,
      "POLICY_MAX_TOTAL_STEPS",
      `plan has ${meta.total_steps_planned} total steps; max ${maxTotalSteps}`
      )
    );
  }

  // 0) Capability allowlist (Tier 5.1)
  const allowedCaps = parseCsv(env.POLICY_ALLOWED_CAPABILITIES);
  if (allowedCaps.length) {
    const requiredCaps = Array.isArray((plan as any).required_capabilities)
      ? (plan as any).required_capabilities
      : [];
    for (const cap of requiredCaps) {
      if (typeof cap !== "string") {
        return withMeta(deny("POLICY_CAPABILITY_INVALID", "required_capabilities must be string[]"));
      }
      if (!allowedCaps.includes(cap)) {
        return withMeta(deny("POLICY_CAPABILITY_NOT_ALLOWED", `capability ${cap} not allowlisted`));
      }
    }
  }

  // 1) Protocol guard (basic safety)
  for (const step of plan.steps) {
    let url: URL;
    try {
      url = new URL(step.url);
    } catch {
      return withMeta(deny("POLICY_URL_INVALID", `invalid url: ${step.url}`));
    }

    // Tier-10.x: Live Notion safety rails (read-only by default; writes approval-scoped)
    const action = typeof (step as any).action === "string" ? ((step as any).action as string) : "";
    const isNotionLiveEndpoint = url.hostname === "api.notion.com" && url.pathname.startsWith("/v1/");
    const isNotionLiveAction = action.startsWith("notion.live.");
    if (isNotionLiveEndpoint || isNotionLiveAction) {
      const method = String(step.method || "GET").toUpperCase();
      const readOnlyFlag = (step as any).read_only;

      // 1) If it's not explicitly read_only, it MUST be approval_scoped and have prestate.
      if (readOnlyFlag !== true) {
        const approvalScoped = (step as any).approval_scoped;
        if (approvalScoped !== true) {
          return withMeta(
            deny(
            "NOTION_LIVE_REQUIRES_READ_ONLY",
            "Live Notion requires read_only=true unless approval_scoped=true"
            )
          );
        }

        const hasPrestate = !!(step as any).prestate;
        const hasFingerprint = typeof (step as any).prestate_fingerprint === "string" && String((step as any).prestate_fingerprint).trim();
        if (!hasPrestate || !hasFingerprint) {
          return withMeta(
            deny(
            "NOTION_LIVE_WRITE_REQUIRES_PRESTATE",
            "Approval-scoped live writes require prestate + prestate_fingerprint"
            )
          );
        }

        if (method !== "PATCH") {
          return withMeta(
            deny(
            "NOTION_LIVE_WRITE_METHOD_NOT_ALLOWED",
            "Only PATCH allowed for approval-scoped live notion writes"
            )
          );
        }

        // Live writes must be explicitly approved (Tier 10.2) using the same approval token mechanism.
        if (!approved) {
          const destination = `${url.hostname}${url.pathname}`;
          return withMeta(
            requireApproval({
            code: "NOTION_LIVE_WRITE_APPROVAL_REQUIRED",
            reason: "Live Notion writes require explicit approval (Tier 10.2)",
            action,
            destination,
            summary: `PATCH ${url.pathname}`,
            })
          );
        }
      }

      // 2) Read-only method constraints
      if (readOnlyFlag === true) {
        if (method !== "GET" && method !== "HEAD") {
          return withMeta(
            deny(
            "NOTION_LIVE_METHOD_NOT_ALLOWED",
            "Only GET/HEAD allowed for notion.live.read"
            )
          );
        }
      }
    }

    // Tier-XX: Vendor docs capture is a separate evidence lane.
    // It is deny-by-default and requires an explicit host allowlist.
    const isDocsCaptureAction = action === "docs.capture" || action.startsWith("docs.capture.");
    if (isDocsCaptureAction) {
      const method = String(step.method || "GET").toUpperCase();
      const readOnlyFlag = (step as any).read_only;

      if (readOnlyFlag !== true) {
        return withMeta(deny("DOCS_CAPTURE_REQUIRES_READ_ONLY", "docs.capture requires read_only=true"));
      }

      if (method !== "GET" && method !== "HEAD") {
        return withMeta(deny("DOCS_CAPTURE_METHOD_NOT_ALLOWED", "docs.capture only allows GET/HEAD"));
      }

      const allowedHosts = parseCsv(env.DOCS_CAPTURE_ALLOWED_HOSTS);
      if (!allowedHosts.length) {
        return withMeta(
          deny(
            "DOCS_CAPTURE_HOST_NOT_ALLOWED",
            "DOCS_CAPTURE_ALLOWED_HOSTS is not set (deny-by-default for docs capture)"
          )
        );
      }

      if (!allowedHosts.includes(url.hostname)) {
        return withMeta(deny("DOCS_CAPTURE_HOST_NOT_ALLOWED", `host ${url.hostname} not allowlisted for docs capture`));
      }
    }

    // Browser operator (local automation) is deny-by-default for network targets.
    // - Allows file:// for offline/local evidence capture.
    // - http/https requires an explicit host allowlist AND explicit approval (/approve).
    const isBrowserOperator =
      step.adapter === "BrowserOperatorAdapter" || action === "browser.operator" || action.startsWith("browser.operator.");

    if (isBrowserOperator) {
      const readOnlyFlag = (step as any).read_only;
      if (readOnlyFlag !== true) {
        return withMeta(deny("BROWSER_OPERATOR_REQUIRES_READ_ONLY", "browser.operator requires read_only=true"));
      }

      if (url.protocol === "file:") {
        // Allowed (offline/local).
      } else if (url.protocol === "http:" || url.protocol === "https:") {
        const allowedHosts = parseCsv(env.BROWSER_OPERATOR_ALLOWED_HOSTS);
        if (!allowedHosts.length) {
          return withMeta(
            deny(
              "BROWSER_OPERATOR_HOST_NOT_ALLOWED",
              "BROWSER_OPERATOR_ALLOWED_HOSTS is not set (deny-by-default for browser operator network navigation)"
            )
          );
        }
        if (!allowedHosts.includes(url.hostname)) {
          return withMeta(
            deny("BROWSER_OPERATOR_HOST_NOT_ALLOWED", `host ${url.hostname} not allowlisted for browser operator`)
          );
        }

        if (!approved) {
          const destination = `${url.hostname}${url.pathname}`;
          return withMeta(
            requireApproval({
              code: "BROWSER_OPERATOR_NETWORK_APPROVAL_REQUIRED",
              reason: "Browser operator network navigation requires explicit approval",
              action,
              destination,
              summary: `Navigate ${url.protocol}//${url.hostname}${url.pathname}`,
            })
          );
        }
      } else {
        return withMeta(deny("BROWSER_OPERATOR_PROTOCOL_BLOCK", `protocol not allowed: ${url.protocol}`));
      }
    }

    // Browser L0 (read-only) is a separate evidence lane.
    // It is deny-by-default and requires an explicit host allowlist for http(s) URLs.
    const isBrowserL0Action = action === "browser.l0" || action.startsWith("browser.l0.");
    if (isBrowserL0Action) {
      const method = String(step.method || "GET").toUpperCase();
      const readOnlyFlag = (step as any).read_only;

      if (readOnlyFlag !== true) {
        return withMeta(deny("BROWSER_L0_REQUIRES_READ_ONLY", "browser.l0 requires read_only=true"));
      }

      if (method !== "GET" && method !== "HEAD") {
        return withMeta(deny("BROWSER_L0_METHOD_NOT_ALLOWED", "browser.l0 only allows GET/HEAD"));
      }

      const allowData = String(env.BROWSER_L0_ALLOW_DATA ?? "1").trim() !== "0";
      const allowHttp = String(env.BROWSER_L0_ALLOW_HTTP ?? "0").trim() === "1";
      const allowedSchemes = allowData
        ? allowHttp
          ? ["https:", "http:", "data:"]
          : ["https:", "data:"]
        : allowHttp
          ? ["https:", "http:"]
          : ["https:"];

      const allowedHosts = parseCsv(env.BROWSER_L0_ALLOWED_HOSTS);

      try {
        assertUrlSafeForL0(step.url, { allowedSchemes, allowedHosts });
      } catch (err: any) {
        if (err instanceof BrowserL0GuardError) {
          if (err.code === "SCHEME_NOT_ALLOWED") {
            return withMeta(deny("SCHEME_NOT_ALLOWED", err.message));
          }
          if (err.code === "HOST_NOT_ALLOWED") {
            return withMeta(deny("HOST_NOT_ALLOWED", err.message));
          }
          if (err.code === "SSRF_GUARD_BLOCKED") {
            return withMeta(deny("SSRF_GUARD_BLOCKED", err.message));
          }
          return withMeta(deny("BROWSER_L0_BAD_URL", err.message));
        }
        return withMeta(deny("BROWSER_L0_BAD_URL", String(err?.message ?? err)));
      }

      // data: is offline and deterministic; allow it through the generic protocol guard.
      if (url.protocol === "data:") {
        continue;
      }
    }

    // Tier 6.x: Notion has explicit read vs write lanes.
    // - Read is deny-only (Tier 6.0 contract)
    // - Write is approval-scoped (Tier 6.1), never auto-exec
    const isNotionPath = url.pathname.includes("/notion/");
    if (isNotionPath) {
      if (action.startsWith("notion.read.")) {
        if (!methodIsReadOnly(step.method)) {
          return withMeta(deny("METHOD_NOT_ALLOWED", `Notion read method ${step.method} is not allowed (GET/HEAD only)`));
        }
        const readOnlyFlag = (step as any).read_only;
        if (readOnlyFlag !== true) {
          return withMeta(deny("READ_ONLY_REQUIRED", "Notion read steps must set read_only=true"));
        }
      } else if (action === "notion.write.page_property" || action === "notion.write.page_title") {
        // Validate the write shape first (deny, no approval loophole).
        if (step.method !== "PATCH") {
          return withMeta(deny("METHOD_NOT_ALLOWED", `Notion write method ${step.method} is not allowed (PATCH only)`));
        }

        // Tier 6.1/6.2: tight endpoint allowlist (no silent drift).
        const p = url.pathname;
        const pagePrefix = "/notion/page/";
        if (!p.startsWith(pagePrefix)) {
          return withMeta(
            deny("NOTION_ENDPOINT_FORBIDDEN", "Notion write steps must target /notion/page/:id endpoints only")
          );
        }

        const remainder = p.slice(pagePrefix.length); // <id> or <id>/title
        const hasSlash = remainder.includes("/");
        const isTitleEndpoint = hasSlash && remainder.endsWith("/title") && remainder.split("/").length === 2;
        const isPageEndpoint = !hasSlash && remainder.length > 0;

        if (action === "notion.write.page_property") {
          if (!isPageEndpoint) {
            return withMeta(
              deny("NOTION_ENDPOINT_FORBIDDEN", "notion.write.page_property is restricted to /notion/page/:id")
            );
          }
        }
        if (action === "notion.write.page_title") {
          if (!isTitleEndpoint) {
            return withMeta(
              deny("NOTION_ENDPOINT_FORBIDDEN", "notion.write.page_title is restricted to /notion/page/:id/title")
            );
          }
        }

        const readOnlyFlag = (step as any).read_only;
        if (readOnlyFlag !== false) {
          return withMeta(deny("READ_ONLY_REQUIRED", "Notion write steps must set read_only=false"));
        }

        // Tier 6.1: Notion writes are approval-scoped by default.
        // Exception (Tier-19/20): in APPROVAL_GATED_AUTONOMY, a promoted fingerprint or an
        // active delegated class may satisfy the approval gate (still subject to all deny checks).
        if (!approved) {
          const canSkipNotionApproval =
            autonomyMode === "APPROVAL_GATED_AUTONOMY" &&
            (promotionMaySkipApprovalGate ||
              (delegationDecision && delegationDecision.active === true && delegationDecision.reason === "OK"));

          if (canSkipNotionApproval) {
            continue;
          }

          const destination = `${url.hostname}${url.pathname}`;
          const isTitleWrite = action === "notion.write.page_title";
          const isOrchestratedWritePhase =
            action === "notion.write.page_property" && meta?.phase_id === "write" && (meta?.phases_count ?? 0) > 0;
          return withMeta(
            requireApproval({
            code: isTitleWrite
              ? "NOTION_WRITE_REQUIRES_APPROVAL"
              : isOrchestratedWritePhase
                ? "ORCHESTRATED_WRITE_REQUIRES_APPROVAL"
                : "NOTION_WRITE_APPROVAL_REQUIRED",
            reason: isTitleWrite
              ? "Notion title updates require human approval"
              : isOrchestratedWritePhase
                ? "Tier-7 write phase requires approval"
                : "Notion writes require explicit approval (Tier 6.1)",
            action,
            destination,
            summary: `PATCH ${url.pathname}`,
            })
          );
        }
      } else {
        return withMeta(
          deny(
          "NOTION_ACTION_FORBIDDEN",
          "Only notion.read.* and notion.write.page_property/notion.write.page_title actions may access /notion/ endpoints"
          )
        );
      }
    }

    if (url.protocol !== "http:" && url.protocol !== "https:" && !(isBrowserOperator && url.protocol === "file:")) {
      return withMeta(deny("POLICY_URL_PROTOCOL_BLOCK", `protocol not allowed: ${url.protocol}`));
    }
  }

  // 2) Domain allowlist
  const allowedDomains = parseCsv(env.ALLOWED_DOMAINS);
  if (allowedDomains.length) {
    for (const step of plan.steps) {
      const u = new URL(step.url);
      if (u.protocol === "data:") continue;
      const host = u.hostname;
      if (!allowedDomains.includes(host)) {
        return withMeta(deny("DOMAIN_NOT_ALLOWED", `host ${host} not allowlisted`));
      }
    }
  }

  // Optional method allowlist
  const allowedMethods = parseCsv(env.ALLOWED_METHODS).map((m) => m.toUpperCase());
  if (allowedMethods.length) {
    for (const step of plan.steps) {
      if (!allowedMethods.includes(step.method)) {
        return withMeta(deny("POLICY_METHOD_BLOCK", `method ${step.method} not allowlisted`));
      }
    }
  }

  // 3) Time limits (cheap, deterministic)
  const maxSteps = parseNumberEnv(env.POLICY_MAX_STEPS);
  if (maxSteps !== null && plan.steps.length > maxSteps) {
    return withMeta(deny("BUDGET_MAX_STEPS_EXCEEDED", `plan has ${plan.steps.length} steps; max ${maxSteps}`));
  }

  const maxStepTimeoutMs = parseNumberEnv(env.POLICY_MAX_STEP_TIMEOUT_MS);
  const defaultStepTimeoutMs = parseNumberEnv(env.DEFAULT_STEP_TIMEOUT_MS);
  if (maxStepTimeoutMs !== null && defaultStepTimeoutMs !== null && defaultStepTimeoutMs > maxStepTimeoutMs) {
    return withMeta(
      deny(
      "POLICY_STEP_TIMEOUT_CAP",
      `DEFAULT_STEP_TIMEOUT_MS (${defaultStepTimeoutMs}) exceeds cap (${maxStepTimeoutMs})`
      )
    );
  }

  const noExecAfter = parseUtcHm(env.POLICY_NO_EXEC_AFTER_UTC);
  if (noExecAfter) {
    const h = clock.getUTCHours();
    const m = clock.getUTCMinutes();
    const cur = h * 60 + m;
    const cutoff = noExecAfter.hour * 60 + noExecAfter.minute;
    if (cur >= cutoff) {
      return withMeta(deny("POLICY_TIME_WINDOW", `execution blocked after ${env.POLICY_NO_EXEC_AFTER_UTC} UTC`));
    }
  }

  // 4) Tier 5.3 approval gate: writes in production require explicit human approval.
  if (isProd(env)) {
    const hasWrites = plan.steps.some((s) => methodIsWrite(s.method));
    if (hasWrites) {
      // If we're resuming via /approve, allow the write to proceed.
      const approved =
        meta?.execution_id && meta?.approved_execution_id && meta.execution_id === meta.approved_execution_id;
      if (!approved) {
        const hosts = uniqueHostsFromSteps(plan.steps);
        const destination = hosts.length ? `Hosts:${hosts.join(",")}` : "External";
        const writeCount = plan.steps.filter((s) => methodIsWrite(s.method)).length;
        return withMeta(
          requireApproval({
          code: "WRITE_OPERATION",
          reason: "write operation in production requires explicit approval",
          action: "external.write",
          destination,
          summary: `Execute ${writeCount} write step(s)`,
          })
        );
      }
    }
  }

  return withMeta({ allowed: true });
}
