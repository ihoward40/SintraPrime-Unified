import { z } from "zod";

/**
 * SP-IKE governed runtime contract.
 *
 * This module is deliberately stateless. SintraPrime remains the system of record
 * and authority plane. Adapters must persist through the canonical control plane;
 * IKE-Bot must not create a second memory, scheduler, approval, or orchestration DB.
 */

export const CapabilityId = z.enum([
  "named_agents",
  "isolated_agent_memory",
  "agent_to_agent_handoff",
  "scheduled_routines",
  "event_driven_work",
  "multi_model_routing",
  "local_model_execution",
  "living_file_memory",
  "semantic_memory_retrieval",
  "skill_library",
  "git_coding_delegate",
  "connector_tools",
  "voice_conversation",
  "screen_guidance",
  "computer_control",
  "email_actions",
  "calendar_actions",
  "drive_actions",
  "phone_calls",
  "draft_first_actions",
  "principal_approval_gate",
  "action_narration",
  "kill_switch",
  "evidence_receipts",
  "cost_budgeting",
  "self_evaluation",
  "swarm_execution",
]);

export type CapabilityId = z.infer<typeof CapabilityId>;

export type RiskTier = "observe" | "draft" | "reversible" | "consequential" | "prohibited";

export interface CapabilityDefinition {
  id: CapabilityId;
  description: string;
  defaultRisk: RiskTier;
  requiresPrincipalApproval: boolean;
  requiresAuthenticatedPrincipal: boolean;
  evidenceRequired: boolean;
  adapterRequired: boolean;
}

