/**
 * Canonical governed Python↔TypeScript runtime bridge adapter.
 *
 * This module provides the TypeScript side of a deterministic, versioned
 * JSON envelope that carries governed mission-control state across the
 * runtime boundary between the Python L2 backend and the web frontend.
 *
 * Design rules (P6 bridge):
 *   - The L2 store is the ONLY state machine.
 *   - This adapter owns no transition logic — it validates read-only state.
 *   - Every envelope carries an integrity hash and authority_delta = 0.
 *   - Provider invocation, live external calls, and secrets are prohibited.
 *   - Replay/stale/tamper detection is fail-closed.
 *   - The wire schema is versioned; mismatches are denied.
 */

import {
  BridgeEnvelopeV1,
  BridgeResultV1,
  AuthorityDecision,
  ConsequenceClass,
  BridgeContractError,
  InMemoryNonceTracker,
  ValidateEnvelopeOptions,
  deserializeEnvelopeV1,
  deserializeResultV1,
  serializeEnvelopeV1,
  serializeResultV1,
  validateEnvelope,
  validateResult,
  computePayloadSha256,
  computeEvidenceSha256,
  BRIDGE_CONTRACT_VERSION,
} from "./bridgeContract";
import { AuthorityValidator } from "./bridgeAuthority";

/** Bridge wire-schema version.  Must match Python BRIDGE_SCHEMA_VERSION. */
export const BRIDGE_SCHEMA_VERSION = 1;

/** Canonical state source identifier. */
export const CANONICAL_STATE_SOURCE = 'sintra_live/l2';

/** Read-only projection of L2 mission state. */
export interface BridgeProjection {
  mission_id: string;
  aggregate_version: number;
  aggregate_sha256: string;
  current_state: string;
  authority_delta: number;
  side_effects: number;
  canonical_state_source: string;
}

/** Full envelope crossing the boundary. */
export interface BridgeEnvelope {
  schema_version: number;
  mission_id: string;
  aggregate_version: number;
  aggregate_sha256: string;
  current_state: string;
  authority_delta: number;
  side_effects: number;
  canonical_state_source: string;
  envelope_sha256: string;
  payload: Record<string, unknown>;
}

/** Error thrown when a bridge envelope fails validation. */
export class BridgeEnvelopeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BridgeEnvelopeError';
  }
}

/**
 * Compute SHA-256 hash of a JSON-serializable body.
 * Uses the Web Crypto API (available in browsers and Node 18+).
 */
