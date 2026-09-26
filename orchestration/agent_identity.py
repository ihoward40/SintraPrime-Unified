"""Authentication boundary for A2A agent principals.

Credentials are injected through A2A_AGENT_CREDENTIALS as a JSON object mapping
opaque tokens to {agent_id, tenant_id}. Tokens must be provisioned by the
runtime secret manager and are never stored in the registry or message body.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPrincipal:
    agent_id: str
    tenant_id: str


def authenticate_agent(token: str | None, tenant_id: str | None = None) -> AgentPrincipal:
    if not token:
        raise PermissionError("A2A authentication required")
    raw = os.getenv("A2A_AGENT_CREDENTIALS", "{}")
    try:
        credentials = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("A2A_AGENT_CREDENTIALS is not valid JSON") from exc
    entry = credentials.get(token)
    if not isinstance(entry, dict) or not entry.get("agent_id") or not entry.get("tenant_id"):
        raise PermissionError("A2A authentication failed")
    principal = AgentPrincipal(agent_id=str(entry["agent_id"]), tenant_id=str(entry["tenant_id"]))
    if tenant_id is not None and tenant_id != principal.tenant_id:
        raise PermissionError("A2A tenant scope mismatch")
    return principal
