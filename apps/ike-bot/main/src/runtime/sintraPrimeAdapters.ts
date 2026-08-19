import crypto from "crypto";
import {
  EvidenceReceipt,
  GovernedAction,
  LivingFileRef,
  RuntimeAdapters,
} from "./governedRuntime";

export interface PrincipalSession {
  authenticated: true;
  principal_id: string;
  tenant_id: string;
  role: string;
  permissions: string[];
  correlation_id?: string | null;
  causation_id?: string | null;
  service_identity_persistence: "postgresql-durable-descriptor";
  orchestration_state_persistence: "process-local-mock-coordinator";
}

export interface ServiceIdentityDescriptor {
  identity_id: string;
  type: string;
  tenant_id: string;
  display_name: string;
  agent_id?: string | null;
  scopes: string[];
  scoped_folders: string[];
  allowed_capabilities: string[];
  status: string;
  expires_at?: string | null;
}

export interface OrchestrationRun {
  run_id: string;
  status: string;
  tenant_id: string;
  created_by: string;
  constraints: Record<string, unknown>;
  approvals: Array<Record<string, unknown>>;
  routing_decisions: Array<Record<string, unknown>>;
  verification: Array<Record<string, unknown>>;
  reconciliation?: Record<string, unknown> | null;
  events: Array<Record<string, unknown>>;
}

export interface LivingContextItem extends LivingFileRef {
  excerpt: string;
  matchedTerms: string[];
}

export interface AcceptanceSideEffectReceipt {
  committed: boolean;
  side_effect_type: "ACCEPTANCE_MARKER";
  run_id: string;
  draft_hash: string;
  service_identity_id: string;
  audit_log_id: string;
  evidence_hash: string;
  previous_evidence_hash?: string | null;
}

export interface SintraPrimeAdapterOptions {
  baseUrl: string;
  bearerToken: string;
  fetchImpl?: typeof fetch;
}

export interface SubmitIntentInput {
  objective: string;
  constraints?: Record<string, unknown>;
  execution_mode?: string;
  budget_limits?: Record<string, unknown>;
}

export class SintraPrimeRuntimeBridge {
  private readonly baseUrl: string;
  private readonly bearerToken: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: SintraPrimeAdapterOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.bearerToken = options.bearerToken;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async authenticatePrincipal(): Promise<PrincipalSession> {
    return this.json<PrincipalSession>("/api/v1/principal/session", { method: "GET" });
  }

