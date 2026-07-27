"""Increment One tests for Hermes Quicksilver service authorization.

These tests use controlled fixtures and do not import the broken Hermes runtime
modules. They verify the fail-closed, read-only, redacted, and persisted behavior
of the Quicksilver adapter surface.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from portal.config import Settings
from portal.models.hermes_quicksilver import (
    Decision,
    DelegationRequest,
    HermesProfileDescriptor,
    RiskCeiling,
    SpecialistProfileMapping,
)
from portal.services.hermes_quicksilver import (
    AuthorizationError,
    HermesQuicksilverService,
    TrustedCaller,
)
from portal.services.hermes_quicksilver.delegation_audit import (
    EVENT_POLICY_HARD_DENIED,
    EVENT_SPECIALIST_MAPPING_DENIED,
    AuditRedactionError,
    DelegationAuditBuilder,
)
from portal.services.hermes_quicksilver.hard_deny_policy import HermesHardDenyPolicy
from portal.services.hermes_quicksilver.mapping_service import (
    MappingServiceError,
    SpecialistMappingService,
)
from portal.services.hermes_quicksilver.profile_registry import (
    HermesProfileInvalidError,
    HermesProfileRegistry,
    HermesProfileRegistryError,
    HermesRootUnavailableError,
)

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def hermes_home(tmp_path: Path) -> Path:
    home = tmp_path / ".hermes"
    profiles = home / "profiles"
    profiles.mkdir(parents=True)

    coder = profiles / "coder"
    coder.mkdir()
    (coder / "profile.yaml").write_text(
        'name: "Coder Profile"\ndescription: "Code review and refactoring"\n'
        'model: "gpt-4"\nprovider: "openai"\nskills:\n- devops\n- python\n',
        encoding="utf-8",
    )

    research = profiles / "research"
    research.mkdir()
    (research / "profile.yaml").write_text(
        'name: "Research Profile"\ndescription_auto: "Legal research"\n',
        encoding="utf-8",
    )
    return home


@pytest.fixture
def registry(hermes_home: Path) -> HermesProfileRegistry:
    return HermesProfileRegistry(hermes_home=hermes_home)


@pytest.fixture
def tenant_id() -> str:
    return str(uuid4())


@pytest.fixture
def tenant_id_b() -> str:
    return str(uuid4())


@pytest.fixture
def mapping_factory(tenant_id: str):
    def _make(**overrides):
        defaults = {
            "specialist_id": "sintra-legal-research",
            "hermes_profile_id": "research",
            "display_name": "Legal Research Specialist",
            "capabilities": ["legal_research"],
            "allowed_tool_classes": ["read", "search"],
            "prohibited_tool_classes": ["write", "execute"],
            "risk_ceiling": RiskCeiling.LOW,
            "tenant_scope": [tenant_id],
            "enabled": True,
            "minimum_hermes_version": "0.18.0",
            "maximum_hermes_version": "0.19.0",
        }
        defaults.update(overrides)
        return SpecialistProfileMapping(**defaults)

    return _make


@pytest.fixture
def mapping_service(registry: HermesProfileRegistry, mapping_factory):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    svc.register(mapping_factory())
    return svc


@pytest.fixture
def audit_builder():
    return DelegationAuditBuilder(source_version="0.18.2")


@pytest.fixture
def trusted_caller(tenant_id: str) -> TrustedCaller:
    return TrustedCaller(
        user_id="user-" + str(uuid4()),
        tenant_id=tenant_id,
        permission="hermes_quicksilver:admin",
    )


@pytest.fixture
def enabled_settings():
    return Settings(HERMES_QUICKSILVER_ENABLED=True)


# ── Feature flag tests ───────────────────────────────────────────────────────


def test_feature_disabled_by_default():
    settings = Settings()
    assert settings.is_hermes_quicksilver_enabled is False


def test_disabled_feature_performs_no_filesystem_access(registry: HermesProfileRegistry):
    svc = HermesQuicksilverService(registry=registry)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id="any",
        actor_id="any",
    )
    result, event = svc.execute(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "feature_disabled"
    assert event.event_type == EVENT_POLICY_HARD_DENIED


def test_disabled_feature_performs_no_cli_invocation(registry: HermesProfileRegistry):
    svc = HermesQuicksilverService(registry=registry)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id="any",
        actor_id="any",
    )
    result, event = svc.execute(request)
    assert result.data is None
    assert result.reason_code == "feature_disabled"


# ── Authorization tests ──────────────────────────────────────────────────────


def test_untrusted_caller_denied_for_admin_discovery(registry, enabled_settings, tenant_id):
    svc = HermesQuicksilverService(
        registry=registry, settings=enabled_settings, internal_admin_permission="hermes_quicksilver:admin"
    )
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="internal_admin",
        tenant_id=tenant_id,
        actor_id="internal_admin",
    )
    result, event = svc.execute(request, caller=None)
    assert result.decision == Decision.DENY
    assert result.reason_code == "untrusted_caller"


def test_literal_identity_denied(enabled_settings, tenant_id, mapping_service):
    svc = HermesQuicksilverService(mapping_service=mapping_service, settings=enabled_settings)
    for literal in ("internal_admin", "system", "root", "default"):
        caller = TrustedCaller(user_id=literal, tenant_id=tenant_id, permission="hermes_quicksilver:admin")
        request = DelegationRequest(
            operation="list_profiles",
            specialist_id="any",
            tenant_id=tenant_id,
            actor_id=literal,
        )
        result, event = svc.execute(request, caller=caller)
        assert result.decision == Decision.DENY, literal
        assert result.reason_code == "untrusted_caller", literal


def test_missing_caller_context_denied(enabled_settings, tenant_id):
    svc = HermesQuicksilverService(settings=enabled_settings)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "untrusted_caller"


def test_trusted_caller_permitted_for_admin_discovery(
    registry, enabled_settings, trusted_caller
):
    svc = HermesQuicksilverService(registry=registry, settings=enabled_settings)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=trusted_caller.tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.ALLOW
    assert result.data is not None
    assert result.data["count"] == 2


def test_tenant_authorization_distinct_from_mapping(
    registry, enabled_settings, tenant_id, tenant_id_b, mapping_factory
):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    svc.register(mapping_factory(tenant_scope=[tenant_id_b]))
    service = HermesQuicksilverService(mapping_service=svc, registry=registry, settings=enabled_settings)
    caller = TrustedCaller(user_id="user-" + str(uuid4()), tenant_id=tenant_id, permission="hermes_quicksilver:admin")
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="actor-1",
    )
    result, event = service.execute(request, caller=caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "tenant_mismatch"


def test_tenant_mismatch_denied_before_mapping(
    registry, enabled_settings, tenant_id, tenant_id_b
):
    svc = HermesQuicksilverService(registry=registry, settings=enabled_settings)
    caller = TrustedCaller(user_id="user-" + str(uuid4()), tenant_id=tenant_id, permission="hermes_quicksilver:admin")
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=tenant_id_b,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "tenant_unauthorized"


def test_specialist_mapping_does_not_substitute_for_admin_authorization(
    registry, enabled_settings, tenant_id, mapping_service
):
    svc = HermesQuicksilverService(mapping_service=mapping_service, registry=registry, settings=enabled_settings)
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=None)
    assert result.decision == Decision.DENY
    assert result.reason_code == "untrusted_caller"


# ── Hard-deny precedence tests ───────────────────────────────────────────────


def test_hard_deny_before_mapping_and_registry(
    enabled_settings, tenant_id
):
    """Unknown operations must not call mapping or registry."""
    registry_spy = MagicMock(spec=HermesProfileRegistry)
    mapping_spy = MagicMock(spec=SpecialistMappingService)
    svc = HermesQuicksilverService(
        mapping_service=mapping_spy,
        registry=registry_spy,
        settings=enabled_settings,
    )
    caller = TrustedCaller(user_id="user-" + str(uuid4()), tenant_id=tenant_id, permission="hermes_quicksilver:admin")
    request = DelegationRequest(
        operation="run_agent",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "hard_denied"
    assert event.event_type == EVENT_POLICY_HARD_DENIED
    mapping_spy.resolve.assert_not_called()
    mapping_spy.get_contract.assert_not_called()
    registry_spy.list_profiles.assert_not_called()
    registry_spy.get_profile.assert_not_called()


def test_unknown_operation_denied_before_mapping_and_registry(
    enabled_settings, tenant_id
):
    registry_spy = MagicMock(spec=HermesProfileRegistry)
    mapping_spy = MagicMock(spec=SpecialistMappingService)
    svc = HermesQuicksilverService(
        mapping_service=mapping_spy,
        registry=registry_spy,
        settings=enabled_settings,
    )
    caller = TrustedCaller(user_id="user-" + str(uuid4()), tenant_id=tenant_id, permission="hermes_quicksilver:admin")
    request = DelegationRequest(
        operation="unknown_action",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "hard_denied"
    assert event.event_type == EVENT_POLICY_HARD_DENIED
    mapping_spy.resolve.assert_not_called()
    mapping_spy.get_contract.assert_not_called()
    registry_spy.list_profiles.assert_not_called()
    registry_spy.get_profile.assert_not_called()


def test_admin_discovery_does_not_invoke_mapping_or_registry_profile_get(
    registry, enabled_settings, trusted_caller
):
    mapping_spy = MagicMock(spec=SpecialistMappingService)
    svc = HermesQuicksilverService(
        mapping_service=mapping_spy,
        registry=registry,
        settings=enabled_settings,
    )
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=trusted_caller.tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.ALLOW
    mapping_spy.resolve.assert_not_called()
    mapping_spy.get_contract.assert_not_called()


# ── Profile registry tests ─────────────────────────────────────────────────────


def test_list_profiles_read_only(registry: HermesProfileRegistry, hermes_home: Path):
    profiles = registry.list_profiles()
    assert len(profiles) == 2
    coder = next(p for p in profiles if p.profile_id == "coder")
    assert coder.display_name == "Coder Profile"
    assert "python" in coder.skills
    assert (hermes_home / "profiles" / "coder" / "profile.yaml").exists()


def test_get_profile_metadata(registry: HermesProfileRegistry):
    profile = registry.get_profile("research")
    assert profile is not None
    assert profile.display_name == "Research Profile"
    assert profile.description == "Legal research"


def test_missing_profile_returns_none(registry: HermesProfileRegistry):
    assert registry.get_profile("nonexistent") is None


def test_missing_hermes_root_fails_closed(tmp_path: Path):
    missing = tmp_path / "does_not_exist"
    registry = HermesProfileRegistry(hermes_home=missing)
    with pytest.raises(HermesRootUnavailableError):
        registry.list_profiles()


def test_malformed_profile_yaml_ignored(registry: HermesProfileRegistry, hermes_home: Path):
    bad = hermes_home / "profiles" / "bad"
    bad.mkdir()
    (bad / "profile.yaml").write_text("not: valid: yaml: :::\n", encoding="utf-8")
    profile = registry.get_profile("bad")
    assert profile is not None
    assert profile.profile_id == "bad"


def test_path_traversal_rejected(registry: HermesProfileRegistry):
    assert registry.get_profile("../etc/passwd") is None


def test_profile_directory_symlink_rejected(registry: HermesProfileRegistry, hermes_home: Path):
    profiles = hermes_home / "profiles"
    target = profiles / "coder"
    link = profiles / "linker"
    link.symlink_to(target, target_is_directory=True)
    listed = registry.list_profiles()
    assert "linker" not in [p.profile_id for p in listed]


def test_profile_yaml_symlink_rejected(registry: HermesProfileRegistry, hermes_home: Path):
    profiles = hermes_home / "profiles"
    target = profiles / "coder" / "profile.yaml"
    bad_dir = profiles / "bad2"
    bad_dir.mkdir()
    link = bad_dir / "profile.yaml"
    link.symlink_to(target)
    with pytest.raises(HermesProfileInvalidError):
        registry.get_profile("bad2")


def test_resolved_path_remains_under_profiles_root(registry: HermesProfileRegistry, hermes_home: Path):
    profile = registry.get_profile("coder")
    assert profile is not None
    assert str(hermes_home / "profiles" / "coder") in str(profile.source_path)


def test_oversized_file_rejected(registry: HermesProfileRegistry, hermes_home: Path):
    big_dir = hermes_home / "profiles" / "big"
    big_dir.mkdir()
    (big_dir / "profile.yaml").write_text("x" * (2 * 1024 * 1024), encoding="utf-8")
    with pytest.raises(HermesProfileInvalidError):
        registry.get_profile("big")


def test_forbidden_files_identified(registry: HermesProfileRegistry):
    assert registry.is_forbidden_file("config.yaml") is True
    assert registry.is_forbidden_file("state.db") is True
    assert registry.is_forbidden_file(".env") is True
    assert registry.is_forbidden_file("credentials.json") is True
    assert registry.is_forbidden_file("profile.yaml") is False


# ── Mapping service tests ─────────────────────────────────────────────────────


def test_unknown_specialist_rejected(registry: HermesProfileRegistry, tenant_id: str):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="unknown",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "unknown_specialist"


def test_missing_mapping_rejected(registry: HermesProfileRegistry, tenant_id: str):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="no-mapping",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "unknown_specialist"


def test_duplicate_mapping_rejected(mapping_factory, registry: HermesProfileRegistry):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    svc.register(mapping_factory())
    with pytest.raises(MappingServiceError):
        svc.register(mapping_factory())


def test_disabled_mapping_rejected(mapping_factory, registry, tenant_id):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    svc.register(mapping_factory(enabled=False))
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "disabled_mapping"


def test_tenant_mismatch_rejected(mapping_factory, registry, tenant_id, tenant_id_b):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.18.2")
    svc.register(mapping_factory(tenant_scope=[tenant_id_b]))
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "tenant_mismatch"


def test_unsupported_version_rejected(mapping_factory, registry, tenant_id):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.20.0")
    svc.register(mapping_factory())
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "unsupported_version"


def test_mapping_deterministic(mapping_service, tenant_id):
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    r1 = mapping_service.resolve(request)
    r2 = mapping_service.resolve(request)
    assert r1.hermes_profile_id == r2.hermes_profile_id == "research"
    assert r1.decision == r2.decision == Decision.ALLOW


# ── Hard-deny policy tests ───────────────────────────────────────────────────


def test_hard_deny_overrides_allow(mapping_service, enabled_settings, tenant_id, trusted_caller):
    svc = HermesQuicksilverService(mapping_service=mapping_service, settings=enabled_settings)
    request = DelegationRequest(
        operation="run_agent",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "hard_denied"
    assert event.event_type == EVENT_POLICY_HARD_DENIED


def test_operation_allowlist_enforced(mapping_service, enabled_settings, tenant_id, trusted_caller):
    svc = HermesQuicksilverService(mapping_service=mapping_service, settings=enabled_settings)
    request = DelegationRequest(
        operation="unknown_action",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.DENY
    assert result.reason_code == "hard_denied"
    assert event.event_type == EVENT_POLICY_HARD_DENIED


# ── Audit event tests ────────────────────────────────────────────────────────


def test_audit_identifiers_preserved(audit_builder, tenant_id):
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="actor-1",
        correlation_id="corr-123",
    )
    event = audit_builder.build_denial(
        event_type=EVENT_POLICY_HARD_DENIED,
        request=request,
        reason_code="feature_disabled",
    )
    assert event.tenant_id == tenant_id
    assert event.actor_id == "actor-1"
    assert event.correlation_id == "corr-123"
    assert event.specialist_id == "sintra-legal-research"


def test_audit_nested_secret_redacted(audit_builder, tenant_id):
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
        context={
            "outer": {
                "inner": {"api_key": "super-secret"},
                "items": [{"token": "another"}, "safe"],
            }
        },
    )
    event = audit_builder.build_denial(
        event_type=EVENT_POLICY_HARD_DENIED,
        request=request,
        reason_code="feature_disabled",
    )
    data = event.to_dict()
    assert data["metadata"]["redaction_applied"] is True
    assert data["metadata"]["context"]["outer"]["inner"]["api_key"] == "[REDACTED]"
    assert data["metadata"]["context"]["outer"]["items"][0]["token"] == "[REDACTED]"


def test_audit_mixed_case_secret_key_redacted(audit_builder, tenant_id):
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
        context={"API_KEY": "super-secret"},
    )
    event = audit_builder.build_denial(
        event_type=EVENT_POLICY_HARD_DENIED,
        request=request,
        reason_code="feature_disabled",
    )
    data = event.to_dict()
    assert data["metadata"]["context"]["API_KEY"] == "[REDACTED]"


def test_audit_prohibited_fields_absent(audit_builder, tenant_id):
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    event = audit_builder.build_denial(
        event_type=EVENT_POLICY_HARD_DENIED,
        request=request,
        reason_code="feature_disabled",
    )
    data = event.to_dict()
    for prohibited in ("api_key", "token", "secret", "password"):
        assert prohibited not in data


def test_audit_serialization_deterministic(audit_builder, tenant_id):
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
        correlation_id="corr-1",
    )
    event = audit_builder.build_denial(
        event_type=EVENT_POLICY_HARD_DENIED,
        request=request,
        reason_code="feature_disabled",
    )
    s1 = DelegationAuditBuilder.serialize(event)
    s2 = DelegationAuditBuilder.serialize(event)
    assert s1 == s2


def test_audit_rejects_unsafe_serializable_value(audit_builder, tenant_id):
    class BadObject:
        pass

    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
        context={"bad": BadObject()},
    )
    with pytest.raises(AuditRedactionError):
        audit_builder.build_denial(
            event_type=EVENT_POLICY_HARD_DENIED,
            request=request,
            reason_code="feature_disabled",
        )


# ── Audit persistence tests ───────────────────────────────────────────────────


def test_audit_persistence_invoked_exactly_once(registry, enabled_settings, trusted_caller):
    svc = HermesQuicksilverService(registry=registry, settings=enabled_settings)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=trusted_caller.tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.ALLOW

    db_mock = MagicMock()
    calls: list = []

    async def fake_audit(*args, **kwargs):
        calls.append((args, kwargs))
        return MagicMock(id="audit-1")

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("portal.services.audit_service.audit", fake_audit)
        import asyncio

        coro = svc.persist_event(db_mock, event)
        persisted = asyncio.run(coro)

    assert len(calls) == 1
    assert persisted.id == "audit-1"


def test_audit_persistence_fails_closed(registry, enabled_settings, trusted_caller):
    svc = HermesQuicksilverService(registry=registry, settings=enabled_settings)
    request = DelegationRequest(
        operation="list_profiles",
        specialist_id="any",
        tenant_id=trusted_caller.tenant_id,
        actor_id="actor-1",
    )
    result, event = svc.execute(request, caller=trusted_caller)
    assert result.decision == Decision.ALLOW

    db_mock = MagicMock()

    async def failing_audit(*_args, **_kwargs):
        raise RuntimeError("audit write failed")

    import asyncio

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("portal.services.audit_service.audit", failing_audit)
        with pytest.raises(RuntimeError, match="audit write failed"):
            asyncio.run(svc.persist_event(db_mock, event))


# ── CLI safety tests ──────────────────────────────────────────────────────────


def test_cli_arguments_not_shell_interpolated():
    registry = HermesProfileRegistry(cli_executable=["echo", "profile"])
    assert isinstance(registry.cli_executable, list)
    assert all(isinstance(arg, str) for arg in registry.cli_executable)


def test_cli_timeout_fails_closed(tmp_path: Path):
    script = tmp_path / "slow_cli.py"
    script.write_text("import time; time.sleep(100)\n", encoding="utf-8")
    registry = HermesProfileRegistry(
        hermes_home=tmp_path,
        cli_executable=[sys.executable, str(script), "profile", "list", "--json"],
        cli_timeout_seconds=0.1,
    )
    with pytest.raises(HermesProfileRegistryError):
        registry.invoke_cli_profile_list()


# ── External action tests ────────────────────────────────────────────────────


def test_no_external_action_executed(mapping_service, enabled_settings, tenant_id, trusted_caller):
    svc = HermesQuicksilverService(mapping_service=mapping_service, settings=enabled_settings)
    for operation in ("run_agent", "send_message", "execute_tool", "restart_gateway"):
        request = DelegationRequest(
            operation=operation,
            specialist_id="sintra-legal-research",
            tenant_id=tenant_id,
            actor_id="any",
        )
        result, event = svc.execute(request, caller=trusted_caller)
        assert result.decision == Decision.DENY


# ── Version compatibility tests ───────────────────────────────────────────────


def test_minimum_version_enforced(mapping_factory, registry, tenant_id):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.17.0")
    svc.register(mapping_factory())
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "unsupported_version"


def test_maximum_version_enforced(mapping_factory, registry, tenant_id):
    svc = SpecialistMappingService(registry=registry, hermes_version="0.19.1")
    svc.register(mapping_factory())
    request = DelegationRequest(
        operation="validate_profile_mapping",
        specialist_id="sintra-legal-research",
        tenant_id=tenant_id,
        actor_id="any",
    )
    result = svc.resolve(request)
    assert result.decision == Decision.DENY
    assert result.reason_code == "unsupported_version"


# ── Model validation tests ─────────────────────────────────────────────────────


def test_overlapping_tool_classes_rejected(tenant_id):
    with pytest.raises(ValueError):
        SpecialistProfileMapping(
            specialist_id="bad",
            hermes_profile_id="research",
            display_name="Bad",
            allowed_tool_classes=["read"],
            prohibited_tool_classes=["read"],
            tenant_scope=[tenant_id],
            minimum_hermes_version="0.18.0",
        )


def test_empty_tenant_scope_rejected():
    with pytest.raises(ValueError):
        SpecialistProfileMapping(
            specialist_id="bad",
            hermes_profile_id="research",
            display_name="Bad",
            tenant_scope=[],
            minimum_hermes_version="0.18.0",
        )


def test_invalid_hermes_profile_id_rejected(tenant_id):
    with pytest.raises(ValueError):
        SpecialistProfileMapping(
            specialist_id="bad",
            hermes_profile_id="INVALID_ID",
            display_name="Bad",
            tenant_scope=[tenant_id],
            minimum_hermes_version="0.18.0",
        )
