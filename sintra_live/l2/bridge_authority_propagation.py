"""Authority decision binding and propagation for the Python<->TypeScript bridge.

This module is a propagation/validation adapter ONLY. It does NOT create a new
authority model. It binds a resolved authority decision from the existing L2
authority resolver to a BridgeEnvelopeV1 and validates the authority_delta
invariant at result time.

Design rules:
  * The bridge confers NO authority -- it propagates and validates.
  * authority_delta must always be 0 unless explicitly authorized.
  * Reuses AuthorityDecision enum from bridge_envelope_contract.py.
  * All validation is fail-closed.

Contract compliance:
  BRIDGE_CONTRACT_SHA256 = 7c08de2fc06a3698d40c0d947d77ea2915419d4354e459de95e2dfc1e199a062
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from sintra_live.l2.bridge_envelope_contract import (
    AuthorityDecision,
    BridgeEnvelopeV1,
    BridgeValidationError,
    compute_payload_sha256,
)

__all__ = [
    "AuthorityPropagator",
    "propagate_authority",
    "check_authority_delta",
]


class AuthorityPropagator:
    """Binds a resolved authority decision to a BridgeEnvelopeV1.

    This is a propagation adapter -- it does NOT make authority decisions.
    It takes an already-resolved authority decision string and binds it to
    the bridge envelope. Construction of BridgeEnvelopeV1 validates schema
    version, identifiers, hash binding, and that the decision is a known
    AuthorityDecision value.

    Full fail-closed validation (expiry, nonce replay, revoked checks) is
    performed separately via validate_envelope() or the replay protection
    module.
    """

    def __init__(self, authority_decision: str) -> None:
        """Initialize with a resolved authority decision string.

        Validates that the decision is a known AuthorityDecision value.
        Raises BridgeValidationError if the value is unknown.
        """
        self._authority_decision = self._validate_decision(authority_decision)

    @staticmethod
    def _validate_decision(decision: str) -> str:
        """Validate that the decision is a known AuthorityDecision value."""
        if not isinstance(decision, str):
            raise BridgeValidationError(
                "INVALID_AUTHORITY_DECISION",
                "authority_decision must be a string",
            )
        try:
            return AuthorityDecision(decision).value
        except ValueError:
            raise BridgeValidationError(
                "INVALID_AUTHORITY_DECISION",
                f"unknown authority_decision: {decision}",
            )

    @property
    def authority_decision(self) -> str:
        """The bound authority decision string."""
        return self._authority_decision

    def bind_to_envelope(self, **envelope_fields: Any) -> BridgeEnvelopeV1:
        """Bind the authority decision to a BridgeEnvelopeV1.

        The caller provides all envelope fields. If ``authority_decision`` is
        included in ``envelope_fields`` it must match the propagator's value;
        otherwise the propagator's value is injected automatically.

        Returns the constructed, construction-validated BridgeEnvelopeV1.
        Raises BridgeValidationError on any construction-time validation
        failure (schema mismatch, invalid identifier, hash mismatch, unknown
        authority decision, etc.).
        """
        if "authority_decision" in envelope_fields:
            if envelope_fields["authority_decision"] != self._authority_decision:
                raise BridgeValidationError(
                    "AUTHORITY_DECISION_MISMATCH",
                    f"envelope authority_decision "
                    f"'{envelope_fields['authority_decision']}' "
                    f"does not match propagator decision "
                    f"'{self._authority_decision}'",
                )
        else:
            envelope_fields["authority_decision"] = self._authority_decision

        return BridgeEnvelopeV1(**envelope_fields)


def propagate_authority(
    authority_decision: str,
    *,
    schema_version: str,
    mission_id: str,
    execution_id: str,
    nonce: str,
    tenant_id: str,
    actor_id: str,
    consequence_class: str,
    capability_id: str,
    payload: Dict[str, Any],
    issued_at: str,
    expires_at: str,
    provenance: str,
    payload_sha256: str | None = None,
) -> BridgeEnvelopeV1:
    """Bind an authority_decision to a BridgeEnvelopeV1 and return it.

    Given an authority_decision string and the remaining envelope fields,
    construct and return the bound envelope. The payload hash is computed
    automatically if not provided.

    This is a convenience function wrapping AuthorityPropagator.

    Raises BridgeValidationError on any construction-time validation failure.
    """
    propagator = AuthorityPropagator(authority_decision)

    fields: Dict[str, Any] = dict(
        schema_version=schema_version,
        mission_id=mission_id,
        execution_id=execution_id,
        nonce=nonce,
        tenant_id=tenant_id,
        actor_id=actor_id,
        authority_decision=authority_decision,
        consequence_class=consequence_class,
        capability_id=capability_id,
        payload=payload,
        payload_sha256=(
            payload_sha256
            if payload_sha256 is not None
            else compute_payload_sha256(payload)
        ),
        issued_at=issued_at,
        expires_at=expires_at,
        provenance=provenance,
    )

    return propagator.bind_to_envelope(**fields)


def check_authority_delta(authority_delta: int) -> Tuple[bool, str]:
    """Verify that authority_delta == 0 at result time.

    The bridge must not change authority. authority_delta must always be 0
    unless explicitly authorized -- and the bridge never authorizes a change.

    Returns:
        (True, "OK") if authority_delta == 0.
        (False, "AUTHORITY_DELTA_NONZERO") if authority_delta != 0.
    """
    if not isinstance(authority_delta, int) or isinstance(authority_delta, bool):
        return (False, "AUTHORITY_DELTA_NONZERO")
    if authority_delta != 0:
        return (False, "AUTHORITY_DELTA_NONZERO")
    return (True, "OK")