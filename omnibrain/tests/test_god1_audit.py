"""SP-GOD1-SWARMS-001 Phase 20 — swarm lifecycle audit events."""
from __future__ import annotations

from omnibrain.swarms import make_swarm_identity


class TestSwarmLifecycleAudit:
    def test_swarm_identity_is_audit_ready(self):
        ident = make_swarm_identity(
            mission_id="M-1", swarm_type="BUILD", authority_id="AUTH-1",
            principal_origin="principal", parent_execution_id="EXEC-1",
            coordinator_agent_id="agent.coordinator",
            member_agent_ids={"agent.w1", "agent.w2"})
        # every field the audit event requires is present on the identity
        assert ident.swarm_id
        assert ident.mission_id
        assert ident.authority_id
        assert ident.principal_origin == "principal"
        assert ident.coordinator_agent_id
        assert ident.member_agent_ids

    def test_audit_trail_records_swarm_events(self):
        import inspect
        import tempfile
        from pathlib import Path

        from governance.audit_trail import AuditTrail
        tmp = Path(tempfile.mkdtemp())
        kwargs = {"db_path": tmp / "audit.db"} if "db_path" in inspect.signature(
            AuditTrail.__init__).parameters else {}
        trail = AuditTrail(**kwargs)
        trail.log(actor="agent.coordinator", action="SWARM_CREATED", outcome="PROPOSED",
                  risk_level=__import__("governance.risk_types", fromlist=["RiskLevel"]).RiskLevel.MEDIUM,
                  metadata={"swarm_id": "S-1", "mission_id": "M-1"})
        entries = trail.query(actor="agent.coordinator")
        assert any(getattr(e, "action", "") == "SWARM_CREATED" for e in entries)