  async provisionServiceIdentity(input: {
    display_name: string;
    agent_id?: string;
    scopes?: string[];
    scoped_folders?: string[];
    allowed_capabilities?: string[];
    credential_ref?: string;
    ttl_minutes?: number;
    idempotency_key?: string;
  }): Promise<ServiceIdentityDescriptor> {
    return this.json<ServiceIdentityDescriptor>("/api/v1/principal/service-identities", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async retrieveLivingContext(query: string, refs: string[]): Promise<LivingContextItem[]> {
    const response = await this.json<Array<{
      uri: string;
      title: string;
      content_hash: string;
      source: "git";
      classification: "internal";
      excerpt: string;
      matched_terms: string[];
    }>>("/api/v1/principal/living-context", {
      method: "POST",
      body: JSON.stringify({ query, refs }),
    });

    return response.map((item) => ({
      uri: item.uri,
      title: item.title,
      contentHash: item.content_hash,
      source: item.source,
      classification: item.classification,
      excerpt: item.excerpt,
      matchedTerms: item.matched_terms,
    }));
  }

  async executeMission(input: SubmitIntentInput): Promise<OrchestrationRun> {
    return this.json<OrchestrationRun>("/api/v1/principal/missions", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async getMission(missionId: string): Promise<OrchestrationRun> {
    return this.json<OrchestrationRun>(
      `/api/v1/principal/missions/${encodeURIComponent(missionId)}`,
      { method: "GET" },
    );
  }

  async approveMission(
    missionId: string,
    approved: boolean,
    reason?: string,
  ): Promise<OrchestrationRun> {
    return this.json<OrchestrationRun>(
      `/api/v1/principal/missions/${encodeURIComponent(missionId)}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ approved, reason }),
      },
    );
  }

  async cancelMission(missionId: string, reason: string): Promise<void> {
    await this.json(`/api/v1/principal/missions/${encodeURIComponent(missionId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async writeRuntimeReceipt(receipt: EvidenceReceipt): Promise<{
    auditLogId: string;
    evidenceHash: string;
    previousEvidenceHash?: string | null;
  }> {
    const response = await this.json<{
      audit_log_id: string;
      evidence_hash: string;
      previous_evidence_hash?: string | null;
    }>("/api/v1/principal/runtime-receipts", {
      method: "POST",
      body: JSON.stringify({
        receipt_id: receipt.receiptId,
        mission_id: receipt.missionId,
        causation_id: receipt.causationId,
        capability: receipt.capability,
        action: receipt.action,
        actor_agent_id: receipt.actorAgentId,
        timestamp: receipt.timestamp,
        input_hash: receipt.inputHash,
        output_hash: receipt.outputHash,
        approval_id: receipt.approvalId,
        side_effect_reference: receipt.sideEffectReference,
      }),
    });
    return {
      auditLogId: response.audit_log_id,
      evidenceHash: response.evidence_hash,
      previousEvidenceHash: response.previous_evidence_hash,
    };
  }

  async commitAcceptanceSideEffect(input: {
    runId: string;
    draftHash: string;
    serviceIdentityId: string;
    principalBrief: Record<string, unknown>;
  }): Promise<AcceptanceSideEffectReceipt> {
    return this.json<AcceptanceSideEffectReceipt>("/api/v1/principal/acceptance-side-effects", {
      method: "POST",
      body: JSON.stringify({
        run_id: input.runId,
        draft_hash: input.draftHash,
        service_identity_id: input.serviceIdentityId,
        side_effect_type: "ACCEPTANCE_MARKER",
        principal_brief: input.principalBrief,
      }),
    });
  }

  asRuntimeAdapters(): RuntimeAdapters {
    return {
      submitIntent: async (input: unknown) => {
        const run = await this.executeMission(input as SubmitIntentInput);
        return { missionId: run.run_id, causationId: run.run_id };
      },
      requestApproval: async (input: GovernedAction & { missionId: string; causationId: string }) => {
        const run = await this.getMission(input.missionId);
        const approval = run.approvals.find(
          (item) => item.status === "REQUESTED" || item.status === "APPROVED",
        );
        return {
          approvalId: String(approval?.approval_id ?? ""),
          approved: approval?.status === "APPROVED",
        };
      },
      writeReceipt: async (receipt: EvidenceReceipt) => {
        await this.writeRuntimeReceipt(receipt);
      },
      retrieveContext: async (query: string, refs?: string[]) => {
        return this.retrieveLivingContext(query, refs ?? []);
      },
      scheduleMission: async () => {
        throw new Error(
          "Canonical scheduler write API is not exposed by SintraPrime Portal; private scheduler fallback is forbidden.",
        );
      },
      cancelMission: async (missionId: string, reason: string) => {
        await this.cancelMission(missionId, reason);
      },
    };
  }

  private async json<T = unknown>(path: string, init: RequestInit): Promise<T> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.bearerToken}`,
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(init.headers ?? {}),
      },
    });
    const text = await response.text();
    const body = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new Error(
        `SintraPrime ${init.method ?? "GET"} ${path} failed (${response.status}): ${text}`,
      );
    }
    return body as T;
  }
}

export function hashCanonical(value: unknown): string {
  const canonical = stableStringify(value);
  return crypto.createHash("sha256").update(canonical, "utf8").digest("hex");
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(",")}}`;
}
