/**
 * Canonical bridge envelope/result contract — sp-bridge-v1 (TypeScript mirror).
 *
 * This module is the TypeScript serialization mapping for the Python
 * bridge_envelope_contract.py. It MUST NOT introduce new semantics.
 * All authority and mission semantics are defined by the Python L2 layer;
 * this module only projects, serializes, and validates them.
 *
 * Design rules:
 *   - The Python contract is the authoritative definition.
 *   - This module is a serialization mapping, NOT a new semantic definition.
 *   - Hashes MUST be identical to Python for the same logical data.
 *   - JSON canonicalization: sortKeysDeep + JSON.stringify (no separators needed
 *     since JS has no tuple distinction — matches existing bridge.ts pattern).
 *   - Fail-closed: any validation failure rejects the envelope/result.
 *   - BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS.
 *   - MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED.
 *   - UNVERIFIED != COMPLETE.
 */

// ---------------------------------------------------------------------------
// Contract version
// ---------------------------------------------------------------------------

export const BRIDGE_CONTRACT_VERSION = "sp-bridge-v1";

// Hash domain separation prefixes (must match Python HASH_DOMAIN_* exactly)
const HASH_DOMAIN_PAYLOAD = "SP-LIVE-001:L2:BRIDGE:PAYLOAD:V1\x00";
const HASH_DOMAIN_EVIDENCE = "SP-LIVE-001:L2:BRIDGE:EVIDENCE:V1\x00";

// ---------------------------------------------------------------------------
// AuthorityDecision enum (union type matching Python values)
// ---------------------------------------------------------------------------

export type AuthorityDecision =
  | "ALLOW"
  | "DENY"
  | "APPROVAL_REQUIRED"
  | "CAPABILITY_UNAVAILABLE"
  | "AUTHORITY_MISSING"
  | "POLICY_CONFLICT"
  | "EXPIRED"
  | "REVOKED";

export const AUTHORITY_DECISION_VALUES: readonly AuthorityDecision[] = [
  "ALLOW",
  "DENY",
  "APPROVAL_REQUIRED",
  "CAPABILITY_UNAVAILABLE",
  "AUTHORITY_MISSING",
  "POLICY_CONFLICT",
  "EXPIRED",
  "REVOKED",
] as const;

// ConsequenceClass (matching Python ConsequenceClass enum values)
export type ConsequenceClass =
  | "READ_ONLY"
  | "REVERSIBLE_INTERNAL"
  | "SCOPED_WRITE"
  | "EXTERNAL_COMMUNICATION"
  | "FINANCIAL"
  | "PRODUCTION"
  | "LEGAL"
  | "SECURITY_SENSITIVE"
  | "GOVERNANCE_PROTECTED";

export const CONSEQUENCE_CLASS_VALUES: readonly ConsequenceClass[] = [
  "READ_ONLY",
  "REVERSIBLE_INTERNAL",
  "SCOPED_WRITE",
  "EXTERNAL_COMMUNICATION",
  "FINANCIAL",
  "PRODUCTION",
  "LEGAL",
  "SECURITY_SENSITIVE",
  "GOVERNANCE_PROTECTED",
] as const;

// ---------------------------------------------------------------------------
// Interfaces (matching Python dataclass fields exactly)
// ---------------------------------------------------------------------------

export interface BridgeEnvelopeV1 {
  schema_version: string;
  mission_id: string;
  execution_id: string;
  nonce: string;
  tenant_id: string;
  actor_id: string;
  authority_decision: AuthorityDecision;
  consequence_class: ConsequenceClass;
  capability_id: string;
  payload: Record<string, unknown>;
  payload_sha256: string;
  issued_at: string;
  expires_at: string;
  provenance: string;
}

