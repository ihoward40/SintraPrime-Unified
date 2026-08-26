/**
 * TypeScript-side authority validation adapter for the V1 bridge contract.
 *
 * This module is the TS mirror of Python's bridge authority propagation
 * patterns (sintra_live/l2/bridge_envelope_contract.py — the authority
 * validation rules embedded in validate_envelope / validate_result).
 *
 * Design rules:
 *   - It does NOT create a second authority model.
 *   - AuthorityDecision values are PROJECTIONS of existing governed
 *     authority semantics, not a new authority model.
 *   - authority_delta MUST be 0 — no direct authority expansion.
 *   - Validation/propagation only — no privilege inference from caller.
 *   - Fail-closed on all violations (throws BridgeContractError).
 *   - No new authority model — validation/propagation only.
 */

import {
  AuthorityDecision,
  AUTHORITY_DECISION_VALUES,
  BridgeContractError,
  BridgeEnvelopeV1,
  BridgeResultV1,
} from "./bridgeContract";

// ---------------------------------------------------------------------------
// Authority decision validation
// ---------------------------------------------------------------------------

/**
 * Allowed authority decisions that permit execution to proceed.
 * Only ALLOW is an affirmative grant; the rest are deny/defer variants.
 */
const EXECUTION_PERMITTING_DECISIONS: ReadonlySet<AuthorityDecision> = new Set([
  "ALLOW",
]);

/**
 * Authority decisions that represent expired or revoked authority.
 * These are always rejected at the envelope level (fail-closed).
 */
const EXPIRED_OR_REVOKED: ReadonlySet<AuthorityDecision> = new Set([
  "EXPIRED",
  "REVOKED",
]);

/**
 * Validate that an authority_decision value is in the allowed set
 * defined by the V1 contract (AUTHORITY_DECISION_VALUES).
 *
 * Mirrors Python's _validate_authority_decision() in
 * bridge_envelope_contract.py.
 *
 * @param value - The authority_decision field to validate
 * @returns The validated AuthorityDecision value
 * @throws BridgeContractError with rule INVALID_AUTHORITY_DECISION
 *   if the value is not a string or not in the allowed set
 */
export function validateAuthorityDecision(value: unknown): AuthorityDecision {
  if (typeof value !== "string") {
    throw new BridgeContractError(
      "INVALID_AUTHORITY_DECISION",
      "authority_decision must be a string",
    );
  }
  if (!AUTHORITY_DECISION_VALUES.includes(value as AuthorityDecision)) {
    throw new BridgeContractError(
      "INVALID_AUTHORITY_DECISION",
      `unknown authority_decision: ${value}`,
    );
  }
  return value as AuthorityDecision;
}

/**
 * Check that authority_delta == 0.
 *
 * The bridge contract invariant: no direct authority expansion across
 * the runtime boundary. authority_delta must always be 0.
 *
 * Mirrors Python's validate_result() authority_delta check in
 * bridge_envelope_contract.py.
 *
 * @param delta - The authority_delta value to check
 * @throws BridgeContractError with rule AUTHORITY_DELTA_NONZERO
 *   if delta is not 0
 */
export function checkAuthorityDelta(delta: unknown): void {
  if (typeof delta !== "number" || !Number.isInteger(delta) || delta !== 0) {
    throw new BridgeContractError(
      "AUTHORITY_DELTA_NONZERO",
      `authority_delta must be 0, got ${delta}`,
    );
  }
}

// ---------------------------------------------------------------------------
// Authority propagation helpers
// ---------------------------------------------------------------------------

/**
 * Check whether the authority decision permits execution to proceed.
 * Only "ALLOW" is an affirmative grant.
 *
 * @param decision - The validated AuthorityDecision
 * @returns true if execution may proceed, false otherwise
 */
export function isExecutionPermitting(decision: AuthorityDecision): boolean {
  return EXECUTION_PERMITTING_DECISIONS.has(decision);
}

