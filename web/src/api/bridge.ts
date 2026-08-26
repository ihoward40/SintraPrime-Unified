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