export interface BridgeResultV1 {
  schema_version: string;
  mission_id: string;
  execution_id: string;
  nonce: string;
  status: string;
  result: Record<string, unknown>;
  evidence: Record<string, unknown>;
  evidence_sha256: string;
  authority_delta: number;
  side_effect_count: number;
  completed_at: string;
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

export class BridgeContractError extends Error {
  readonly rule: string;
  constructor(rule: string, message?: string) {
    super(message ? `${rule}: ${message}` : rule);
    this.name = "BridgeContractError";
    this.rule = rule;
  }
}

// ---------------------------------------------------------------------------
// Field sets (matching Python ENVELOPE_FIELDS / RESULT_FIELDS)
// ---------------------------------------------------------------------------

export const ENVELOPE_FIELDS: readonly string[] = [
  "schema_version",
  "mission_id",
  "execution_id",
  "nonce",
  "tenant_id",
  "actor_id",
  "authority_decision",
  "consequence_class",
  "capability_id",
  "payload",
  "payload_sha256",
  "issued_at",
  "expires_at",
  "provenance",
] as const;

export const RESULT_FIELDS: readonly string[] = [
  "schema_version",
  "mission_id",
  "execution_id",
  "nonce",
  "status",
  "result",
  "evidence",
  "evidence_sha256",
  "authority_delta",
  "side_effect_count",
  "completed_at",
] as const;

// ---------------------------------------------------------------------------
// Canonical JSON (must produce identical bytes to Python canonical_bytes)
// ---------------------------------------------------------------------------

/**
 * Sort keys recursively in an object/array structure.
 * Matches Python json.dumps(sort_keys=True, separators=(",",":"),
 * ensure_ascii=False).
 *
 * Note: JS JSON.stringify already uses no spaces when no replacer is given,
 * which matches separators=(",",":").
 */
function sortKeysDeep<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(sortKeysDeep) as unknown as T;
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(value as Record<string, unknown>).sort()) {
    sorted[key] = sortKeysDeep((value as Record<string, unknown>)[key]);
  }
  return sorted as unknown as T;
}

/**
 * Canonical JSON bytes matching Python canonical_bytes().
 * Uses sortKeysDeep + JSON.stringify with no whitespace.
 */
function canonicalJsonBytes(value: unknown): Uint8Array {
  const sorted = sortKeysDeep(value);
  // JSON.stringify with no replacer/indentation produces compact JSON (", "":")
  // matching Python separators=(",",":")
  const jsonStr = JSON.stringify(sorted);
  return new TextEncoder().encode(jsonStr);
}

// ---------------------------------------------------------------------------
// Hash helpers (must produce identical SHA-256 to Python)
// ---------------------------------------------------------------------------

/**
 * Compute SHA-256 of payload with domain separation.
 * Uses the same domain prefix + canonical bytes as Python compute_payload_sha256().
 */
