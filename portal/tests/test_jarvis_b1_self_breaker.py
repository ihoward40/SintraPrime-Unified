"""S6 SELF-BREAKER probes (independent Breaker BLOCKED by provider 402).

Non-mutating adversarial probes against the B1 seam. In-memory DB only.
Attacks: authority bypass, replay, params drift, tenant crossing, credential
leak, double execution, timeout semantics, false success, receipt tamper,
bypass imports, real-provider reachability.
Run: python -m pytest portal/tests/test_jarvis_b1_self_breaker.py
"""
from __future__ import annotations

import json
import uuid

import pytest

from portal.services.jarvis_action_approval import (
    approve_action,
    create_action_approval,
)
from portal.services.jarvis_action_executor import (
    AuthorityContext,
    GovernedActionExecutor,
)
from portal.services.jarvis_action_receipt import verify_receipt_chain
from portal.services.jarvis_action_taxonomy import ActionFailure
from portal.services.jarvis_github_adapter import FakeGitHubProvider, GitHubLabelAdapter
from portal.services.jarvis_proposed_action import new_proposed_action

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "33333333-3333-3333-3333-333333333333"
PRINCIPAL = "22222222-2222-2222-2222-222222222222"
MISSION = str(uuid.uuid4())


@pytest.fixture
async def db_session():
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from portal.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _principal_probe():
    """Accept the test principal and isolate registry/receipt-chain state per test."""
    import portal.services.jarvis_action_approval as _ap
    import portal.services.jarvis_action_executor as _ex
    import portal.services.tenant_principal_service as tps

    async def fake_principal(db, authenticated_user_id, tenant_id):
        return str(authenticated_user_id).startswith("22222222")

    orig = getattr(tps, "is_tenant_principal", None)
    tps.is_tenant_principal = fake_principal
    _ap._REGISTRY.__init__()
    if getattr(_ex, "RECEIPT_CHAIN", None) is not None:
        _ex.RECEIPT_CHAIN = None
    yield
    _ap._REGISTRY.__init__()
    if orig is not None:
        tps.is_tenant_principal = orig


def _action():
    return new_proposed_action(
        mission_id=MISSION,
        request_id=str(uuid.uuid4()),
        tenant_id=TENANT,
        action_type="github.issue.add_label",
        proposed_by=PRINCIPAL,
        parameters={
            "target_system": "github",
            "target_resource": "ihoward40/SintraPrime-Unified#42",
            "operation": "add_label",
            "label": "jarvis-b1-acceptance",
        },
    )


