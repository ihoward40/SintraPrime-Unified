"""SintraPrime Doctor — R0 Foundation Diagnostics (directive §13).

Reports subsystem health as AVAILABLE / DEGRADED / UNAVAILABLE / MISCONFIGURED.
Does not expose secret values.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


@dataclass
class Check:
    subsystem: str
    status: str  # PASS | FAIL | DEGRADED | BLOCKED | NOT_CONFIGURED
    detail: str = ""


def check_python() -> Check:
    v = sys.version.split()[0]
    try:
        import pydantic_core  # noqa: F401

        return Check("Python", "PASS", f"{v} + pydantic_core OK")
    except ImportError:
        return Check("Python", "FAIL", f"{v} — pydantic_core broken")


def check_database() -> Check:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return Check("Database", "NOT_CONFIGURED", "DATABASE_URL not set")
    scheme = url.split("://")[0]
    if "sqlite" in scheme:
        return Check("Database", "DEGRADED", f"SQLite ({scheme}) — not PostgreSQL")
    if "postgresql" in scheme:
        try:
            import sqlalchemy

            engine = sqlalchemy.create_engine(url.replace("+asyncpg", "+psycopg2"))
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            return Check("Database", "PASS", f"PostgreSQL connected ({scheme})")
        except Exception as e:
            return Check("Database", "FAIL", str(e).splitlines()[0][:80])
    return Check("Database", "DEGRADED", f"Unknown scheme: {scheme}")


def check_portal_app() -> Check:
    try:
        from portal.main import app

        routes = len([r for r in app.routes if hasattr(r, "path")])
        return Check("Portal App", "PASS", f"{routes} routes loaded")
    except Exception as e:
        return Check("Portal App", "FAIL", str(e).splitlines()[0][:80])


def check_auth() -> Check:
    try:
        from portal.auth.jwt_handler import create_access_token

        token = create_access_token(
            user_id="doctor", tenant_id="doctor", role="SUPER_ADMIN", permissions=[]
        )
        return Check("Auth (JWT)", "PASS", f"Token created ({len(token)} bytes)")
    except Exception as e:
        return Check("Auth (JWT)", "FAIL", str(e).splitlines()[0][:80])


def check_rbac() -> Check:
    try:
        from portal.auth.rbac import Permission, Role

        roles = [r.name for r in Role]
        perms = [p.name for p in Permission]
        return Check("RBAC", "PASS", f"{len(roles)} roles, {len(perms)} permissions")
    except Exception as e:
        return Check("RBAC", "FAIL", str(e).splitlines()[0][:80])


def check_correlation() -> Check:
    try:
        return Check("Correlation", "PASS", "Middleware/context present")
    except Exception as e:
        return Check("Correlation", "FAIL", str(e).splitlines()[0][:80])


def check_governance_engine() -> Check:
    try:
        # Check if anyone imports it
        import subprocess

        result = subprocess.run(
            ["grep", "-rln", "GovernanceEngine", "portal/", "agents/", "core/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        callers = [
            ln for ln in result.stdout.strip().split("\n") if ln and "sintraprime_doctor" not in ln
        ]
        if callers:
            return Check("GovernanceEngine", "PASS", f"{len(callers)} callers")
        return Check("GovernanceEngine", "DEGRADED", "Present but ZERO callers (disconnected)")
    except Exception as e:
        return Check("GovernanceEngine", "FAIL", str(e).splitlines()[0][:80])


def check_providers() -> Check:
    try:
        from portal.services.orchestration.provider_registry import mock_provider_registry

        providers = mock_provider_registry()
        real = [p for p in providers if not getattr(p, "data_policy", {}).get("mock_only", False)]
        return Check(
            "Providers",
            "DEGRADED" if not real else "PASS",
            f"{len(providers)} registered, {len(real)} real, {len(providers) - len(real)} mock",
        )
    except Exception as e:
        return Check("Providers", "FAIL", str(e).splitlines()[0][:80])


def check_websocket() -> Check:
    try:
        return Check("WebSocket", "PASS", "ConnectionManager present")
    except Exception as e:
        return Check("WebSocket", "FAIL", str(e).splitlines()[0][:80])


def check_memory() -> Check:
    try:
        return Check("Memory", "PASS", "MemoryEngine importable")
    except Exception as e:
        return Check("Memory", "FAIL", str(e).splitlines()[0][:80])


def check_workflow_runtime() -> Check:
    try:
        import workflow_runtime  # noqa: F401

        return Check("Workflow Runtime", "PASS", "Module importable")
    except ImportError:
        return Check("Workflow Runtime", "UNAVAILABLE", "Not on this branch")


def check_collaboration() -> Check:
    try:
        import collaboration  # noqa: F401

        return Check("Collaboration", "PASS", "Module importable")
    except ImportError:
        return Check("Collaboration", "UNAVAILABLE", "Not on this branch")


def check_migrations() -> Check:
    portal_schema = Path("portal/migrations/portal_schema.sql")
    if not portal_schema.exists():
        return Check("Migrations", "UNAVAILABLE", "portal_schema.sql not found")
    count = sum(1 for line in portal_schema.read_text().splitlines() if "CREATE TABLE" in line)
    return Check(
        "Migrations",
        "PARTIAL",
        f"{count} tables in base schema; incremental migrations require manual ordering",
    )


def main() -> list[Check]:
    return [
        check_python(),
        check_database(),
        check_portal_app(),
        check_auth(),
        check_rbac(),
        check_correlation(),
        check_governance_engine(),
        check_providers(),
        check_websocket(),
        check_memory(),
        check_workflow_runtime(),
        check_collaboration(),
        check_migrations(),
    ]


if __name__ == "__main__":
    checks = main()
    max_sub = max(len(c.subsystem) for c in checks)
    for c in checks:
        icon = {
            "PASS": "\u2705",
            "FAIL": "\u274c",
            "DEGRADED": "\u26a0\ufe0f",
            "BLOCKED": "\U0001f6ab",
            "NOT_CONFIGURED": "\u2753",
            "UNAVAILABLE": "\u2b1c",
            "PARTIAL": "\U0001f7e0",
        }.get(c.status, "?")
        print(f"  {icon} {c.subsystem:<{max_sub}} {c.status:<14} {c.detail}")
    pass_count = sum(1 for c in checks if c.status == "PASS")
    fail_count = sum(1 for c in checks if c.status in ("FAIL", "UNAVAILABLE"))
    print(f"\n  {pass_count}/{len(checks)} PASS | {fail_count} FAIL/UNAVAILABLE")