export async function computePayloadSha256(
  payload: Record<string, unknown>,
): Promise<string> {
  const domainBytes = new TextEncoder().encode(HASH_DOMAIN_PAYLOAD);
  const payloadBytes = canonicalJsonBytes(payload);
  // Concatenate domain + payload
  const combined = new Uint8Array(domainBytes.length + payloadBytes.length);
  combined.set(domainBytes, 0);
  combined.set(payloadBytes, domainBytes.length);
  const digest = await crypto.subtle.digest("SHA-256", combined);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Compute SHA-256 of evidence with domain separation.
 * Uses the same domain prefix + canonical bytes as Python compute_evidence_sha256().
 */
export async function computeEvidenceSha256(
  evidence: Record<string, unknown>,
): Promise<string> {
  const domainBytes = new TextEncoder().encode(HASH_DOMAIN_EVIDENCE);
  const evidenceBytes = canonicalJsonBytes(evidence);
  const combined = new Uint8Array(domainBytes.length + evidenceBytes.length);
  combined.set(domainBytes, 0);
  combined.set(evidenceBytes, domainBytes.length);
  const digest = await crypto.subtle.digest("SHA-256", combined);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// ---------------------------------------------------------------------------
// Serialization
// ---------------------------------------------------------------------------

/**
 * Serialize a BridgeEnvelopeV1 to canonical JSON string.
 * The output is a compact JSON string with sorted keys,
 * matching Python serialize_envelope_v1().
 */
export async function serializeEnvelopeV1(
  envelope: BridgeEnvelopeV1,
): Promise<string> {
  const sorted = sortKeysDeep(envelope as unknown as Record<string, unknown>);
  return JSON.stringify(sorted);
}

/**
 * Deserialize a canonical JSON string to a BridgeEnvelopeV1.
 * Performs construction-level validation (field set, schema version, hash binding).
 * Full validateEnvelope() must be called separately for the 14 reject rules.
 */
export async function deserializeEnvelopeV1(
  raw: string,
): Promise<BridgeEnvelopeV1> {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new BridgeContractError("INVALID_JSON", "envelope is not valid JSON");
  }
  if (typeof data !== "object" || data === null) {
    throw new BridgeContractError("INVALID_ENVELOPE", "envelope must be a JSON object");
  }

  // Check exact field set
  const expected = new Set(ENVELOPE_FIELDS);
  const actual = new Set(Object.keys(data as Record<string, unknown>));
  if (actual.size !== expected.size || ![...actual].every((k) => expected.has(k))) {
    const missing = [...expected].filter((k) => !actual.has(k)).sort();
    const unknown = [...actual].filter((k) => !expected.has(k)).sort();
    throw new BridgeContractError(
      "FIELD_MISMATCH",
      `missing=${missing}, unknown=${unknown}`,
    );
  }

  const obj = data as Record<string, unknown>;

  // Schema version
  if (obj.schema_version !== BRIDGE_CONTRACT_VERSION) {
    throw new BridgeContractError("SCHEMA_VERSION_MISMATCH");
  }

  // Authority decision validation
  if (!AUTHORITY_DECISION_VALUES.includes(obj.authority_decision as AuthorityDecision)) {
    throw new BridgeContractError(
      "INVALID_AUTHORITY_DECISION",
      `unknown authority_decision: ${obj.authority_decision}`,
    );
  }

  // Consequence class validation
  if (!CONSEQUENCE_CLASS_VALUES.includes(obj.consequence_class as ConsequenceClass)) {
    throw new BridgeContractError(
      "INVALID_CONSEQUENCE_CLASS",
      `unknown consequence_class: ${obj.consequence_class}`,
    );
  }

  // Payload hash binding
  const payload = obj.payload as Record<string, unknown>;
  const expectedHash = await computePayloadSha256(payload);
  if (obj.payload_sha256 !== expectedHash) {
    throw new BridgeContractError("PAYLOAD_HASH_MISMATCH");
  }

  return obj as unknown as BridgeEnvelopeV1;
}

/**
 * Serialize a BridgeResultV1 to canonical JSON string.
 */
export async function serializeResultV1(
  result: BridgeResultV1,
): Promise<string> {
  const sorted = sortKeysDeep(result as unknown as Record<string, unknown>);
  return JSON.stringify(sorted);
}

/**
 * Deserialize a canonical JSON string to a BridgeResultV1.
 */
export async function deserializeResultV1(
  raw: string,
): Promise<BridgeResultV1> {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new BridgeContractError("INVALID_JSON", "result is not valid JSON");
  }
  if (typeof data !== "object" || data === null) {
    throw new BridgeContractError("INVALID_RESULT", "result must be a JSON object");
  }

  // Check exact field set
  const expected = new Set(RESULT_FIELDS);
  const actual = new Set(Object.keys(data as Record<string, unknown>));
  if (actual.size !== expected.size || ![...actual].every((k) => expected.has(k))) {
    const missing = [...expected].filter((k) => !actual.has(k)).sort();
    const unknown = [...actual].filter((k) => !expected.has(k)).sort();
    throw new BridgeContractError(
      "FIELD_MISMATCH",
      `missing=${missing}, unknown=${unknown}`,
    );
  }

  const obj = data as Record<string, unknown>;

  // Schema version
  if (obj.schema_version !== BRIDGE_CONTRACT_VERSION) {
    throw new BridgeContractError("SCHEMA_VERSION_MISMATCH");
  }

  // Evidence hash binding
  const evidence = obj.evidence as Record<string, unknown>;
  const expectedHash = await computeEvidenceSha256(evidence);
  if (obj.evidence_sha256 !== expectedHash) {
    throw new BridgeContractError("EVIDENCE_HASH_MISMATCH");
  }

  return obj as unknown as BridgeResultV1;
}

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

const SHA256_RE = /^[0-9a-f]{64}$/;
const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
const TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/;

function validateIdentifier(value: unknown, name: string): string {
  if (typeof value !== "string" || !IDENTIFIER_RE.test(value)) {
    throw new BridgeContractError("INVALID_IDENTIFIER", `invalid ${name}`);
  }
  return value;
}

function validateSha256(value: unknown, name: string): string {
  if (typeof value !== "string" || !SHA256_RE.test(value)) {
    throw new BridgeContractError("INVALID_SHA256", `invalid ${name}`);
  }
  return value;
}

function validateTimestamp(value: unknown, name: string): string {
  if (typeof value !== "string" || !TIMESTAMP_RE.test(value)) {
    throw new BridgeContractError("INVALID_TIMESTAMP", `invalid ${name}`);
  }
  return value;
}

function validateInt(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0 || value > 2 ** 63 - 1) {
    throw new BridgeContractError("INVALID_INTEGER", `invalid ${name}`);
  }
  return value;
}

/**
 * Parse canonical timestamp string to epoch milliseconds.
 */
