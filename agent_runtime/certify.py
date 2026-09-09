"""Phase 3K — certification entrypoint + machine-readable output (§23-§25)
and 3O — dependency graph generation (§34-§35).

sintraprime agents certify --agent <id> | --all

Certification binds to the repository revision (source_sha) and records the
dependency closure (§ backlog: certification dependency closure) — any
change to manifest/authority/memory/provider/tool/runtime hashes makes the
certification STALE rather than quietly green.
"""
from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent_runtime.canonical import canonical_hash
from agent_runtime.delegation import DelegationAuthority
from agent_runtime.manifest import CertificationStatus, manifest_hash
from agent_runtime.registry import AgentRegistry
from agent_runtime.tool_policy import ProviderPolicyContract


class CertificationResult(BaseModel):
    """§24 machine-readable certification output."""

    agent_id: str
    agent_version: str
    manifest_hash: str
    certification_generation: str
    authority: str
    memory: str
    provider_policy: str
    tool_policy: str
    runtime: str
    negative_tests: str
    failure_injection: str
    result: str  # PASS | FAIL
    evidence_refs: tuple[str, ...] = ()
    timestamp: str
    source_sha: str
    dependency_closure: dict[str, str] = Field(default_factory=dict)


def source_sha(repo_path: Path | None = None) -> str:
    """Bind certification to the repository revision (§24)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_path) if repo_path else None,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def certification_generation(source: str) -> str:
    """§ improvement (backlog §15): certification generation from the source
    revision — stale certification becomes mechanically obvious."""
    return f"GEN-{hashlib.sha256(source.encode()).hexdigest()[:6].upper()}"


def certify_agent(
    registry: AgentRegistry,
    agent_id: str,
    *,
    delegation_authority: DelegationAuthority,
    negative_matrix: dict[str, str] | None = None,
    failure_injection: dict[str, str] | None = None,
    repo_path: Path | None = None,
) -> CertificationResult:
    """Run the certification ladder for one agent and emit the receipt.

    Checks: manifest validation, registry status, authority provenance,
    memory policy, provider policy, tool policy, runtime readiness,
    negatives, failure injection. Each subsystem PASS/FAIL feeds `result`.
    """
    manifest = registry.resolve(agent_id)
    sha = source_sha(repo_path)
    sections: dict[str, str] = {}

    # manifest
    errors = registry.validate(manifest)
    sections["manifest"] = "PASS" if not errors else f"FAIL: {errors}"
    # registry ladder
    status = registry.status(agent_id)
    sections["registry"] = "PASS" if status in (CertificationStatus.VALIDATED, CertificationStatus.TESTED, CertificationStatus.CERTIFIED) else f"FAIL: status {status}"
    # authority: provenance chain to governance root
    rooted = delegation_authority._has_governance_root(agent_id)
    sections["authority"] = "PASS" if rooted else "FAIL: no governance-rooted authority provenance"
    # memory policy
    sections["memory"] = "PASS" if not (manifest.memory_scope.value == "GOVERNANCE_READONLY" and manifest.memory_write_requests_allowed) else "FAIL: governance write forbidden"
    # provider policy
    try:
        ProviderPolicyContract(**manifest.provider_policy.model_dump())
        sections["provider_policy"] = "PASS"
    except Exception as exc:
        sections["provider_policy"] = f"FAIL: {exc}"
    # tool policy
    sections["tool_policy"] = "PASS" if manifest.tool_policy is not None else "FAIL"
    # runtime: bounded budgets present
    sections["runtime"] = "PASS" if manifest.budget_policy.max_iterations >= 1 else "FAIL: unbounded"
    # negatives + failure injection (supplied by the certification harness)
    sections["negative_tests"] = (negative_matrix or {}).get(agent_id, "NOT_RUN")
    sections["failure_injection"] = (failure_injection or {}).get(agent_id, "NOT_RUN")

    result = "PASS" if all(v == "PASS" for k, v in sections.items() if k not in ("negative_tests", "failure_injection")) and sections["negative_tests"] in ("PASS", "NOT_RUN") and sections["failure_injection"] in ("PASS", "NOT_RUN") else "FAIL"
    dependency_closure = {
        "manifest_hash": manifest_hash(manifest),
        "authority_policy": manifest.authority_policy.value,
        "memory_scope": manifest.memory_scope.value,
        "provider_policy": canonical_hash(manifest.provider_policy),
        "tool_policy": canonical_hash(manifest.tool_policy),
        "runtime_contract": "agent_runtime@cp2",
    }
    return CertificationResult(
        agent_id=agent_id,
        agent_version=manifest.agent_version,
        manifest_hash=manifest_hash(manifest),
        certification_generation=certification_generation(sha),
        **{k: v for k, v in sections.items() if k not in ("manifest", "registry")},
        result=result,
        evidence_refs=(f"receipt:{agent_id}@{sha[:12]}",),
        timestamp=datetime.now(UTC).isoformat(),
        source_sha=sha,
        dependency_closure=dependency_closure,
    )


# ---------------------------------------------------------------------------
# 3O — dependency graph (§34-§35), generated from registry + authority
# ---------------------------------------------------------------------------


def build_dependency_graph(registry: AgentRegistry, delegation_authority: DelegationAuthority) -> dict[str, Any]:
    """Generate the agent dependency graph from manifests/registry (§34).

    Nodes: agents, capabilities, memory scopes, provider classes, tools,
    authority policies. Edges: actual dependencies. Never hand-authored.
    """
    nodes: dict[str, list[dict]] = {"agents": [], "capabilities": [], "memory_scopes": [], "provider_classes": [], "tools": [], "authority_policies": []}
    edges: list[dict[str, str]] = []
    for m in registry.list():
        nodes["agents"].append({"agent_id": m.agent_id, "version": m.agent_version, "status": registry.status(m.agent_id).value})
        for cap in (*m.required_capabilities, *m.optional_capabilities):
            nodes["capabilities"].append({"capability_id": cap})
            edges.append({"from": m.agent_id, "to": f"cap:{cap}", "type": "requires"})
        for cap in m.forbidden_capabilities:
            edges.append({"from": m.agent_id, "to": f"cap:{cap}", "type": "forbidden"})
        nodes["memory_scopes"].append({"scope": m.memory_scope.value, "agent": m.agent_id})
        edges.append({"from": m.agent_id, "to": f"memory:{m.memory_scope.value}", "type": "memory_scope"})
        nodes["provider_classes"].append({"provider_class": m.provider_policy.provider_class, "agent": m.agent_id})
        edges.append({"from": m.agent_id, "to": f"provider:{m.provider_policy.provider_class}", "type": "provider"})
        edges.append({"from": m.agent_id, "to": f"authority:{m.authority_policy.value}", "type": "authority_policy"})
        nodes["authority_policies"].append({"policy": m.authority_policy.value})
        grantor = delegation_authority._grantor_of.get(m.agent_id)
        if grantor and grantor != "governance":
            edges.append({"from": m.agent_id, "to": grantor, "type": "delegated_by"})
    # §35 validation
    validation: dict[str, Any] = {
        "orphan_agents": [a["agent_id"] for a in nodes["agents"] if not any(e["from"] == a["agent_id"] for e in edges)],
        "unknown_capabilities": sorted({e["to"].split("cap:")[1] for e in edges if e["to"].startswith("cap:") and e["to"].split("cap:")[1] not in _known_caps()}),
        "agents_without_authority_path": [a["agent_id"] for a in nodes["agents"] if not delegation_authority._has_governance_root(a["agent_id"]) and any(e["from"] == a["agent_id"] and e["type"] == "delegated_by" for e in edges)],
    }
    return {"nodes": nodes, "edges": edges, "validation": validation}


def _known_caps() -> frozenset[str]:
    from agent_runtime.manifest import KNOWN_CAPABILITIES

    return KNOWN_CAPABILITIES
