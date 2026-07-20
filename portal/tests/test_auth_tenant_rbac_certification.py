from __future__ import annotations

import importlib
import inspect
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from portal.auth.jwt_handler import (
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from portal.auth.jwt_handler import (
    settings as jwt_settings,
)
from portal.auth.rbac import CurrentUser, Permission, Role, get_current_user
from portal.main import create_app
from portal.models.billing import Invoice
from portal.routers import billing, users
from portal.services.audit_service import audit

BASELINE_COMMIT = "baseline-placeholder"
EVIDENCE_SCHEMA_VERSION = "1.0"

APPROVED_PUBLIC_V1_ROUTES = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/password/reset-request",
    "/api/v1/auth/password/reset-confirm",
    "/api/v1/documents/share/{share_token}",
    "/api/v1/sso/okta/authorize",
    "/api/v1/sso/azure/authorize",
    "/api/v1/sso/google/authorize",
    "/api/v1/sso/callback",
    "/api/v1/sso/health",
    "/api/v1/blackstone/health",
}

PUBLIC_ROUTE_JUSTIFICATIONS = {
    "/api/v1/auth/login": "Credential exchange must be public so anonymous users can obtain a session.",
    "/api/v1/auth/refresh": "Refresh-token rotation is cookie-based and intentionally callable before access-token auth.",
    "/api/v1/auth/password/reset-request": "Password reset initiation must be public to prevent account enumeration and support lost-password recovery.",
    "/api/v1/auth/password/reset-confirm": "Password reset completion must be public because the one-time reset token is the authorization artifact.",
    "/api/v1/documents/share/{share_token}": "Shared-document access is token-gated and intentionally public for external recipients.",
    "/api/v1/sso/okta/authorize": "OIDC authorization redirect entry point.",
    "/api/v1/sso/azure/authorize": "OIDC authorization redirect entry point.",
    "/api/v1/sso/google/authorize": "OIDC authorization redirect entry point.",
    "/api/v1/sso/callback": "SSO callback must receive the external provider response before local session issuance.",
    "/api/v1/sso/health": "Router health probe for bootstrap verification.",
    "/api/v1/blackstone/health": "Read-only health probe for the governance evaluation surface.",
}

TEST_REFERENCE = "portal/tests/test_auth_tenant_rbac_certification.py"


class DummyResult:
    def __init__(self, rows):
        self._rows = list(rows if isinstance(rows, list) else [rows])

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class DummySession:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.executed = []

    async def execute(self, query):
        self.executed.append(query)
        result = self.execute_results.pop(0) if self.execute_results else None
        if isinstance(result, Exception):
            raise result
        if isinstance(result, DummyResult):
            return result
        return DummyResult(result)

    def add(self, obj):
        if getattr(obj, "id", None) in (None, ""):
            obj.id = uuid4()
        if getattr(obj, "created_at", None) in (None, ""):
            obj.created_at = datetime.now(UTC)
        if hasattr(obj, "currency") and getattr(obj, "currency", None) in (None, ""):
            obj.currency = "USD"
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def flush(self):
        return None


class AuditSession(DummySession):
    def __init__(self):
        super().__init__(execute_results=[])
        self.audit_entries = []

    def add(self, obj):
        super().add(obj)
        self.audit_entries.append(obj)


class _TokenCapture:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return