function parseTimestampMs(ts: string): number {
  // Format: YYYY-MM-DDTHH:MM:SS.ffffffZ
  // JS Date can parse ISO 8601; microseconds may be truncated to millis
  // Replace microseconds with milliseconds for JS Date parsing
  const match = ts.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{6})Z$/);
  if (!match) {
    throw new BridgeContractError("INVALID_TIMESTAMP", `cannot parse: ${ts}`);
  }
  const base = match[1];
  const micro = match[2];
  // Take first 3 digits as milliseconds, pad if needed
  const millis = micro.substring(0, 3).padEnd(3, "0");
  return new Date(`${base}.${millis}Z`).getTime();
}

// ---------------------------------------------------------------------------
// In-memory nonce tracker
// ---------------------------------------------------------------------------

export class InMemoryNonceTracker {
  private missionNonces: Set<string> = new Set();
  private tenantNonces: Set<string> = new Set();

  /**
   * Check if nonce is fresh and record it.
   * Returns true if fresh (and records it), false if duplicate.
   */
  checkAndRecord(missionId: string, tenantId: string, nonce: string): boolean {
    const mKey = `${missionId}\x00${nonce}`;
    const tKey = `${tenantId}\x00${nonce}`;
    if (this.missionNonces.has(mKey)) return false;
    if (this.tenantNonces.has(tKey)) return false;
    this.missionNonces.add(mKey);
    this.tenantNonces.add(tKey);
    return true;
  }

  isDuplicate(missionId: string, tenantId: string, nonce: string): boolean {
    const mKey = `${missionId}\x00${nonce}`;
    const tKey = `${tenantId}\x00${nonce}`;
    return this.missionNonces.has(mKey) || this.tenantNonces.has(tKey);
  }

  clear(): void {
    this.missionNonces.clear();
    this.tenantNonces.clear();
  }
}

// ---------------------------------------------------------------------------
// Validation: 14 fail-closed reject rules for envelopes
// ---------------------------------------------------------------------------

export interface ValidateEnvelopeOptions {
  nonceTracker?: InMemoryNonceTracker;
  expectedMissionId?: string;
  expectedTenantId?: string;
  currentTime?: string;
}

/**
 * Validate a bridge envelope against all 14 fail-closed reject rules.
 * Throws BridgeContractError on any failure.
 *
 * Reject rules:
 *   1.  Unknown schema version
 *   2.  Missing mission_id
 *   3.  Missing execution_id
 *   4.  Missing nonce
 *   5.  Missing tenant_id
 *   6.  Missing authority_decision
 *   7.  Missing capability_id
 *   8.  Payload hash mismatch
 *   9.  Expired envelope
 *   10. Revoked authority
 *   11. Cross-mission replay
 *   12. Cross-tenant replay
 *   13. Duplicate nonce
 *   14. Expired authority decision (EXPIRED)
 */
export async function validateEnvelope(
  envelope: BridgeEnvelopeV1,
  options: ValidateEnvelopeOptions = {},
): Promise<void> {
  // Rule 1: Unknown schema version
  if (envelope.schema_version !== BRIDGE_CONTRACT_VERSION) {
    throw new BridgeContractError("SCHEMA_VERSION_MISMATCH");
  }

  // Rule 2: Missing mission_id
  if (!envelope.mission_id) {
    throw new BridgeContractError("MISSING_MISSION_ID");
  }

  // Rule 3: Missing execution_id
  if (!envelope.execution_id) {
    throw new BridgeContractError("MISSING_EXECUTION_ID");
  }

  // Rule 4: Missing nonce
  if (!envelope.nonce) {
    throw new BridgeContractError("MISSING_NONCE");
  }

  // Rule 5: Missing tenant_id
  if (!envelope.tenant_id) {
    throw new BridgeContractError("MISSING_TENANT_ID");
  }

  // Rule 6: Missing authority_decision
  if (!envelope.authority_decision) {
    throw new BridgeContractError("MISSING_AUTHORITY_DECISION");
  }
  if (!AUTHORITY_DECISION_VALUES.includes(envelope.authority_decision)) {
    throw new BridgeContractError(
      "INVALID_AUTHORITY_DECISION",
      `unknown authority_decision: ${envelope.authority_decision}`,
    );
  }

  // Rule 7: Missing capability_id
  if (!envelope.capability_id) {
    throw new BridgeContractError("MISSING_CAPABILITY_ID");
  }

  // Rule 8: Payload hash mismatch
  const expectedHash = await computePayloadSha256(envelope.payload);
  if (envelope.payload_sha256 !== expectedHash) {
    throw new BridgeContractError("PAYLOAD_HASH_MISMATCH");
  }

  // Rule 9: Expired envelope
  let nowMs: number;
  if (options.currentTime) {
    nowMs = parseTimestampMs(options.currentTime);
  } else {
    nowMs = Date.now();
  }
  const expiresMs = parseTimestampMs(envelope.expires_at);
  if (nowMs > expiresMs) {
    throw new BridgeContractError("EXPIRED_ENVELOPE");
  }

  // Rule 10: Revoked authority
  if (envelope.authority_decision === "REVOKED") {
    throw new BridgeContractError("REVOKED_AUTHORITY");
  }

  // Rule 11: Cross-mission replay
  if (options.expectedMissionId && envelope.mission_id !== options.expectedMissionId) {
    throw new BridgeContractError("CROSS_MISSION_REPLAY");
  }

  // Rule 12: Cross-tenant replay
  if (options.expectedTenantId && envelope.tenant_id !== options.expectedTenantId) {
    throw new BridgeContractError("CROSS_TENANT_REPLAY");
  }

  // Rule 13: Duplicate nonce
  if (options.nonceTracker) {
    if (!options.nonceTracker.checkAndRecord(
      envelope.mission_id, envelope.tenant_id, envelope.nonce,
    )) {
      throw new BridgeContractError("DUPLICATE_NONCE");
    }
  }

  // Rule 14: Expired authority decision
  if (envelope.authority_decision === "EXPIRED") {
    throw new BridgeContractError("EXPIRED_AUTHORITY");
  }
}