async function computeHash(body: Record<string, unknown>): Promise<string> {
  // Sort keys deterministically — must match Python json.dumps(sort_keys=True)
  const sorted = sortKeysDeep(body);
  const encoded = new TextEncoder().encode(JSON.stringify(sorted));
  const digest = await crypto.subtle.digest('SHA-256', encoded);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function sortKeysDeep<T>(value: T): T {
  if (value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map(sortKeysDeep) as unknown as T;
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(value as Record<string, unknown>).sort()) {
    sorted[key] = sortKeysDeep((value as Record<string, unknown>)[key]);
  }
  return sorted as unknown as T;
}

/**
 * Build a sealed envelope from a projection and optional payload.
 * The envelope includes a SHA-256 integrity hash.
 */
export async function serializeEnvelope(
  projection: BridgeProjection,
  payload: Record<string, unknown> = {},
): Promise<BridgeEnvelope> {
  const body: Omit<BridgeEnvelope, 'envelope_sha256'> = {
    schema_version: BRIDGE_SCHEMA_VERSION,
    mission_id: projection.mission_id,
    aggregate_version: projection.aggregate_version,
    aggregate_sha256: projection.aggregate_sha256,
    current_state: projection.current_state,
    authority_delta: projection.authority_delta,
    side_effects: projection.side_effects,
    canonical_state_source: projection.canonical_state_source,
    payload,
  };
  const envelope_sha256 = await computeHash(body as Record<string, unknown>);
  return { ...body, envelope_sha256 };
}

/**
 * Parse and validate a raw JSON envelope.  Fail-closed on all violations.
 */
export async function deserializeEnvelope(raw: string): Promise<BridgeEnvelope> {
  let body: Record<string, unknown>;
  try {
    body = JSON.parse(raw);
  } catch {
    throw new BridgeEnvelopeError('envelope is not valid JSON');
  }

  if (typeof body !== 'object' || body === null) {
    throw new BridgeEnvelopeError('envelope body must be a JSON object');
  }

  // Schema version
  const sv = body.schema_version;
  if (sv !== BRIDGE_SCHEMA_VERSION) {
    throw new BridgeEnvelopeError(
      `schema_version mismatch: expected ${BRIDGE_SCHEMA_VERSION}, got ${sv}`,
    );
  }

  // Required fields
  const required = [
    'mission_id', 'aggregate_version', 'aggregate_sha256',
    'current_state', 'authority_delta', 'side_effects',
    'canonical_state_source', 'envelope_sha256',
  ];
  for (const key of required) {
    if (!(key in body)) {
      throw new BridgeEnvelopeError(`missing required field: ${key}`);
    }
  }

  // Authority delta must be zero
  if (body.authority_delta !== 0) {
    throw new BridgeEnvelopeError(
      `authority_delta must be zero, got ${body.authority_delta}`,
    );
  }

  // Side effects must be zero
  if (body.side_effects !== 0) {
    throw new BridgeEnvelopeError(
      `side_effects must be zero, got ${body.side_effects}`,
    );
  }

  // Canonical source
  if (body.canonical_state_source !== CANONICAL_STATE_SOURCE) {
    throw new BridgeEnvelopeError(
      `canonical_state_source must be ${CANONICAL_STATE_SOURCE}, got ${body.canonical_state_source}`,
    );
  }

  // Integrity hash verification
  const expectedHash = body.envelope_sha256 as string;
  const bodyForHash: Record<string, unknown> = { ...body };
  delete bodyForHash.envelope_sha256;
  const computed = await computeHash(bodyForHash);
  if (computed !== expectedHash) {
    throw new BridgeEnvelopeError(
      `integrity hash mismatch: expected ${expectedHash}, computed ${computed}`,
    );
  }

  return body as unknown as BridgeEnvelope;
}

// ---------------------------------------------------------------------------
// V1 canonical bridge runtime adapter
//
// The following functions use the canonical V1 contract (bridgeContract.ts)
// to provide a fail-closed bridge runtime that consumes only validated V1
// envelopes, rejects malformed/missing authority fields, preserves
// mission/execution identity, and returns structured V1 results.
//
// Design rules (V1):
//   - Consume only validated V1 envelopes (deserialize + validate).
//   - Reject malformed/missing authority fields (fail-closed).
//   - Preserve mission/execution identity across the boundary.
//   - Return structured V1 results.
//   - No privilege inference from caller.
//   - No direct authority expansion (authority_delta == 0).
// ---------------------------------------------------------------------------

/**
 * Transport status for bridge operations.
 *
 * BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS.
 * A successful transport means the envelope was received, validated,
 * and processed without protocol violations. The mission outcome
 * is carried in the V1 result's status field, which may be
 * COMPLETE, UNVERIFIED, FAILED, etc.
 *
 * Key distinction:
 *   - SUCCESS: The bridge transport succeeded (no protocol error).
 *   - REJECTED: The envelope was rejected by fail-closed validation.
 *   - DENIED: Authority decision was DENY / AUTHORITY_MISSING / etc.
 *   - ERROR: An unexpected error occurred during bridge processing.
 */
export enum BridgeTransportStatus {
  /** Bridge transport succeeded — check result.status for mission outcome. */
  SUCCESS = "SUCCESS",
  /** Envelope rejected by fail-closed validation (malformed, hash mismatch, etc.). */
  REJECTED = "REJECTED",
  /** Authority decision denied execution (DENY, AUTHORITY_MISSING, POLICY_CONFLICT, etc.). */
  DENIED = "DENIED",
  /** Envelope expired or authority revoked. */
  EXPIRED = "EXPIRED",
  /** Unexpected error during bridge processing. */
  ERROR = "ERROR",
}

/**
 * Outcome of executing a capability via the bridge.
 *
 * This is the internal representation of what happened when the
 * capability executor was invoked. It is used by buildV1Result()
 * to construct a V1 result envelope.
 */
export interface BridgeExecutionOutcome {
  /** The mission_id from the source envelope (identity preserved). */
  mission_id: string;
  /** The execution_id from the source envelope (identity preserved). */
  execution_id: string;
  /** The nonce from the source envelope (identity preserved). */
  nonce: string;
  /** Mission outcome status (e.g. "COMPLETE", "UNVERIFIED", "FAILED"). */
  status: string;
  /** The result payload produced by the capability executor. */
  result: Record<string, unknown>;
  /** Evidence produced by the capability executor (must be non-empty). */
  evidence: Record<string, unknown>;
  /** ISO-8601 timestamp of completion. */
  completed_at: string;
}

/**
 * Input fields for building a V1 envelope.
 *
 * These are the projection + authority + execution fields needed
 * to construct a canonical BridgeEnvelopeV1.
 */
export interface V1EnvelopeInput {
  // Identity fields
  mission_id: string;
  execution_id: string;
  nonce: string;
  tenant_id: string;
  actor_id: string;
  // Authority fields
  authority_decision: AuthorityDecision;
  consequence_class: ConsequenceClass;
  capability_id: string;
  // Payload
  payload: Record<string, unknown>;
  // Temporal fields
  issued_at: string;
  expires_at: string;
  // Provenance
  provenance: string;
}

/**
 * Build a V1 envelope from projection + authority + execution fields.
 *
 * This function constructs a canonical BridgeEnvelopeV1, computing
 * the payload_sha256 hash from the payload. The envelope is NOT
 * validated here — call receiveV1Envelope() to validate.
 *
 * @param input - The envelope input fields
 * @returns A BridgeEnvelopeV1 with computed payload_sha256
 */
export async function buildV1Envelope(
  input: V1EnvelopeInput,
): Promise<BridgeEnvelopeV1> {
  const payloadSha256 = await computePayloadSha256(input.payload);
  return {
    schema_version: BRIDGE_CONTRACT_VERSION,
    mission_id: input.mission_id,
    execution_id: input.execution_id,
    nonce: input.nonce,
    tenant_id: input.tenant_id,
    actor_id: input.actor_id,
    authority_decision: input.authority_decision,
    consequence_class: input.consequence_class,
    capability_id: input.capability_id,
    payload: input.payload,
    payload_sha256: payloadSha256,
    issued_at: input.issued_at,
    expires_at: input.expires_at,
    provenance: input.provenance,
  };
}

/**
 * Deserialize and validate a V1 envelope (fail-closed).
 *
 * This is the canonical receive path:
 *   1. Deserialize the JSON string (field set + schema version + hash binding).
 *   2. Validate against all 14 fail-closed reject rules.
 *
 * @param raw - The raw JSON string received over the bridge
 * @param options - Validation options (nonce tracker, expected IDs, etc.)
 * @returns The validated BridgeEnvelopeV1
 * @throws BridgeContractError on any validation failure
 */
export async function receiveV1Envelope(
  raw: string,
  options: ValidateEnvelopeOptions = {},
): Promise<BridgeEnvelopeV1> {
  // Step 1: Deserialize (field set, schema version, payload hash binding)
  const envelope = await deserializeEnvelopeV1(raw);
  // Step 2: Validate (14 fail-closed reject rules)
  await validateEnvelope(envelope, options);
  return envelope;
}

/**
 * Build a V1 result from an execution outcome.
 *
 * This function constructs a canonical BridgeResultV1, computing
 * the evidence_sha256 hash from the evidence. The authority_delta
 * is always 0 (no authority expansion) and side_effect_count is
 * always 0 (no side effects across the bridge).
 *
 * @param outcome - The execution outcome
 * @returns A BridgeResultV1 with computed evidence_sha256
 */
export async function buildV1Result(
  outcome: BridgeExecutionOutcome,
): Promise<BridgeResultV1> {
  const evidenceSha256 = await computeEvidenceSha256(outcome.evidence);
  return {
    schema_version: BRIDGE_CONTRACT_VERSION,
    mission_id: outcome.mission_id,
    execution_id: outcome.execution_id,
    nonce: outcome.nonce,
    status: outcome.status,
    result: outcome.result,
    evidence: outcome.evidence,
    evidence_sha256: evidenceSha256,
    // Invariants: no authority expansion, no side effects
    authority_delta: 0,
    side_effect_count: 0,
    completed_at: outcome.completed_at,
  };
}

/**
 * Deserialize and validate a V1 result.
 *
 * This is the canonical receive path for results:
 *   1. Deserialize the JSON string (field set + schema version + hash binding).
 *   2. Validate against fail-closed invariants (authority_delta == 0, etc.).
 *
 * @param raw - The raw JSON string received over the bridge
 * @param expectedEnvelope - Optional envelope for identity binding check
 * @returns The validated BridgeResultV1
 * @throws BridgeContractError on any validation failure
 */
export async function receiveV1Result(
  raw: string,
  expectedEnvelope?: BridgeEnvelopeV1,
): Promise<BridgeResultV1> {
  // Step 1: Deserialize (field set, schema version, evidence hash binding)
  const result = await deserializeResultV1(raw);
  // Step 2: Validate (authority_delta == 0, side_effect_count == 0, identity binding)
  await validateResult(result, { expectedEnvelope });
  return result;
}

/**
 * Canonical bridge execution flow: receive → validate → execute → result.
 *
 * This is the complete canonical path for executing a capability via the
 * bridge. It:
 *   1. Receives and validates the V1 envelope (fail-closed).
 *   2. Checks authority via AuthorityValidator (fail-closed).
 *   3. If authority permits (ALLOW), invokes the executor.
 *   4. If authority denies, returns a DENIED transport status without executing.
 *   5. Builds a V1 result from the execution outcome.
 *   6. Returns the transport status + result.
 *
 * The executor function receives the validated envelope and returns a
 * BridgeExecutionOutcome. The executor MUST NOT:
 *   - Expand authority (authority_delta must be 0 in the result).
 *   - Produce side effects (side_effect_count must be 0 in the result).
 *   - Infer privileges from the caller.
 *   - Modify the envelope.
 *
 * @param raw - The raw JSON string received over the bridge
 * @param executor - The capability executor function
 * @param options - Validation options (nonce tracker, expected IDs, etc.)
 * @returns An object with transportStatus and, if successful, the V1 result
 */
export async function executeViaBridge(
  raw: string,
  executor: (envelope: BridgeEnvelopeV1) => Promise<BridgeExecutionOutcome>,
  options: {
    nonceTracker?: InMemoryNonceTracker;
    expectedMissionId?: string;
    expectedTenantId?: string;
    currentTime?: string;
  } = {},
): Promise<{
  transportStatus: BridgeTransportStatus;
  result?: BridgeResultV1;
  envelope?: BridgeEnvelopeV1;
  error?: string;
}> {
  let envelope: BridgeEnvelopeV1;

  // Step 1: Receive and validate the envelope (fail-closed)
  try {
    envelope = await receiveV1Envelope(raw, {
      nonceTracker: options.nonceTracker,
      expectedMissionId: options.expectedMissionId,
      expectedTenantId: options.expectedTenantId,
      currentTime: options.currentTime,
    });
  } catch (err) {
    if (err instanceof BridgeContractError) {
      // Classify the rejection
      if (
        err.rule === "EXPIRED_ENVELOPE" ||
        err.rule === "EXPIRED_AUTHORITY"
      ) {
        return {
          transportStatus: BridgeTransportStatus.EXPIRED,
          error: err.message,
        };
      }
      if (err.rule === "REVOKED_AUTHORITY") {
        return {
          transportStatus: BridgeTransportStatus.EXPIRED,
          error: err.message,
        };
      }
      return {
        transportStatus: BridgeTransportStatus.REJECTED,
        error: err.message,
      };
    }
    return {
      transportStatus: BridgeTransportStatus.ERROR,
      error: err instanceof Error ? err.message : String(err),
    };
  }

  // Step 2: Authority validation (fail-closed)
  const authorityValidator = new AuthorityValidator();
  try {
    authorityValidator.validate(envelope);
  } catch (err) {
    if (err instanceof BridgeContractError) {
      if (
        err.rule === "EXPIRED_AUTHORITY" ||
        err.rule === "REVOKED_AUTHORITY"
      ) {
        return {
          transportStatus: BridgeTransportStatus.EXPIRED,
          error: err.message,
          envelope,
        };
      }
      return {
        transportStatus: BridgeTransportStatus.DENIED,
        error: err.message,
        envelope,
      };
    }
    return {
      transportStatus: BridgeTransportStatus.ERROR,
      error: err instanceof Error ? err.message : String(err),
      envelope,
    };
  }

  // Step 3: Check if authority permits execution
  if (!authorityValidator.canExecute(envelope)) {
    // Authority decision is not ALLOW — deny without executing
    return {
      transportStatus: BridgeTransportStatus.DENIED,
      error: `authority_decision is ${envelope.authority_decision}, not ALLOW`,
      envelope,
    };
  }

  // Step 4: Execute the capability
  let outcome: BridgeExecutionOutcome;
  try {
    outcome = await executor(envelope);
  } catch (err) {
    return {
      transportStatus: BridgeTransportStatus.ERROR,
      error: err instanceof Error ? err.message : String(err),
      envelope,
    };
  }

  // Step 5: Build the V1 result
  let result: BridgeResultV1;
  try {
    result = await buildV1Result(outcome);
    // Validate the result we built (self-check)
    await validateResult(result, { expectedEnvelope: envelope });
  } catch (err) {
    return {
      transportStatus: BridgeTransportStatus.ERROR,
      error: err instanceof Error ? err.message : String(err),
      envelope,
    };
  }

  // Step 6: Return success
  return {
    transportStatus: BridgeTransportStatus.SUCCESS,
    result,
    envelope,
  };
}