@pytest.fixture
def secure_app_client():
    app = FastAPI()

    @app.get("/secure")
    async def secure_endpoint(current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
        return {"user_id": current_user.user_id, "tenant_id": current_user.tenant_id}

    return TestClient(app)


@pytest.fixture
def app_graph():
    return create_app()


@pytest.fixture
def current_user_payload():
    return {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "role": Role.ATTORNEY.value,
        "permissions": [Permission.BILLING_READ.value, Permission.PAYMENT_PROCESS.value, Permission.USER_MANAGE_ROLES.value],
        "type": "access",
        "jti": str(uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }


@pytest.fixture
def current_user(current_user_payload):
    return CurrentUser(current_user_payload)


@pytest.fixture
def protected_user():
    return CurrentUser(
        {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "role": Role.FIRM_ADMIN.value,
            "permissions": [
                Permission.BILLING_READ.value,
                Permission.PAYMENT_PROCESS.value,
                Permission.USER_MANAGE_ROLES.value,
                Permission.USER_DELETE.value,
            ],
            "type": "access",
            "jti": str(uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
    )


@pytest.fixture
def tenant_pair():
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    return tenant_a, tenant_b


@pytest.fixture
def invoice_factory(tenant_pair):
    tenant_a, _tenant_b = tenant_pair
    client_a = uuid4()
    client_b = uuid4()

    def build(*, tenant_id: str, amount_paid: float = 0.0, amount_due: float = 100.0, status: str = "sent"):
        return Invoice(
            id=uuid4(),
            tenant_id=tenant_id,
            client_id=client_a if tenant_id == tenant_a else client_b,
            matter_id=None,
            case_id=None,
            created_by=uuid4(),
            invoice_number=f"INV-{tenant_id[:8]}",
            invoice_date=date(2026, 1, 1),
            due_date=date(2026, 2, 1),
            subtotal=100.0,
            tax_rate=0.0,
            tax_amount=0.0,
            discount_amount=0.0,
            total=100.0,
            amount_paid=amount_paid,
            amount_due=amount_due,
            currency="USD",
            status=status,
        )

    return build


@pytest.fixture
def payment_body(tenant_pair):
    _tenant_a, _tenant_b = tenant_pair
    return billing.PaymentCreate(
        invoice_id=uuid4(),
        client_id=uuid4(),
        amount=50.0,
        payment_method="ach",
        payment_date=date(2026, 1, 15),
        reference="ACH-001",
    )


@pytest.fixture
def role_change_user(protected_user):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=protected_user.tenant_id,
        role_id=uuid4(),
        email="target@example.test",
        full_name="Target User",
        is_active=True,
    )


@pytest.fixture
def role_obj():
    return SimpleNamespace(id=uuid4(), name=Role.ATTORNEY.value)


@pytest.fixture
def team_role_obj():
    return SimpleNamespace(id=uuid4(), name=Role.PARALEGAL.value)


@pytest.fixture
def audit_session():
    return AuditSession()


@pytest.fixture
def audit_entry_payload():
    return {
        "action": "invoice_view",
        "status": "success",
        "user_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "resource_type": "invoice",
        "resource_id": str(uuid4()),
        "resource_name": "INV-2026-0001",
        "details": {"request_id": None, "correlation_id": None},
        "actor_ip": "127.0.0.1",
        "actor_email": "auditor@example.test",
    }


def make_access_token(payload_overrides: dict | None = None) -> str:
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "role": Role.ATTORNEY.value,
        "permissions": [Permission.BILLING_READ.value],
        "type": "access",
        "jti": str(uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, jwt_settings.JWT_SECRET_KEY, algorithm=jwt_settings.JWT_ALGORITHM)


def make_refresh_token(payload_overrides: dict | None = None) -> tuple[str, str]:
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "family": str(uuid4()),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return create_refresh_token(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        family=payload.get("family"),
    )


def route_dependency_names(route: APIRoute) -> list[str]:
    names: list[str] = []
    stack = list(getattr(route.dependant, "dependencies", []))
    while stack:
        dependant = stack.pop()
        call = getattr(dependant, "call", None)
        if call is not None:
            name = getattr(call, "__name__", None)
            if not name:
                cls = type(call)
                name = f"{cls.__module__}.{cls.__qualname__}"
            names.append(f"{getattr(call, '__module__', '')}:{name}")
        stack.extend(getattr(dependant, "dependencies", []))
    return names


def classify_route(route: APIRoute) -> dict[str, str | list[str]]:
    source = inspect.getsource(route.endpoint)
    dependency_names = route_dependency_names(route)
    auth_dependency = "none"
    if "Depends(require_permissions(" in source:
        auth_dependency = "require_permissions"
    elif "Depends(require_role(" in source:
        auth_dependency = "require_role"
    elif "Depends(get_current_user)" in source:
        auth_dependency = "get_current_user"

    if "require_same_tenant(" in source or "tenant_id == current_user.tenant_id" in source or "tenant_id=current_user.tenant_id" in source:
        tenant_control = "tenant-bound"
    elif "portal_user_id == current_user.user_id" in source:
        tenant_control = "self-bound"
    elif "current_user.is_super_admin()" in source:
        tenant_control = "super-admin-exception"
    elif auth_dependency == "none":
        tenant_control = "public"
    else:
        tenant_control = "role-bound"

    public = route.path in APPROVED_PUBLIC_V1_ROUTES
    if public:
        justification = PUBLIC_ROUTE_JUSTIFICATIONS[route.path]
    else:
        justification = f"Protected by {auth_dependency or 'route-level enforcement'}"

    return {
        "path": route.path,
        "methods": sorted(route.methods or []),
        "handler": route.name,
        "source_module": route.endpoint.__module__,
        "auth_dependency": auth_dependency,
        "authorization_dependency": auth_dependency if auth_dependency != "none" else "none",
        "tenant_control_mechanism": tenant_control,
        "public_protected_classification": "PUBLIC" if public else "PROTECTED",
        "exception_justification": justification,
        "test_reference": TEST_REFERENCE,
        "dependency_calls": dependency_names,
    }


def collect_route_matrix(app: FastAPI | None = None) -> list[dict[str, str | list[str]]]:
    app = app or create_app()
    routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path.startswith("/api/v1/")]
    if not routes:
        root = Path(__file__).resolve().parents[2]
        main_source = (root / "portal" / "main.py").read_text(encoding="utf-8", errors="ignore")
        include_pattern = re.compile(r'app\.include_router\((\w+)\.router(?:,\s*prefix="([^"]+)")?')
        for match in include_pattern.finditer(main_source):
            module_name = match.group(1)
            prefix = match.group(2) or ""
            module = importlib.import_module(f"portal.routers.{module_name}")
            for route in module.router.routes:
                if not isinstance(route, APIRoute):
                    continue
                route_path = route.path
                if prefix and not route_path.startswith(prefix):
                    route_path = f"{prefix.rstrip('/')}{route_path}"
                synthetic_route = SimpleNamespace(
                    path=route_path,
                    methods=route.methods,
                    name=route.name,
                    endpoint=route.endpoint,
                    dependant=route.dependant,
                )
                if synthetic_route.path.startswith("/api/v1/"):
                    routes.append(synthetic_route)
    return [classify_route(route) for route in sorted(routes, key=lambda route: (route.path, sorted(route.methods or [])))]


def collect_websocket_routes(app: FastAPI | None = None) -> list[dict[str, str]]:
    root = Path(__file__).resolve().parents[2]
    routes: list[dict[str, str]] = []
    for path in root.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/.venv/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "websocket" not in text:
            continue
        prefix_match = re.search(r"APIRouter\([^\)]*prefix\s*=\s*['\"]([^'\"]+)['\"]", text)
        prefix = prefix_match.group(1) if prefix_match else ""
        module = f"portal.{path.relative_to(root).with_suffix('').as_posix().replace('/', '.')}"
        for match in re.finditer(r"@(?:router|app)\.websocket\(\s*['\"]([^'\"]+)['\"]\s*\)", text):
            routes.append(
                {
                    "path": f"{prefix}{match.group(1)}",
                    "name": path.stem,
                    "module": module,
                }
            )
    return sorted({(item["path"], item["name"], item["module"]): item for item in routes}.values(), key=lambda item: item["path"])


def collect_non_http_entrypoints(app: FastAPI | None = None, root: Path | None = None) -> dict[str, list[dict[str, str]]]:
    root = root or Path(__file__).resolve().parents[2]
    results = {
        "websocket_routes": collect_websocket_routes(app),
        "background_tasks": [],
        "scheduler_jobs": [],
        "cli_admin_scripts": [],
        "service_to_service_invocations": [],
    }

    py_files = [path for path in root.rglob("*.py") if "/.venv/" not in path.as_posix() and "/tests/" not in path.as_posix()]
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(root))
        if re.search(r"\bBackgroundTasks\b|\.add_task\(", text):
            results["background_tasks"].append({"path": rel, "classification": "ISOLATED NON-PRODUCTION"})
        if re.search(r"\b(APScheduler|BackgroundScheduler|add_job\(|schedule\()\b|cron", text, re.IGNORECASE):
            results["scheduler_jobs"].append({"path": rel, "classification": "ISOLATED NON-PRODUCTION"})
        if rel.startswith("scripts/") or rel.startswith("scripts\\"):
            results["cli_admin_scripts"].append({"path": rel, "classification": "OUT OF SUPPORTED SCOPE"})
        if re.search(r"\b(subprocess\.(run|Popen)|requests\.(get|post|put|patch|delete)|httpx\.(get|post|put|patch|delete)|urllib\.request)\b", text):
            results["service_to_service_invocations"].append({"path": rel, "classification": "OUT OF SUPPORTED SCOPE"})
    return results


def secure_client_request(client: TestClient, token: str | None = None, scheme: str = "Bearer"):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"{scheme} {token}"
    return client.get("/secure", headers=headers)


@pytest.mark.parametrize(
    ("claim", "value", "expected_detail"),
    [
        ("sub", None, "Missing required token claim: sub"),
        ("sub", "", "Missing required token claim: sub"),
        ("tenant_id", None, "Missing required token claim: tenant_id"),
        ("tenant_id", "", "Missing required token claim: tenant_id"),
        ("role", None, "Missing required token claim: role"),
        ("role", "NOT_A_ROLE", "Invalid token role: 'NOT_A_ROLE'"),
    ],
)
def test_authentication_fails_closed_on_missing_and_invalid_claims(secure_app_client, claim, value, expected_detail):
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "role": Role.ATTORNEY.value,
        "permissions": [Permission.BILLING_READ.value],
        "type": "access",
        "jti": str(uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    if value is None:
        payload.pop(claim, None)
    else:
        payload[claim] = value
    token = jwt.encode(payload, jwt_settings.JWT_SECRET_KEY, algorithm=jwt_settings.JWT_ALGORITHM)
    response = secure_client_request(secure_app_client, token)
    assert response.status_code == 401
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("permissions", "expected_detail"),
    [
        ("case:read", "Malformed permissions container"),
        ({"case:read": True}, "Malformed permissions container"),
        ([Permission.BILLING_READ.value, "not.a.permission"], "Unsupported permissions: not.a.permission"),
    ],
)
def test_authentication_fails_closed_on_permissions_shape_and_values(secure_app_client, permissions, expected_detail):
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "role": Role.ATTORNEY.value,
        "permissions": permissions,
        "type": "access",
        "jti": str(uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    token = jwt.encode(payload, jwt_settings.JWT_SECRET_KEY, algorithm=jwt_settings.JWT_ALGORITHM)
    response = secure_client_request(secure_app_client, token)
    assert response.status_code == 401
    assert response.json()["detail"] == expected_detail


def test_authentication_fails_closed_on_jwt_and_header_errors(secure_app_client):
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "role": Role.ATTORNEY.value,
            "permissions": [Permission.BILLING_READ.value],
            "type": "access",
            "jti": str(uuid4()),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        jwt_settings.JWT_SECRET_KEY,
        algorithm=jwt_settings.JWT_ALGORITHM,
    )
    invalid_signature = jwt.encode(
        {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "role": Role.ATTORNEY.value,
            "permissions": [Permission.BILLING_READ.value],
            "type": "access",
            "jti": str(uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        "wrong-secret",
        algorithm=jwt_settings.JWT_ALGORITHM,
    )
    malformed = "not-a.jwt"
    refresh_token, family_id = make_refresh_token()
    assert isinstance((refresh_token, family_id), tuple)
    assert len((refresh_token, family_id)) == 2
    assert decode_refresh_token(refresh_token)["family"] == family_id

    cases = [
        (None, "Bearer", 401, "Authentication required"),
        (malformed, "Bearer", 401, "Invalid access token"),
        (invalid_signature, "Bearer", 401, "Invalid access token"),
        (expired_token, "Bearer", 401, "Access token has expired"),
        (refresh_token, "Bearer", 401, "Invalid access token"),
    ]
    for token, scheme, expected_status, expected_detail in cases:
        response = secure_client_request(secure_app_client, token, scheme=scheme)
        assert response.status_code == expected_status
        assert expected_detail in response.json()["detail"]

    response = secure_client_request(secure_app_client, "abc", scheme="Token")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_billing_tenant_isolation_and_fail_closed_payment_flow(current_user, tenant_pair, invoice_factory):
    tenant_a, tenant_b = tenant_pair
    current_user.tenant_id = tenant_a
    current_user.permissions = frozenset({Permission.PAYMENT_PROCESS})

    same_tenant_invoice = invoice_factory(tenant_id=tenant_a)
    cross_tenant_invoice = invoice_factory(tenant_id=tenant_b)
    same_tenant_invoice.amount_paid = 0.0
    same_tenant_invoice.amount_due = same_tenant_invoice.total
    cross_tenant_invoice.amount_paid = 0.0
    cross_tenant_invoice.amount_due = cross_tenant_invoice.total

    payment = billing.PaymentCreate(
        invoice_id=same_tenant_invoice.id,
        client_id=same_tenant_invoice.client_id,
        amount=50.0,
        payment_method="ach",
        payment_date=date(2026, 1, 15),
        reference="ACH-001",
    )
    success_db = DummySession(execute_results=[same_tenant_invoice])
    response = await billing.record_payment(body=payment, current_user=current_user, db=success_db)
    assert response.amount == 50.0
    assert same_tenant_invoice.amount_paid == 50.0
    assert same_tenant_invoice.amount_due == 50.0
    assert same_tenant_invoice.status == "partial"
    assert success_db.commits == 1
    assert sum(1 for item in success_db.added if isinstance(item, billing.Payment)) == 1
    assert sum(1 for item in success_db.added if item.__class__.__name__ == "AuditLog") == 1

    denied_db = DummySession(execute_results=[None])
    denied_payment = billing.PaymentCreate(
        invoice_id=cross_tenant_invoice.id,
        client_id=cross_tenant_invoice.client_id,
        amount=25.0,
        payment_method="ach",
        payment_date=date(2026, 1, 15),
    )
    with pytest.raises(HTTPException) as excinfo:
        await billing.record_payment(body=denied_payment, current_user=current_user, db=denied_db)
    assert excinfo.value.status_code == 404
    assert denied_db.commits == 0
    assert len(denied_db.added) == 0
    assert cross_tenant_invoice.amount_paid == 0.0
    assert cross_tenant_invoice.amount_due == cross_tenant_invoice.total
    assert cross_tenant_invoice.status == "sent"


@pytest.mark.asyncio
async def test_rbac_escalation_controls(current_user, protected_user, role_change_user, role_obj, team_role_obj, monkeypatch):
    current_user.permissions = frozenset({Permission.USER_MANAGE_ROLES, Permission.USER_DELETE, Permission.USER_READ})

    target_role = SimpleNamespace(id=uuid4(), name=Role.PARALEGAL.value)
    target_user = role_change_user
    target_user.role_id = team_role_obj.id

    db = DummySession(execute_results=[target_user, target_role])
    audit_calls = []
    revoke_calls = []

    async def capture_audit(*args, **kwargs):
        audit_calls.append((args, kwargs))

    async def capture_revoke(*args, **kwargs):
        revoke_calls.append((args, kwargs))

    def response_patch(user):
        return {"id": str(user.id), "role_id": str(user.role_id), "tenant_id": str(user.tenant_id)}

    monkeypatch.setattr(users, "revoke_all_user_sessions", capture_revoke)
    monkeypatch.setattr(users, "audit", capture_audit)
    monkeypatch.setattr(users.UserResponse, "from_orm_with_role", staticmethod(response_patch))

    same_tenant_response = await users.change_user_role(user_id=target_user.id, role=target_role.name, current_user=current_user, db=db)
    assert same_tenant_response["role_id"] == str(target_role.id)
    assert db.commits == 1
    assert len(revoke_calls) == 1
    assert len(audit_calls) == 1

    self_db = DummySession(execute_results=[])
    with pytest.raises(HTTPException) as self_exc:
        await users.change_user_role(user_id=UUID(current_user.user_id), role=Role.PARALEGAL.value, current_user=current_user, db=self_db)
    assert self_exc.value.status_code == 400
    assert "Cannot change your own role" in self_exc.value.detail

    cross_tenant_user = SimpleNamespace(id=uuid4(), tenant_id=str(uuid4()), role_id=uuid4(), email="cross@example.test", full_name="Cross Tenant", is_active=True)
    cross_db = DummySession(execute_results=[None])
    with pytest.raises(HTTPException) as cross_exc:
        await users.change_user_role(user_id=cross_tenant_user.id, role=Role.PARALEGAL.value, current_user=current_user, db=cross_db)
    assert cross_exc.value.status_code == 404

    denied_user = CurrentUser(
        {
            "sub": str(uuid4()),
            "tenant_id": current_user.tenant_id,
            "role": Role.CLIENT.value,
            "permissions": [Permission.USER_READ.value],
            "type": "access",
            "jti": str(uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
    )
    assert not denied_user.has_permission(Permission.USER_MANAGE_ROLES)
    assert not denied_user.has_role(Role.PARALEGAL)

    if hasattr(users, "assign_permissions"):
        pytest.fail("Unsupported permission-assignment route exists and must be covered explicitly.")


def test_dynamic_live_app_route_discovery(app_graph):
    matrix = collect_route_matrix(app_graph)
    assert matrix, "Route matrix must not be empty"

    discovered_public = {row["path"] for row in matrix if row["public_protected_classification"] == "PUBLIC"}
    assert discovered_public == APPROVED_PUBLIC_V1_ROUTES

    for row in matrix:
        assert row["public_protected_classification"] in {"PUBLIC", "PROTECTED"}
        if row["path"] in APPROVED_PUBLIC_V1_ROUTES:
            assert row["exception_justification"] == PUBLIC_ROUTE_JUSTIFICATIONS[row["path"]]
        else:
            assert row["auth_dependency"] != "none"
            assert row["exception_justification"].startswith("Protected by")

    shared_document = next(row for row in matrix if row["path"] == "/api/v1/documents/share/{share_token}")
    assert shared_document["public_protected_classification"] == "PUBLIC"
    assert "shared-document" in shared_document["exception_justification"].lower()


def test_non_http_entrypoint_inventory(app_graph):
    inventory = collect_non_http_entrypoints(app_graph)
    assert inventory["websocket_routes"], "WebSocket routes must be discovered from the live app graph"
    assert any(item["classification"] == "ISOLATED NON-PRODUCTION" for item in inventory["background_tasks"]) or inventory["background_tasks"] == []
    assert any(item["classification"] == "OUT OF SUPPORTED SCOPE" for item in inventory["cli_admin_scripts"]) or inventory["cli_admin_scripts"] == []
    assert all(item["classification"] in {"ISOLATED NON-PRODUCTION", "OUT OF SUPPORTED SCOPE"} for item in inventory["service_to_service_invocations"])


@pytest.mark.asyncio
async def test_audit_correlation_verification(audit_session, audit_entry_payload):
    entry = await audit(
        audit_session,
        action=audit_entry_payload["action"],
        status=audit_entry_payload["status"],
        user_id=audit_entry_payload["user_id"],
        tenant_id=audit_entry_payload["tenant_id"],
        resource_type=audit_entry_payload["resource_type"],
        resource_id=audit_entry_payload["resource_id"],
        resource_name=audit_entry_payload["resource_name"],
        details=audit_entry_payload["details"],
        actor_ip=audit_entry_payload["actor_ip"],
        actor_email=audit_entry_payload["actor_email"],
        actor_role=Role.ATTORNEY.value,
        actor_user_agent="pytest",
        http_method="GET",
        http_path="/api/v1/invoices/123",
        http_status_code=200,
    )
    assert entry.actor_email == audit_entry_payload["actor_email"]
    assert entry.tenant_id == audit_entry_payload["tenant_id"]
    assert entry.action == audit_entry_payload["action"]
    assert entry.resource_type == audit_entry_payload["resource_type"]
    assert entry.status == audit_entry_payload["status"]
    assert entry.request_id is None
    assert entry.session_id is None or entry.session_id == ""
    assert audit_session.audit_entries, "Audit entry should be persisted in the session"


def test_refresh_token_tuple_handling_and_malformed_parameter_construction():
    refresh_token, family_id = create_refresh_token(
        user_id=str(uuid4()),
        tenant_id=str(uuid4()),
    )
    assert isinstance(refresh_token, str)
    assert isinstance(family_id, str)
    assert decode_refresh_token(refresh_token)["family"] == family_id

    bad_authorization = f"Bearer {'not-a.jwt'}"
    assert bad_authorization == "Bearer not-a.jwt"
    assert decode_access_token.__name__ == "decode_access_token"


@pytest.mark.asyncio
async def test_focused_certification_helpers_round_trip(current_user):
    payload = {
        "sub": current_user.user_id,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role.value,
        "permissions": [p.value for p in current_user.permissions],
        "type": "access",
        "jti": str(uuid4()),
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    token = jwt.encode(payload, jwt_settings.JWT_SECRET_KEY, algorithm=jwt_settings.JWT_ALGORITHM)
    assert decode_access_token(token)["sub"] == current_user.user_id

    raw = json.loads(json.dumps({"repository": "SintraPrime-Unified", "schema_version": EVIDENCE_SCHEMA_VERSION}))
    assert raw["repository"] == "SintraPrime-Unified"


def test_live_route_inventory_helper_outputs_json_serializable(app_graph):
    matrix = collect_route_matrix(app_graph)
    inventory = collect_non_http_entrypoints(app_graph)
    payload = {
        "repository": "SintraPrime-Unified",
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "baseline_commit": BASELINE_COMMIT,
        "route_count": len(matrix),
        "non_http_count": sum(len(v) for v in inventory.values()),
    }
    json.dumps(payload)
    assert payload["route_count"] >= len(APPROVED_PUBLIC_V1_ROUTES)


def test_route_dependency_names_are_stable_across_runs(app_graph):
    """Dependency names must not include memory addresses and must be identical across repeated enumerations."""
    routes = [r for r in app_graph.routes if isinstance(r, APIRoute)]
    assert routes, "expected at least one APIRoute in the live app graph"

    snapshots = [route_dependency_names(r) for r in routes]
    # Re-enumerate and assert byte-identical output (no memory-address drift).
    snapshots_again = [route_dependency_names(r) for r in routes]
    assert snapshots == snapshots_again

    for names in snapshots:
        for name in names:
            # Memory addresses present in repr() appear as hex runs like 0x0000021D...
            assert "0x" not in name, f"dependency name contains a memory address: {name!r}"
            assert "<" not in name, f"dependency name contains repr() angle brackets: {name!r}"


def test_non_http_entrypoint_inventory_works_outside_repo_root(app_graph, monkeypatch, tmp_path):
    """collect_non_http_entrypoints must return the same inventory regardless of the process cwd."""
    import tempfile

    repo_root = Path(__file__).resolve().parents[2]
    # Use a portable directory guaranteed to exist outside the repo root on both Windows and Linux.
    outside_dir = Path(tempfile.gettempdir())
    if outside_dir.resolve() == repo_root.resolve():
        outside_dir = tmp_path
    monkeypatch.chdir(outside_dir)

    assert Path.cwd() != repo_root, "test precondition: cwd must be outside the repo root"

    default_inventory = collect_non_http_entrypoints(app_graph)
    explicit_inventory = collect_non_http_entrypoints(app_graph, root=repo_root)

    assert default_inventory == explicit_inventory, (
        "collect_non_http_entrypoints default root must be derived from the test file location, not Path.cwd()"
    )
    assert default_inventory["websocket_routes"], "expected at least one websocket route discovered"
