"""Disposable Gate 4B E1 adapter with no network or production reachability.

`sandbox.echo-write-v1` writes only to the certification table in the canonical
PostgreSQL database. It has no credential resolver, HTTP client, filesystem write,
or production hostname/destination support.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.external_action_sandbox import SandboxEchoEffect

ADAPTER_ID = "sandbox.echo-write-v1"
OPERATION_ID = "echo_write"
ENVIRONMENT = "sandbox"
DESTINATION_PREFIX = "sandbox://gate4b/"


class SandboxAdapterError(ValueError):
    """Raised when a request escapes the disposable Gate 4B contract."""


def canonical_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class SandboxEchoAdapter:
    adapter_id = ADAPTER_ID
    operation_id = OPERATION_ID
    environment = ENVIRONMENT
    compensation = "reversible"

    @staticmethod
    def validate_destination(destination: str) -> None:
        if not destination.startswith(DESTINATION_PREFIX):
            raise SandboxAdapterError("Gate 4B destination is outside the disposable sandbox")
        if ".." in destination or destination.endswith("/"):
            raise SandboxAdapterError("Gate 4B destination is malformed")

    @staticmethod
    def canonicalize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if not isinstance(payload, dict) or not payload:
            raise SandboxAdapterError("Sandbox payload must be a non-empty object")
        canonical = json.loads(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        )
        return canonical, canonical_json_hash(canonical)

    def preflight(self, *, destination: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.validate_destination(destination)
        canonical, payload_hash = self.canonicalize_payload(payload)
        receipt = {
            "adapter_id": self.adapter_id,
            "operation_id": self.operation_id,
            "environment": self.environment,
            "destination": destination,
            "payload_hash": payload_hash,
            "payload": canonical,
            "network_access": False,
            "credential_access": False,
            "production_reachable": False,
            "compensation": self.compensation,
        }
        receipt["receipt_hash"] = canonical_json_hash(receipt)
        return receipt

    async def execute_once(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        destination: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self.validate_destination(destination)
        canonical, payload_hash = self.canonicalize_payload(payload)
        existing = await db.scalar(
            select(SandboxEchoEffect).where(
                SandboxEchoEffect.tenant_id == tenant_id,
                SandboxEchoEffect.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return self._effect_result(existing, duplicate=True)

        confirmation_id = f"sandbox-confirm-{uuid.uuid4().hex[:16]}"
        effect = SandboxEchoEffect(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            destination=destination,
            idempotency_key=idempotency_key,
            payload=canonical,
            payload_hash=payload_hash,
            confirmation_id=confirmation_id,
        )
        db.add(effect)
        await db.flush()
        return self._effect_result(effect, duplicate=False)

    async def reconcile_unknown_outcome(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        effect = await db.scalar(
            select(SandboxEchoEffect).where(
                SandboxEchoEffect.tenant_id == tenant_id,
                SandboxEchoEffect.idempotency_key == idempotency_key,
            )
        )
        return self._effect_result(effect, duplicate=True) if effect is not None else None

    async def compensate(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        effect = await db.scalar(
            select(SandboxEchoEffect).where(
                SandboxEchoEffect.tenant_id == tenant_id,
                SandboxEchoEffect.idempotency_key == idempotency_key,
            )
        )
        if effect is None:
            return None
        if effect.compensated_at is None:
            from datetime import UTC, datetime

            effect.compensated_at = datetime.now(UTC)
            await db.flush()
        return self._effect_result(effect, duplicate=False)

    @staticmethod
    def _effect_result(effect: SandboxEchoEffect, *, duplicate: bool) -> dict[str, Any]:
        return {
            "effect_id": effect.id,
            "destination": effect.destination,
            "payload_hash": effect.payload_hash,
            "confirmation_id": effect.confirmation_id,
            "duplicate": duplicate,
            "compensated": effect.compensated_at is not None,
        }


sandbox_echo_adapter = SandboxEchoAdapter()