export const CAPABILITIES: Readonly<Record<CapabilityId, CapabilityDefinition>> = {
  named_agents: { id: "named_agents", description: "Persistent named specialist agents with role, description, avatar metadata, skills, and provider preferences.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  isolated_agent_memory: { id: "isolated_agent_memory", description: "Per-agent scoped memory with explicit shared-memory promotion.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  agent_to_agent_handoff: { id: "agent_to_agent_handoff", description: "@mention/delegation between agents with causation-preserving replies.", defaultRisk: "draft", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  scheduled_routines: { id: "scheduled_routines", description: "Recurring agent missions routed through canonical scheduling and governance.", defaultRisk: "draft", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  event_driven_work: { id: "event_driven_work", description: "Webhook/event-triggered missions with authenticated source, scope, revocation, and audit.", defaultRisk: "draft", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  multi_model_routing: { id: "multi_model_routing", description: "Route each task to local or cloud models by capability, latency, privacy, and cost policy.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  local_model_execution: { id: "local_model_execution", description: "Use local models where policy and task requirements permit.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  living_file_memory: { id: "living_file_memory", description: "Human-readable Markdown/Obsidian-compatible knowledge exposed as governed context, not a hidden duplicate system of record.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  semantic_memory_retrieval: { id: "semantic_memory_retrieval", description: "On-demand retrieval of relevant memory instead of loading entire vaults into context.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  skill_library: { id: "skill_library", description: "Versioned reusable skills with owner, provenance, compatibility, last-used and review state.", defaultRisk: "draft", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  git_coding_delegate: { id: "git_coding_delegate", description: "Delegate coding tasks to governed coding agents with branch/test/review boundaries.", defaultRisk: "reversible", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  connector_tools: { id: "connector_tools", description: "Use Gmail, Calendar, Drive, Slack, GitHub, MCP and plugins through scoped service identities.", defaultRisk: "reversible", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  voice_conversation: { id: "voice_conversation", description: "Interruptible conversational voice interface with explicit task state.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  screen_guidance: { id: "screen_guidance", description: "Vision-based UI guidance such as pointing to the next control without clicking it.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  computer_control: { id: "computer_control", description: "Screen/mouse/keyboard execution with narration, stop control and approval gates before consequential actions.", defaultRisk: "reversible", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  email_actions: { id: "email_actions", description: "Read/draft/send email with draft-first defaults and explicit send authority.", defaultRisk: "consequential", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  calendar_actions: { id: "calendar_actions", description: "Read availability and create/update events under scoped authority.", defaultRisk: "reversible", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  drive_actions: { id: "drive_actions", description: "Read and write governed files while preserving source provenance and version history.", defaultRisk: "reversible", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  phone_calls: { id: "phone_calls", description: "Place calls through an approved telephony adapter with identity disclosure, transcript and consent rules.", defaultRisk: "consequential", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  draft_first_actions: { id: "draft_first_actions", description: "Prepare work fully, then stop before publish/send/spend/file/submit unless separately authorized.", defaultRisk: "draft", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: false },
  principal_approval_gate: { id: "principal_approval_gate", description: "Human-in-the-loop gate for consequential side effects and policy exceptions.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  action_narration: { id: "action_narration", description: "Real-time narration of tool and computer actions so the Principal can interrupt or redirect.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  kill_switch: { id: "kill_switch", description: "Principal-controlled immediate cancellation of active execution with durable receipt.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  evidence_receipts: { id: "evidence_receipts", description: "Cryptographically hash action inputs, outputs, approvals, side effects and causation metadata.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  cost_budgeting: { id: "cost_budgeting", description: "Per-mission token, API, telephony and spend ceilings with hard stops.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  self_evaluation: { id: "self_evaluation", description: "Post-run rubric evaluation, contradiction detection and confidence reporting before final brief.", defaultRisk: "observe", requiresPrincipalApproval: false, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
  swarm_execution: { id: "swarm_execution", description: "Parallel specialist agents coordinated by a governed mission graph with bounded fan-out and causation tracking.", defaultRisk: "draft", requiresPrincipalApproval: true, requiresAuthenticatedPrincipal: true, evidenceRequired: true, adapterRequired: true },
};

export interface PrincipalContext {
  authenticated: boolean;
  principalId?: string;
  correlationId: string;
  approvedCapabilities?: CapabilityId[];
  maxRisk?: Exclude<RiskTier, "prohibited">;
}

export interface GovernedAction {
  capability: CapabilityId;
  action: string;
  risk?: RiskTier;
  sideEffect: boolean;
  draftOnly?: boolean;
  estimatedCostUsd?: number;
}

export interface GateDecision {
  allowed: boolean;
  requiresApproval: boolean;
  reason: string;
  effectiveRisk: RiskTier;
}

const RISK_ORDER: Record<RiskTier, number> = {
  observe: 0,
  draft: 1,
  reversible: 2,
  consequential: 3,
  prohibited: 4,
};

export function evaluateAuthority(ctx: PrincipalContext, input: GovernedAction): GateDecision {
  const capability = CAPABILITIES[input.capability];
  const effectiveRisk = input.draftOnly && input.risk === "consequential"
    ? "draft"
    : (input.risk ?? capability.defaultRisk);

  if (effectiveRisk === "prohibited") {
    return { allowed: false, requiresApproval: false, reason: "Action is prohibited by runtime policy.", effectiveRisk };
  }

  if (capability.requiresAuthenticatedPrincipal && !ctx.authenticated) {
    return { allowed: false, requiresApproval: false, reason: "Authenticated Principal context is required.", effectiveRisk };
  }

  if (ctx.maxRisk && RISK_ORDER[effectiveRisk] > RISK_ORDER[ctx.maxRisk]) {
    return { allowed: false, requiresApproval: false, reason: `Risk tier ${effectiveRisk} exceeds mission ceiling ${ctx.maxRisk}.`, effectiveRisk };
  }

  const preapproved = ctx.approvedCapabilities?.includes(input.capability) ?? false;
  const requiresApproval = input.sideEffect && (capability.requiresPrincipalApproval || effectiveRisk === "consequential") && !preapproved;

  if (requiresApproval) {
    return { allowed: false, requiresApproval: true, reason: "Principal approval is required before the side effect may occur.", effectiveRisk };
  }

  return { allowed: true, requiresApproval: false, reason: "Action is within the current governed authority envelope.", effectiveRisk };
}

export interface ModelCandidate {
  id: string;
  provider: "local" | "openai" | "anthropic" | "google" | "other";
  supportsVision?: boolean;
  supportsTools?: boolean;
  supportsLongContext?: boolean;
  local?: boolean;
  estimatedInputUsdPer1M?: number;
  estimatedOutputUsdPer1M?: number;
}

export interface ModelPolicy {
  requireLocal?: boolean;
  requireVision?: boolean;
  requireTools?: boolean;
  requireLongContext?: boolean;
  maxInputUsdPer1M?: number;
  maxOutputUsdPer1M?: number;
}

export function selectModel(candidates: ModelCandidate[], policy: ModelPolicy): ModelCandidate | undefined {
  return candidates
    .filter((m) => !policy.requireLocal || m.local)
    .filter((m) => !policy.requireVision || m.supportsVision)
    .filter((m) => !policy.requireTools || m.supportsTools)
    .filter((m) => !policy.requireLongContext || m.supportsLongContext)
    .filter((m) => policy.maxInputUsdPer1M === undefined || (m.estimatedInputUsdPer1M ?? Infinity) <= policy.maxInputUsdPer1M)
    .filter((m) => policy.maxOutputUsdPer1M === undefined || (m.estimatedOutputUsdPer1M ?? Infinity) <= policy.maxOutputUsdPer1M)
    .sort((a, b) => {
      if (Boolean(a.local) !== Boolean(b.local)) return a.local ? -1 : 1;
      return (a.estimatedInputUsdPer1M ?? 0) + (a.estimatedOutputUsdPer1M ?? 0)
        - ((b.estimatedInputUsdPer1M ?? 0) + (b.estimatedOutputUsdPer1M ?? 0));
    })[0];
}

export interface AgentProfile {
  id: string;
  name: string;
  title: string;
  description: string;
  soul?: string;
  capabilityIds: CapabilityId[];
  modelPolicy: ModelPolicy;
  memoryScope: "private" | "team" | "principal";
}

export interface HandoffEnvelope {
  missionId: string;
  causationId: string;
  fromAgentId: string;
  toAgentId: string;
  request: string;
  sharedContextRefs: string[];
  requestedCapabilities: CapabilityId[];
}

export interface LivingFileRef {
  uri: string;
  title: string;
  contentHash: string;
  source: "obsidian" | "git" | "drive" | "notion" | "local" | "other";
  classification: "public" | "internal" | "confidential" | "restricted";
  lastReviewedAt?: string;
}

export interface EvidenceReceipt {
  receiptId: string;
  missionId: string;
  causationId: string;
  capability: CapabilityId;
  action: string;
  actorAgentId: string;
  timestamp: string;
  inputHash?: string;
  outputHash?: string;
  approvalId?: string;
  sideEffectReference?: string;
}

export interface RuntimeAdapters {
  /** Canonical SintraPrime intent/mission authority. */
  submitIntent: (input: unknown) => Promise<{ missionId: string; causationId: string }>;
  /** Canonical approval/HITL authority. */
  requestApproval: (input: GovernedAction & { missionId: string; causationId: string }) => Promise<{ approvalId: string; approved: boolean }>;
  /** Canonical evidence/receipt authority. */
  writeReceipt: (receipt: EvidenceReceipt) => Promise<void>;
  /** Canonical memory retrieval. */
  retrieveContext: (query: string, refs?: string[]) => Promise<LivingFileRef[]>;
  /** Canonical scheduler/outbox. */
  scheduleMission: (input: unknown) => Promise<{ scheduleId: string }>;
  /** Canonical cancellation plane. */
  cancelMission: (missionId: string, reason: string) => Promise<void>;
}

export function listCapabilities(): CapabilityDefinition[] {
  return Object.values(CAPABILITIES);
}