async def _approved(db, action, tenant=TENANT, principal=PRINCIPAL):
    art = await create_action_approval(db, action=action, tenant_id=tenant, principal_user_id=PRINCIPAL)
    await approve_action(db, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    return art


# BK-1 missing approval -> zero provider calls
async def test_bk1_no_approval_zero_calls(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    with pytest.raises(Exception):
        await ex.execute(db_session, _action(), None, authority_context=AuthorityContext(provider=provider))
    assert provider.mutation_calls == 0


# BK-2 tenant crossing -> zero provider calls
async def test_bk2_tenant_crossing_zero_calls(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=OTHER_TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    with pytest.raises(Exception) as ei:
        await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code == "TENANT_MISMATCH"
    assert provider.mutation_calls == 0


# BK-3 params drift after approval -> zero provider calls
async def test_bk3_params_drift_after_approval(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    from portal.services.jarvis_proposed_action import ProposedAction, canonical_params_hash
    drifted = ProposedAction(
        action_id=action.action_id, mission_id=action.mission_id, request_id=action.request_id,
        tenant_id=action.tenant_id, action_type=action.action_type,
        target_system=action.target_system, target_resource=action.target_resource,
        operation=action.operation, parameters=dict(action.parameters, label="jarvis-b1-acceptance-evil"),
        params_hash=canonical_params_hash({**action.parameters, "label": "jarvis-b1-acceptance-evil"}),
        risk_class=action.risk_class, consequence_class=action.consequence_class,
        authority_required=action.authority_required, approval_required=action.approval_required,
        proposed_by=action.proposed_by, created_at=action.created_at,
        evidence_refs=action.evidence_refs, reasoning_refs=action.reasoning_refs,
    )
    with pytest.raises(Exception) as ei:
        await ex.execute(db_session, drifted, art, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code == "APPROVAL_MISMATCH"
    assert provider.mutation_calls == 0


# BK-4 PENDING approval -> zero calls; dict approval -> zero calls
async def test_bk4_pending_and_dict_approvals_rejected(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    # dict-style Nova approval must be rejected
    with pytest.raises(Exception):
        await ex.execute(db_session, action, {"approval_id": "x"}, authority_context=AuthorityContext(provider=provider))
    assert provider.mutation_calls == 0
    # PENDING artifact must not authorize
    with pytest.raises(Exception):
        await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider))
    assert provider.mutation_calls == 0


# BK-5 replay: consumed artifact cannot authorize a second mutation
async def test_bk5_replayed_approval_no_second_mutation(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    # consume the approval out-of-band (simulates an executed-then-lost-receipt run)
    from portal.services.jarvis_action_approval import consume_action_approval
    await consume_action_approval(db_session, artifact=art)
    # replay attempt with label ABSENT: must not mutate again
    with pytest.raises(Exception) as ei:
        await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code == "APPROVAL_REPLAY"
    assert provider.mutation_calls == 0


# BK-6 false provider success -> VERIFICATION_FAILED, no success receipt
async def test_bk6_false_success_is_verification_failed(db_session):
    from portal.services.jarvis_github_adapter import FakeGitHubProvider as F

    class Liar(F):
        def add_label(self, repo, issue_number, label, token=None):
            self.mutation_calls += 1
            return {"ok": True}

    provider = Liar()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    with pytest.raises(Exception) as ei:
        await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code == "VERIFICATION_FAILED"
    assert provider.mutation_calls == 1


# BK-7 receipt tamper detection
async def test_bk7_receipt_tamper_detected(db_session):
    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    r = await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider))
    forged = dict(r.receipt)
    forged["verification_status"] = "SIDE_EFFECT_SUCCEEDED_FORGED"
    with pytest.raises(Exception):
        verify_receipt_chain([forged])


# BK-8 timeout UNKNOWN must NOT consume approval (retry remains governed)
async def test_bk8_unknown_leaves_approval_unconsumed(db_session):
    from portal.tests.test_jarvis_b1_governed_action import InconclusiveRefetchProvider
    provider = InconclusiveRefetchProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    action = _action()
    art = await create_action_approval(db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL)
    await approve_action(db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL)
    with pytest.raises(Exception) as ei:
        await ex.execute(db_session, action, art, authority_context=AuthorityContext(provider=provider, mutate_timeout_s=0.2))
    assert ei.value.code in ("SIDE_EFFECT_UNKNOWN", "VERIFICATION_INCONCLUSIVE")
    # approval NOT consumed on unknown: a Principal decision (not the executor) gates retry
    assert art.status == "APPROVED", f"approval state after unknown: {art.status}"


# BK-9 no network-capable imports anywhere in B1 services
def test_bk9_no_network_imports():
    import pathlib
    bad = ("httpx", "requests", "urllib", "socket", "aiohttp", "http.client", "urllib3")
    for f in pathlib.Path("portal/services").glob("jarvis_action_*.py"):
        src = f.read_text(encoding="utf-8")
        for b in bad:
            assert b not in src, f"{f.name} references {b}"
    ad = pathlib.Path("portal/services/jarvis_github_adapter.py").read_text(encoding="utf-8")
    for b in bad:
        assert b not in ad, f"adapter references {b}"


# BK-10 no legacy agent imports in B1
def test_bk10_no_legacy_agent_imports():
    import ast
    import pathlib
    files = list(pathlib.Path("portal/services").glob("jarvis_action_*.py"))
    files.append(pathlib.Path("portal/services/jarvis_github_adapter.py"))
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = " ".join(a.name for a in getattr(node, "names", []))
                for legacy in ("agents", "approval_gateway", "approval_gate"):
                    assert legacy not in mod, f"{f.name} imports {legacy}"
                    assert legacy not in names, f"{f.name} imports {legacy}"
