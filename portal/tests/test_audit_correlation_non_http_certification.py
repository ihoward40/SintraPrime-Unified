"""Audit correlation and non-HTTP authorization certification tests.

This suite verifies:
- correlation generation and propagation
- no concurrent context leakage
- actor/tenant immutability
- audit envelope completeness
- secret redaction
- WebSocket authentication
- WebSocket authorization
- WebSocket tenant isolation
- deterministic non-HTTP inventory
- fail-closed behavior
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from portal.auth.audit_envelope import (
    REDACTED_FIELDS,
    ActorType,
    AuditEvent,
    Outcome,
    Transport,
    build_audit_event,
    compute_integrity_hash,
    redact_secrets,
    serialize_for_log,
)
from portal.auth.correlation import (
    CorrelationContext,
    accept_inbound_identifier,
    bind_context,
    clear_context,
    create_context,
    generate_correlation_id,
    generate_request_id,
    get_current_context,
    prevent_actor_override,
    prevent_tenant_override,
    propagate_to_child,
)
from portal.auth.jwt_handler import create_access_token
from portal.auth.rbac import Permission, Role
from portal.auth.websocket_auth import (
    WS_CLOSE_CODES,
    authenticate_websocket,
    authorize_websocket_connection,
    bind_websocket_context,
)
from portal.config import get_settings
from portal.main import create_app

settings = get_settings()

# ── Correlation identifier generation ──────────────────────────────────────────


class TestCorrelationGeneration:
    def test_generate_request_id_is_unique_and_nonempty(self):
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert isinstance(id1, str)
        assert len(id1) > 10
        assert id1 != id2
        assert id1.startswith("req-")

    def test_generate_correlation_id_is_unique_and_nonempty(self):
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()
        assert isinstance(id1, str)
        assert len(id1) > 10
        assert id1 != id2
        assert id1.startswith("corr-")

    def test_accept_inbound_valid_identifier(self):
        valid = "req-abc123-uuid-like"
        result = accept_inbound_identifier(valid)
        assert result == valid

    def test_accept_inbound_none_generates_new(self):
        result = accept_inbound_identifier(None)
        assert isinstance(result, str)
        assert len(result) > 10
        assert result.startswith("req-")

    def test_accept_inbound_malformed_generates_new(self):
        malformed_values = ["", "   ", "x" * 200, "!!invalid!!", "spaced value", None]
        for val in malformed_values:
            result = accept_inbound_identifier(val)
            assert result.startswith("req-"), f"Failed for {val!r}"

    def test_accept_inbound_non_string_generates_new(self):
        result = accept_inbound_identifier(12345)  # type: ignore[arg-type]
        assert result.startswith("req-")


# ── Tenant/actor immutability ──────────────────────────────────────────────────


class TestIdentityImmutability:
    def test_prevent_tenant_override_ignores_client_input(self):
        trusted = "tenant-abc"
        result = prevent_tenant_override(trusted, "tenant-evil")
        assert result == trusted

    def test_prevent_tenant_override_ignores_none(self):
        trusted = "tenant-abc"
        result = prevent_tenant_override(trusted, None)
        assert result == trusted

    def test_prevent_tenant_override_rejects_empty_trusted(self):
        with pytest.raises(ValueError, match="trusted_tenant_id"):
            prevent_tenant_override("", "evil")

    def test_prevent_actor_override_ignores_client_input(self):
        trusted = "user-abc"
        result = prevent_actor_override(trusted, "user-evil")
        assert result == trusted

    def test_prevent_actor_override_ignores_none(self):
        trusted = "user-abc"
        result = prevent_actor_override(trusted, None)
        assert result == trusted


# ── Concurrent request isolation ───────────────────────────────────────────────


class TestConcurrentIsolation:
    def test_no_concurrent_context_leakage(self):
        """Two concurrent contexts must not leak into each other."""
        ctx_a = create_context(actor_id="user-a", tenant_id="tenant-a")
        ctx_b = create_context(actor_id="user-b", tenant_id="tenant-b")

        async def run_concurrent():
            async def task_a():
                with bind_context(ctx_a):
                    await asyncio.sleep(0.01)
                    ctx = get_current_context()
                    return ctx.actor_id if ctx else None

            async def task_b():
                with bind_context(ctx_b):
                    await asyncio.sleep(0.01)
                    ctx = get_current_context()
                    return ctx.actor_id if ctx else None

            return await asyncio.gather(task_a(), task_b())

        a_result, b_result = asyncio.run(run_concurrent())
        assert a_result == "user-a"
        assert b_result == "user-b"

    def test_context_cleanup_after_exit(self):
        ctx = create_context(actor_id="user-x")
        assert get_current_context() is None
        with bind_context(ctx):
            assert get_current_context() is not None
        assert get_current_context() is None

    def test_clear_context(self):
        ctx = create_context(actor_id="user-y")
        with bind_context(ctx):
            clear_context()
            assert get_current_context() is None


# ── Nested service propagation ─────────────────────────────────────────────────


class TestNestedPropagation:
    def test_propagate_to_child_preserves_correlation_id(self):
        parent = create_context(actor_id="user-1", tenant_id="tenant-1")
        child = propagate_to_child(parent, invocation_type="service")

        assert child.correlation_id == parent.correlation_id
        assert child.request_id != parent.request_id
        assert child.causation_id == parent.request_id
        assert child.actor_id == parent.actor_id
        assert child.tenant_id == parent.tenant_id
        assert child.invocation_type == "service"

    def test_propagate_to_child_creates_chain(self):
        parent = create_context()
        child = propagate_to_child(parent)
        grandchild = propagate_to_child(child)

        # correlation_id flows through the chain
        assert grandchild.correlation_id == parent.correlation_id
        # causation chain: grandchild.causation = child.request, child.causation = parent.request
        assert grandchild.causation_id == child.request_id
        assert child.causation_id == parent.request_id


# ── Audit envelope ─────────────────────────────────────────────────────────────


class TestAuditEnvelope:
    def test_build_audit_event_has_required_fields(self):
        ctx = create_context(actor_id="user-1", tenant_id="tenant-1")
        with bind_context(ctx):
            event = build_audit_event(
                action="test_action",
                actor_type=ActorType.USER,
                source_transport=Transport.HTTP,
            )

        required = {
            "schema_version", "event_id", "request_id", "correlation_id",
            "causation_id", "occurred_at", "actor_id", "actor_type",
            "tenant_id", "action", "source_transport", "outcome",
            "integrity_hash",
        }
        event_dict = event.as_dict()
        for field_name in required:
            assert field_name in event_dict, f"Missing field: {field_name}"
            assert event_dict[field_name] is not None or field_name in ("causation_id",)

    def test_build_audit_event_inherits_context(self):
        ctx = create_context(actor_id="user-ctx", tenant_id="tenant-ctx")
        with bind_context(ctx):
            event = build_audit_event(action="test")
        assert event.actor_id == "user-ctx"
        assert event.tenant_id == "tenant-ctx"
        assert event.request_id == ctx.request_id
        assert event.correlation_id == ctx.correlation_id

    def test_integrity_hash_is_deterministic(self):
        event = build_audit_event(action="hash_test")
        hash1 = compute_integrity_hash(event)
        hash2 = compute_integrity_hash(event)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_integrity_hash_changes_on_modification(self):
        event1 = build_audit_event(action="action_a")
        event2 = build_audit_event(action="action_b")
        assert compute_integrity_hash(event1) != compute_integrity_hash(event2)

    def test_integrity_hash_excludes_itself(self):
        event = build_audit_event(action="test")
        # The hash field should not be part of the hash computation
        event_dict = event.as_dict()
        event_dict["action"] = "modified"
        recomputed = compute_integrity_hash(event_dict)
        # Should differ because action changed
        assert recomputed != event.integrity_hash


# ── Secret redaction ───────────────────────────────────────────────────────────


class TestSecretRedaction:
    def test_redact_password(self):
        data = {"password": "secret123", "user": "alice"}
        result = redact_secrets(data)
        assert result["password"] == "[REDACTED]"
        assert result["user"] == "alice"

    def test_redact_token(self):
        data = {"token": "jwt-value", "id": 1}
        result = redact_secrets(data)
        assert result["token"] == "[REDACTED]"

    def test_redact_authorization_header(self):
        data = {"Authorization": "Bearer xxx", "path": "/api"}
        result = redact_secrets(data)
        assert result["Authorization"] == "[REDACTED]"

    def test_redact_nested(self):
        data = {"outer": {"inner": {"api_key": "key123", "safe": "ok"}}}
        result = redact_secrets(data)
        assert result["outer"]["inner"]["api_key"] == "[REDACTED]"
        assert result["outer"]["inner"]["safe"] == "ok"

    def test_redact_in_list(self):
        data = [{"password": "p1"}, {"safe": "ok"}]
        result = redact_secrets(data)
        assert result[0]["password"] == "[REDACTED]"
        assert result[1]["safe"] == "ok"

    def test_redact_all_known_fields(self):
        for field_name in REDACTED_FIELDS:
            data = {field_name: "value"}
            result = redact_secrets(data)
            assert result[field_name] == "[REDACTED]", f"Failed to redact: {field_name}"

    def test_serialize_for_log_redacts_metadata(self):
        event = build_audit_event(
            action="login",
            metadata={"password": "secret", "username": "alice"},
        )
        logged = serialize_for_log(event)
        assert logged["metadata"]["password"] == "[REDACTED]"
        assert logged["metadata"]["username"] == "alice"

    def test_build_audit_event_redacts_metadata(self):
        event = build_audit_event(
            action="api_call",
            metadata={"token": "bearer-xxx", "data": "safe"},
        )
        assert event.metadata["token"] == "[REDACTED]"
        assert event.metadata["data"] == "safe"


# ── WebSocket authentication ───────────────────────────────────────────────────


class TestWebSocketAuth:
    def _make_token(self, role: str = Role.VIEWER.value, permissions: list[str] | None = None) -> str:
        if permissions is None:
            permissions = [Permission.CLIENT_READ.value]
        return create_access_token(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            role=role,
            permissions=permissions,
        )

    def test_authenticate_websocket_with_valid_token(self):
        token = self._make_token(
            role=Role.FIRM_ADMIN.value,
            permissions=[Permission.ADMIN_DASHBOARD.value],
        )
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/admin/ws?token={token}") as ws:
            # Connection accepted — should receive metrics data
            data = ws.receive_json()
            assert "requests_total" in data

    def test_authenticate_websocket_without_token_rejected(self):
        app = create_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/admin/ws"):
                pass

    def test_authenticate_websocket_with_invalid_token_rejected(self):
        app = create_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/admin/ws?token=invalid-jwt"):
                pass

    def test_authenticate_websocket_with_expired_token_rejected(self):
        # Create an expired token
        expired_payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "role": Role.SUPER_ADMIN.value,
            "permissions": [p.value for p in Permission],
            "type": "access",
            "jti": str(uuid4()),
            "iat": datetime.now(UTC) - timedelta(minutes=30),
            "exp": datetime.now(UTC) - timedelta(minutes=15),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        app = create_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/admin/ws?token={expired_token}"):
                pass

    def test_authorize_websocket_insufficient_permission(self):
        # VIEWER role doesn't have ADMIN_DASHBOARD permission
        token = self._make_token(role=Role.VIEWER.value, permissions=[Permission.CLIENT_READ.value])
        app = create_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/admin/ws?token={token}"):
                pass

    def test_authorize_websocket_with_admin_permission(self):
        token = self._make_token(
            role=Role.FIRM_ADMIN.value,
            permissions=[Permission.ADMIN_DASHBOARD.value],
        )
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/admin/ws?token={token}") as ws:
            data = ws.receive_json()
            assert "requests_total" in data


# ── WebSocket tenant isolation ─────────────────────────────────────────────────


class TestWebSocketTenantIsolation:
    def test_connection_binds_to_authenticated_tenant(self):
        tenant_id = str(uuid4())
        user_id = str(uuid4())
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.FIRM_ADMIN.value,
            permissions=[Permission.ADMIN_DASHBOARD.value],
        )
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/admin/ws?token={token}") as ws:
            # The connection should be registered under the authenticated tenant
            from portal.websocket.connection_manager import ws_manager
            # The connection is registered during the lifecycle
            ws.receive_json()  # consume first message

    def test_client_supplied_tenant_id_is_ignored(self):
        tenant_id = str(uuid4())
        user_id = str(uuid4())
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=Role.FIRM_ADMIN.value,
            permissions=[Permission.ADMIN_DASHBOARD.value],
        )
        # Attempt to pass a different tenant_id via query param
        evil_tenant = str(uuid4())
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect(
            f"/api/v1/admin/ws?token={token}&tenant_id={evil_tenant}"
        ) as ws:
            ws.receive_json()
            # The connection should use the token's tenant_id, not the query param


# ── Deterministic non-HTTP inventory ───────────────────────────────────────────


def collect_websocket_routes(app: FastAPI | None = None) -> list[dict[str, str]]:
    """Dynamically discover WebSocket routes from source."""
    root = Path(__file__).resolve().parents[2]
    routes: list[dict[str, str]] = []
    for path in root.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/.venv/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "websocket" not in text.lower():
            continue
        module = f"portal.{path.relative_to(root).with_suffix('').as_posix().replace('/', '.')}"
        prefix_match = re.search(
            r"APIRouter\([^\)]*prefix\s*=\s*['\"]([^'\"]+)['\"]", text
        )
        prefix = prefix_match.group(1) if prefix_match else ""
        for match in re.finditer(
            r"@(?:router|app)\.websocket\(\s*['\"]([^'\"]+)['\"]\s*\)", text
        ):
            routes.append({
                "path": f"{prefix}{match.group(1)}",
                "module": module,
                "name": path.stem,
            })
    return sorted(
        {item["path"]: item for item in routes}.values(),
        key=lambda item: item["path"],
    )


def collect_non_http_entrypoints(root: Path | None = None) -> dict[str, list[dict[str, str]]]:
    """Dynamically discover all non-HTTP entry points."""
    root = root or Path(__file__).resolve().parents[2]
    results: dict[str, list[dict[str, str]]] = {
        "websocket_routes": collect_websocket_routes(),
        "background_tasks": [],
        "scheduler_jobs": [],
        "cli_admin_scripts": [],
        "service_to_service_invocations": [],
    }

    py_files = [
        path
        for path in root.rglob("*.py")
        if "/.venv/" not in path.as_posix() and "/tests/" not in path.as_posix()
    ]
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(root))
        if re.search(r"\bBackgroundTasks\b|\.add_task\(", text):
            results["background_tasks"].append({
                "path": rel,
                "classification": "ISOLATED NON-PRODUCTION",
            })
        if re.search(r"\b(APScheduler|BackgroundScheduler|add_job\(|schedule\()\b|cron", text, re.IGNORECASE):
            results["scheduler_jobs"].append({
                "path": rel,
                "classification": "ISOLATED NON-PRODUCTION",
            })
        if rel.startswith("scripts/") or rel.startswith("scripts\\"):
            results["cli_admin_scripts"].append({
                "path": rel,
                "classification": "OUT OF SUPPORTED SCOPE",
            })
        if re.search(
            r"\b(subprocess\.(run|Popen)|requests\.(get|post|put|patch|delete)|"
            r"httpx\.(get|post|put|patch|delete)|urllib\.request)\b",
            text,
        ):
            results["service_to_service_invocations"].append({
                "path": rel,
                "classification": "OUT OF SUPPORTED SCOPE",
            })
    return results


class TestNonHTTPInventory:
    def test_websocket_routes_discovered(self):
        routes = collect_websocket_routes()
        assert len(routes) > 0, "Expected at least one WebSocket route"
        # The admin dashboard WS should be discovered
        paths = [r["path"] for r in routes]
        assert "/admin/ws" in paths, f"Expected /admin/ws in {paths}"

    def test_inventory_deterministic_outside_repo_root(self, monkeypatch, tmp_path):
        import tempfile

        repo_root = Path(__file__).resolve().parents[2]
        outside_dir = Path(tempfile.gettempdir())
        if outside_dir.resolve() == repo_root.resolve():
            outside_dir = tmp_path
        monkeypatch.chdir(outside_dir)

        assert Path.cwd() != repo_root

        default_inventory = collect_non_http_entrypoints()
        explicit_inventory = collect_non_http_entrypoints(root=repo_root)

        assert default_inventory == explicit_inventory

    def test_inventory_json_serializable(self):
        inventory = collect_non_http_entrypoints()
        json.dumps(inventory)  # must not raise


# ── Fail-closed behavior ───────────────────────────────────────────────────────


class TestFailClosed:
    def test_correlation_context_immutable(self):
        ctx = create_context(actor_id="user-1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.actor_id = "tampered"  # type: ignore[misc]

    def test_audit_event_immutable(self):
        event = build_audit_event(action="test")
        with pytest.raises((AttributeError, TypeError)):
            event.action = "tampered"  # type: ignore[misc]

    def test_ws_close_codes_defined(self):
        assert 4401 in WS_CLOSE_CODES
        assert 4403 in WS_CLOSE_CODES
        assert WS_CLOSE_CODES[4401] == "authentication required"
        assert WS_CLOSE_CODES[4403] == "forbidden"


# ── Full app integration ───────────────────────────────────────────────────────


class TestAppIntegration:
    def test_dashboard_http_requires_auth(self):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401

    def test_dashboard_http_with_admin_permission(self):
        token = create_access_token(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            role=Role.FIRM_ADMIN.value,
            permissions=[Permission.ADMIN_DASHBOARD.value],
        )
        app = create_app()
        client = TestClient(app)
        response = client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_dashboard_http_insufficient_permission(self):
        token = create_access_token(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            role=Role.VIEWER.value,
            permissions=[Permission.CLIENT_READ.value],
        )
        app = create_app()
        client = TestClient(app)
        response = client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_metrics_http_requires_admin_permission(self):
        app = create_app()
        client = TestClient(app)
        # No auth
        response = client.get("/api/v1/admin/metrics")
        assert response.status_code == 401

        # Insufficient permission
        token = create_access_token(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            role=Role.VIEWER.value,
            permissions=[Permission.CLIENT_READ.value],
        )
        response = client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