export interface ValidateResultOptions {
  expectedEnvelope?: BridgeEnvelopeV1;
}

/**
 * Validate a bridge result against fail-closed invariants.
 * Throws BridgeContractError on any failure.
 *
 * Checks:
 *   - authority_delta == 0
 *   - side_effect_count == 0
 *   - evidence hash binding
 *   - schema version match
 *   - result/envelope identity binding (if expectedEnvelope provided)
 *   - malformed result evidence
 */
export async function validateResult(
  result: BridgeResultV1,
  options: ValidateResultOptions = {},
): Promise<void> {
  // Schema version
  if (result.schema_version !== BRIDGE_CONTRACT_VERSION) {
    throw new BridgeContractError("SCHEMA_VERSION_MISMATCH");
  }

  // authority_delta must be 0
  if (result.authority_delta !== 0) {
    throw new BridgeContractError("AUTHORITY_DELTA_NONZERO");
  }

  // side_effect_count must be 0
  if (result.side_effect_count !== 0) {
    throw new BridgeContractError("SIDE_EFFECT_COUNT_NONZERO");
  }

  // Malformed result evidence — must be a non-empty object
  if (!result.evidence || typeof result.evidence !== "object" || Object.keys(result.evidence).length === 0) {
    throw new BridgeContractError("MALFORMED_RESULT_EVIDENCE");
  }

  // Evidence hash binding
  const expectedHash = await computeEvidenceSha256(result.evidence);
  if (result.evidence_sha256 !== expectedHash) {
    throw new BridgeContractError("EVIDENCE_HASH_MISMATCH");
  }

  // If envelope provided, verify identity binding
  if (options.expectedEnvelope) {
    if (result.mission_id !== options.expectedEnvelope.mission_id) {
      throw new BridgeContractError("CROSS_MISSION_REPLAY");
    }
    if (result.execution_id !== options.expectedEnvelope.execution_id) {
      throw new BridgeContractError("EXECUTION_ID_MISMATCH");
    }
    if (result.nonce !== options.expectedEnvelope.nonce) {
      throw new BridgeContractError("NONCE_MISMATCH");
    }
  }
}

// ---------------------------------------------------------------------------
// Contract artifact (immutable)
// ---------------------------------------------------------------------------

export function contractArtifact(): string {
  const lines = [
    `BRIDGE_CONTRACT_VERSION = ${BRIDGE_CONTRACT_VERSION}`,
    "IDENTITY_BINDINGS = [mission_id, execution_id, nonce, tenant_id, actor_id]",
    "AUTHORITY_BINDINGS = [authority_decision, consequence_class, capability_id]",
    "INTEGRITY_BINDINGS = [payload_sha256, evidence_sha256]",
    "TEMPORAL_BINDINGS = [issued_at, expires_at]",
    "RESULT_INVARIANTS = [authority_delta, side_effect_count, status]",
  ];
  return lines.join("\n");
}

export async function computeContractSha256(): Promise<string> {
  const artifact = contractArtifact();
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(artifact),
  );
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}