/**
 * Check whether the authority decision represents expired or revoked
 * authority. These are always rejected at the envelope level.
 *
 * @param decision - The validated AuthorityDecision
 * @returns true if the authority is expired or revoked
 */
export function isExpiredOrRevoked(decision: AuthorityDecision): boolean {
  return EXPIRED_OR_REVOKED.has(decision);
}

/**
 * Propagate authority from an envelope to a result.
 *
 * The bridge contract invariant: authority_delta is always 0 —
 * the result carries the same authority as the envelope, with no
 * expansion. This function verifies that invariant holds.
 *
 * @param envelope - The source envelope (authority carried forward)
 * @param result - The result to verify
 * @throws BridgeContractError if authority_delta != 0
 */
export function propagateAuthority(
  envelope: BridgeEnvelopeV1,
  result: BridgeResultV1,
): void {
  // Authority delta must be 0 — no expansion across the bridge
  checkAuthorityDelta(result.authority_delta);

  // Identity binding: the result must carry the same mission/execution
  // identity as the envelope. This is not authority expansion — it is
  // verification that the result belongs to the same governed execution.
  if (result.mission_id !== envelope.mission_id) {
    throw new BridgeContractError("CROSS_MISSION_REPLAY");
  }
}

// ---------------------------------------------------------------------------
// AuthorityValidator class
// ---------------------------------------------------------------------------

/**
 * Validator for authority fields on V1 bridge envelopes and results.
 *
 * This class encapsulates the fail-closed authority validation rules
 * from the V1 contract. It does NOT create a new authority model —
 * it validates and propagates existing governed authority semantics.
 *
 * Usage:
 *   const validator = new AuthorityValidator();
 *   validator.validate(envelope);          // validates authority_decision
 *   validator.validateResult(result);      // validates authority_delta
 *   validator.canExecute(envelope);        // checks if execution permitted
 */
export class AuthorityValidator {
  /**
   * Validate the authority_decision field on a V1 bridge envelope.
   *
   * Checks:
   *   - authority_decision is a valid AuthorityDecision value
   *   - authority_decision is not EXPIRED (expired authority)
   *   - authority_decision is not REVOKED (revoked authority)
   *
   * @param envelope - The envelope to validate
   * @throws BridgeContractError on any validation failure
   */
  validate(envelope: BridgeEnvelopeV1): void {
    // Validate the decision value is in the allowed set
    const decision = validateAuthorityDecision(envelope.authority_decision);

    // Reject expired authority (fail-closed)
    if (decision === "EXPIRED") {
      throw new BridgeContractError("EXPIRED_AUTHORITY");
    }

    // Reject revoked authority (fail-closed)
    if (decision === "REVOKED") {
      throw new BridgeContractError("REVOKED_AUTHORITY");
    }
  }

  /**
   * Validate the authority_delta invariant on a V1 bridge result.
   *
   * Checks:
   *   - authority_delta == 0 (no authority expansion)
   *
   * @param result - The result to validate
   * @throws BridgeContractError if authority_delta != 0
   */
  validateResult(result: BridgeResultV1): void {
    checkAuthorityDelta(result.authority_delta);
  }

  /**
   * Check whether the envelope's authority decision permits execution
   * to proceed. Only "ALLOW" is an affirmative grant.
   *
   * This does NOT validate the envelope — use validate() first.
   * This is a predicate for the execution flow after validation passes.
   *
   * @param envelope - The validated envelope
   * @returns true if execution may proceed, false otherwise
   */
  canExecute(envelope: BridgeEnvelopeV1): boolean {
    return isExecutionPermitting(envelope.authority_decision);
  }

  /**
   * Validate authority on both the envelope and the resulting
   * authority propagation to a result. This is the full authority
   * propagation check across the bridge boundary.
   *
   * @param envelope - The source envelope
   * @param result - The result produced from execution
   * @throws BridgeContractError on any validation failure
   */
  validatePropagation(
    envelope: BridgeEnvelopeV1,
    result: BridgeResultV1,
  ): void {
    this.validate(envelope);
    this.validateResult(result);
    propagateAuthority(envelope, result);
  }
}