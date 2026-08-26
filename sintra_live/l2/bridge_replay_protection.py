"""Nonce tracking and replay denial for the Python<->TypeScript bridge.

In-memory replay protection suitable for testing and single-process use.
Tracks nonces per (mission_id, tenant_id) pair and rejects:

  * Duplicate nonce on same mission+tenant
  * Cross-mission replay (same nonce, different mission_id)
  * Cross-tenant replay (same nonce, different tenant_id)

Also provides standalone checks for envelope expiry and revoked authority.

Design rules:
  * All checks return (allowed: bool, reason: str).
  * All validation is fail-closed.
  * BRIDGE_CONTRACT_SHA256 = 7c08de2fc06a3698d40c0d947d77ea2915419d4354e459de95e2dfc1e199a062
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Set, Tuple

from sintra_live.l2.bridge_envelope_contract import AuthorityDecision

__all__ = [
    "NonceTracker",
    "check_expiry",
    "check_revoked",
]


class NonceTracker:
    """In-memory nonce tracker for replay protection.

    Tracks which (mission_id, tenant_id) pairs have used each nonce and
    rejects duplicates, cross-mission replay, and cross-tenant replay.

    Suitable for testing and single-process use. In production this would
    be backed by a durable store.
    """

    def __init__(self) -> None:
        # nonce -> set of (mission_id, tenant_id) pairs that have used it
        self._nonce_owners: Dict[str, Set[Tuple[str, str]]] = {}

    def check_nonce(
        self, mission_id: str, tenant_id: str, nonce: str
    ) -> Tuple[bool, str]:
        """Check if a nonce is fresh for the given (mission_id, tenant_id).

        If the nonce is fresh, it is recorded and (True, "OK") is returned.
        If the nonce has been seen before, the call is rejected:

          * Same (mission_id, tenant_id) -> (False, "DUPLICATE_NONCE")
          * Different mission_id         -> (False, "CROSS_MISSION_REPLAY")
          * Different tenant_id          -> (False, "CROSS_TENANT_REPLAY")

        Cross-mission is checked before cross-tenant when both differ.
        """
        owners = self._nonce_owners.get(nonce)

        if owners:
            # Rule 1: exact duplicate on same mission+tenant
            if (mission_id, tenant_id) in owners:
                return (False, "DUPLICATE_NONCE")

            # Rule 2 & 3: cross-mission or cross-tenant replay
            for (existing_mission, existing_tenant) in owners:
                if existing_mission != mission_id:
                    return (False, "CROSS_MISSION_REPLAY")
                if existing_tenant != tenant_id:
                    return (False, "CROSS_TENANT_REPLAY")

        # Fresh nonce -- record it
        self._nonce_owners.setdefault(nonce, set()).add((mission_id, tenant_id))
        return (True, "OK")

    def clear(self) -> None:
        """Clear all tracked nonces."""
        self._nonce_owners.clear()


def check_expiry(expires_at: str) -> Tuple[bool, str]:
    """Check if an envelope has expired.

    Given an ``expires_at`` timestamp in canonical format
    (``YYYY-MM-DDTHH:MM:SS.ffffffZ``), reject if it is past the current
    UTC time.

    Returns:
        (True, "OK") if the envelope has not expired.
        (False, "EXPIRED_ENVELOPE") if expires_at < current UTC time.
    """
    try:
        dt = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return (False, "EXPIRED_ENVELOPE")

    now = datetime.now(timezone.utc)
    if now > dt:
        return (False, "EXPIRED_ENVELOPE")
    return (True, "OK")


def check_revoked(authority_decision: str) -> Tuple[bool, str]:
    """Check if authority has been revoked.

    Given an ``authority_decision`` string, reject if it is ``REVOKED``.

    Returns:
        (True, "OK") if the authority is not revoked.
        (False, "REVOKED_AUTHORITY") if authority_decision == "REVOKED".
    """
    if authority_decision == AuthorityDecision.REVOKED.value:
        return (False, "REVOKED_AUTHORITY")
    return (True, "OK")