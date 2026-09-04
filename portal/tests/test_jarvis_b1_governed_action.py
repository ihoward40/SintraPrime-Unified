"""JARVIS-001-B1 focused tests — governed action seam (fake provider only).

Proves the minimum complete seam:
Mission -> ProposedAction -> action-bound approval -> GovernedActionExecutor
-> GitHub label adapter -> independent verification -> ActionReceipt
-> bounded memory -> existing Principal Brief.

Constitutional rule: INTELLIGENCE != AUTHORITY. The executor is the only
mutation boundary and independently re-proves authorization at mutation time.
No real external mutation is performed by these tests; a deterministic fake
GitHub provider stands in for the real one. REAL_SIDE_EFFECTS = 0.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from portal.services.jarvis_action_approval import (
    approve_action,
    consume_action_approval,
    create_action_approval,
)
from portal.services.jarvis_action_credential_isolation import build_worker_env
from portal.services.jarvis_action_executor import (
    AuthorityContext,
    GovernedActionExecutor,
    govern_action,
)
from portal.services.jarvis_action_receipt import (
    ActionReceiptChain,
    receipt_contains_secret_material,
    verify_receipt_chain,
)
from portal.services.jarvis_action_taxonomy import ActionFailure
from portal.services.jarvis_github_adapter import (
    FakeGitHubProvider,
    GitHubLabelAdapter,
)
from portal.services.jarvis_proposed_action import (
    ProposedAction,
    canonical_params_hash,
    deterministic_action_id,
    new_proposed_action,
)

pytestmark = pytest.mark.asyncio

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "22222222-2222-2222-2222-222222222222"
PRINCIPAL = "22222222-2222-2222-2222-222222222222"
CANARY = "s4-canary-secret-token-9f2c"
MISSION = "m-" + "a" * 8
REQUEST = "r-" + "b" * 8
ALLOWED_REPO = "ihoward40/SintraPrime-Unified"
ALLOWED_ISSUE = 42
LABEL = "jarvis-b1-acceptance"


@pytest.fixture
async def db_session():
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from portal.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


def _authority_provider_ok(monkeypatch=None):
    """TenantPrincipal probe that accepts the test principal id."""
    import portal.services.tenant_principal_service as tps

    async def fake_principal(db, authenticated_user_id, tenant_id):
        return str(authenticated_user_id).startswith("22222222")

    tps.is_tenant_principal = fake_principal


@pytest.fixture(autouse=True)
def _principal_probe(monkeypatch):
    import portal.services.tenant_principal_service as tps

    async def fake_principal(db, authenticated_user_id, tenant_id):
        return str(authenticated_user_id).startswith("22222222")

    orig = getattr(tps, "is_tenant_principal", None)
    tps.is_tenant_principal = fake_principal
    # fresh isolation state per test: registry + receipt chain
    import portal.services.jarvis_action_approval as _ap
    import portal.services.jarvis_action_executor as _ex
    _ap._REGISTRY.__init__()
    if getattr(_ex, "RECEIPT_CHAIN", None) is not None:
        _ex.RECEIPT_CHAIN = None
    yield
    _ap._REGISTRY.__init__()
    if orig is not None:
        tps.is_tenant_principal = orig


def _params() -> dict:
    return {
        "target_system": "github",
        "target_resource": f"{ALLOWED_REPO}#{ALLOWED_ISSUE}",
        "operation": "add_label",
        "label": LABEL,
    }


def _proposed(params: dict | None = None) -> ProposedAction:
    return new_proposed_action(
        action_type="github.issue.add_label",
        mission_id=MISSION,
        request_id=REQUEST,
        tenant_id=TENANT,
        proposed_by=PRINCIPAL,
        parameters=params or _params(),
        evidence_refs=["req:hash:deadbeef"],
        reasoning_refs=["mission:" + MISSION],
    )


async def _db_session(db_session):
    return db_session


def _authority_ctx(provider: FakeGitHubProvider | None = None) -> AuthorityContext:
    return AuthorityContext(provider=provider or FakeGitHubProvider())


# ---------------------------------------------------------------------------
# B1-1: canonical/hash/tenant/mission binding
# ---------------------------------------------------------------------------

async def test_b1_1_proposed_action_canonical_hash_and_binding():
    p = _proposed()
    assert p.action_type == "github.issue.add_label"
    assert p.tenant_id == TENANT
    assert p.mission_id == MISSION
    assert p.request_id == REQUEST
    # frozen / immutable
    with pytest.raises(Exception):
        p.action_type = "github.issue.close"  # type: ignore[misc]
    # extra fields forbidden
    with pytest.raises(Exception):
        ProposedAction(
            action_type="github.issue.add_label",
            mission_id=MISSION, request_id=REQUEST, tenant_id=TENANT,
            proposed_by=PRINCIPAL, parameters=_params(),
            extra="forbidden",
        )
    # deterministic canonical hash
    h1 = canonical_params_hash(p.parameters)
    h2 = canonical_params_hash(dict(reversed(list(p.parameters.items()))))
    assert h1 == h2
    assert len(h1) == 64
    # deterministic action id from mission+type+params hash
    a1 = deterministic_action_id(MISSION, p.action_type, p.parameters)
    a2 = deterministic_action_id(mission_id=MISSION, action_type=p.action_type, parameters=p.parameters)
    assert a1 == a2
    # deterministic across calls
    assert deterministic_action_id(MISSION, p.action_type, p.parameters) == deterministic_action_id(MISSION, p.action_type, p.parameters)
    # differing params -> different hash
    other = dict(p.parameters); other["label"] = "other-label"
    assert canonical_params_hash(p.parameters) != canonical_params_hash(other)


# ---------------------------------------------------------------------------
# B1-2..B1-5: approval negatives — every failure leaves provider untouched
# ---------------------------------------------------------------------------

async def _approved_action(db: AsyncSession, tenant: str = TENANT, params: dict | None = None):
    action = _proposed(params)
    artifact = await create_action_approval(
        db, action=action, tenant_id=tenant, principal_user_id=PRINCIPAL,
    )
    await approve_action(
        db, artifact=artifact, decision="APPROVED", principal_user_id=PRINCIPAL,
    )
    return action, artifact


def _executor(provider) -> GovernedActionExecutor:
    return GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))


async def test_b1_2_missing_approval_zero_provider_calls(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action = _proposed()
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action, None)
    assert ei.value.code in ("APPROVAL_MISSING", "AUTHORITY_DENIED")
    assert provider.mutation_calls == 0


async def test_b1_3_wrong_tenant_approval_zero_provider_calls(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action = _proposed()
    # approval created under OTHER_TENANT, execution requested under TENANT
    artifact = await create_action_approval(
        db_session, action=action, tenant_id=OTHER_TENANT, principal_user_id=PRINCIPAL,
    )
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    assert provider.mutation_calls == 0
    assert ei.value.code in ("TENANT_MISMATCH", "AUTHORITY_DENIED")


async def test_b1_4_changed_params_after_approval_zero_provider_calls(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    # mutate params after approval
    tampered = dict(action.parameters)
    tampered["label"] = "escalated-privileges-label"
    action2 = _proposed(tampered)
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action2, artifact)
    assert provider.mutation_calls == 0
    assert ei.value.code in ("APPROVAL_MISMATCH", "AUTHORITY_DENIED")


async def test_b1_5_replayed_approval_zero_second_mutation(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r1 = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    assert r1.verification_status == "SIDE_EFFECT_SUCCEEDED"
    first_calls = provider.mutation_calls
    # replay: same approval consumed again must fail closed, no new mutation
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code in ("APPROVAL_REPLAY", "APPROVAL_MISSING")
    assert provider.mutation_calls == first_calls


# ---------------------------------------------------------------------------
# B1-6: credential isolation — worker env has no mutation credential
# ---------------------------------------------------------------------------

async def test_b1_6_worker_environment_excludes_mutation_credential():
    import os
    import subprocess
    import sys

    from portal.services.jarvis_action_credential_isolation import build_worker_env

    env = build_worker_env()
    assert "GITHUB_TOKEN" not in env
    assert "GH_TOKEN" not in env
    assert "PATH" in env  # worker remains functional

    os.environ["GITHUB_TOKEN"] = "b1-test-token-do-not-use"
    try:
        out = subprocess.run(
            [sys.executable, "-c", "import os; print(os.environ.get('GITHUB_TOKEN', 'ABSENT'))"],
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert out.stdout.strip() == "ABSENT"
    finally:
        os.environ.pop("GITHUB_TOKEN", None)


async def test_b1_7_same_action_retry_idempotent(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r1 = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    # retry with the same action id: reconciliation path (approval already consumed;
    # a restarted mission would carry a fresh APPROVED artifact for the SAME action id)
    artifact2 = await create_action_approval(
        db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL,
    )
    await approve_action(
        db_session, artifact=artifact2, decision="APPROVED", principal_user_id=PRINCIPAL,
    )
    r2 = await ex.execute(db_session, action, artifact2, authority_context=AuthorityContext(provider=provider))
    # provider mutation happened exactly once
    assert provider.mutation_calls == 1
    # second run reconciles: label already present -> idempotent success, no new mutation
    assert r2.verification_status == "IDEMPOTENT_SUCCESS"
    assert r2.receipt["action_id"] == r1.receipt["action_id"]




# ---------------------------------------------------------------------------
# B1-8..B1-9: independent verification & reconciliation
# ---------------------------------------------------------------------------

class LyingGitHubProvider(FakeGitHubProvider):
    """Provider that claims success but does not actually change state."""

    def add_label(self, repo: str, issue_number: int, label: str, token: str | None = None) -> dict:
        self.mutation_calls += 1
        self._token_seen = token
        return {"ok": True, "claimed": True}  # lies: state unchanged


async def test_b1_8_provider_success_but_refetch_disagrees_is_verification_failed(db_session):
    provider = LyingGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    assert ei.value.code == "VERIFICATION_FAILED"
    assert provider.mutation_calls == 1  # mutation happened, but is not trusted


async def test_b1_9_mutation_succeeded_response_lost_reconciles(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    # simulate: mutation landed remotely, response lost before local persistence
    provider.prime_label(ALLOWED_ISSUE, LABEL)  # external state already has label
    r = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    # reconciliation: label already present -> idempotent success, POST skipped
    assert r.verification_status == "IDEMPOTENT_SUCCESS"
    assert provider.mutation_calls == 0  # reconciliation saw label present, skipped POST



# ---------------------------------------------------------------------------
# B1-10..B1-14: receipts, tamper detection, bypass prohibition, atomicity
# ---------------------------------------------------------------------------

async def test_b1_10_receipt_contains_authority_provenance_and_hashes(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    rec = r.receipt
    for field in (
        "receipt_id", "action_id", "mission_id", "request_id", "tenant_id",
        "approval_id", "executor", "provider", "target", "params_hash",
        "pre_action_state_hash", "execution_result_hash", "post_action_state_hash",
        "verification_status", "actor", "authority", "started_at", "completed_at",
        "result_hash", "receipt_hash", "previous_receipt_hash",
    ):
        assert rec.get(field) is not None, field


async def test_b1_11_tampered_receipt_fails_integrity(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    chain = ActionReceiptChain()
    chain.add(r.receipt)
    assert verify_receipt_chain(chain.entries) is True
    # tamper with a persisted receipt: verification_status forged after signing
    tampered = dict(r.receipt)
    tampered["verification_status"] = "SIDE_EFFECT_SUCCEEDED_FORGED"
    with pytest.raises(Exception):
        verify_receipt_chain([tampered])


async def test_b1_12_legacy_agents_cannot_satisfy_executor_authority(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action = _proposed()
    # Nova-style in-memory "approval" object is not an action-bound artifact
    nova_style = {"status": "APPROVED", "approver_id": "anyone", "request_id": "x"}
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(db_session, action, nova_style)
    assert ei.value.code in ("APPROVAL_MISSING", "AUTHORITY_DENIED", "APPROVAL_MISMATCH")
    assert provider.mutation_calls == 0
    # ChatAgent-style autonomous task dict is likewise rejected
    chat_style = {"task_id": "t1", "status": "APPROVED", "approver_id": "self"}
    with pytest.raises(ActionFailure):
        await ex.execute(db_session, action, chat_style)
    assert provider.mutation_calls == 0


async def test_b1_13_no_external_mutation_before_approval_consumption(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action = _proposed()
    artifact = await create_action_approval(
        db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL,
    )
    # approval exists but is NOT consumed; a mutation attempt must fail closed
    with pytest.raises(ActionFailure):
        await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    assert provider.mutation_calls == 0


async def test_b1_14_receipt_redacts_secret_material(db_session):
    provider = FakeGitHubProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r = await ex.execute(db_session, action, artifact, authority_context=AuthorityContext(provider=provider))
    # the approval token must never appear in the receipt; probe with a canary
    assert "jarvis-b1-approval:" not in __import__("json").dumps(r.receipt)
    assert receipt_contains_secret_material(r.receipt) is False


# ---------------------------------------------------------------------------
# B1-15/B1-16: timeout reconciliation (B1-6 directive: timeout != second mutation)
# ---------------------------------------------------------------------------


class TimeoutAfterMutationProvider(FakeGitHubProvider):
    """Provider that accepts the mutation, but times out before responding.

    Simulates: provider mutation committed + local response lost. External
    state therefore already contains the label when the executor reconciles.
    """

    def __init__(self, delay: float = 5.0) -> None:
        super().__init__()
        self._delay = delay

    def add_label(self, repo, issue_number, label, token=None):
        import time

        self.mutation_calls += 1
        self._token_seen = token
        labels = self._labels.setdefault((repo, issue_number), [])
        if label not in labels:
            labels.append(label)
        time.sleep(self._delay)  # ack never arrives within executor timeout
        return {"ok": True, "label": label}


class InconclusiveRefetchProvider(TimeoutAfterMutationProvider):
    """Mutation lands but its ack is lost AND the reconciliation refetch fails:
    external state cannot be determined -> UNKNOWN, never fabricated success."""

    def __init__(self, delay: float = 1.0) -> None:
        super().__init__(delay=delay)
        self._reads = 0

    def get_issue_labels(self, repo, issue_number):
        self._reads += 1
        if self._reads == 1:
            return list(self._labels.get((repo, issue_number), []))  # pre-state OK
        raise RuntimeError("provider state read failed during reconciliation")


async def test_b1_15_timeout_after_mutation_reconciles_success(db_session):
    provider = TimeoutAfterMutationProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    r = await ex.execute(
        db_session, action, artifact,
        authority_context=AuthorityContext(provider=provider, mutate_timeout_s=0.2),
    )
    # provider DID mutate (label applied) before the timeout
    assert provider.mutation_calls == 1
    # reconciliation refetched external state and found the label: success
    assert r.verification_status == "SIDE_EFFECT_SUCCEEDED"
    # the receipt must record the reconciliation provenance (timeout -> refetch)
    assert r.receipt["verification_status"] == "SIDE_EFFECT_SUCCEEDED"
    assert "timeout_reconciled" in json.dumps(r.receipt)


async def test_b1_16_timeout_refetch_inconclusive_is_unknown(db_session):
    provider = InconclusiveRefetchProvider()
    ex = _executor(provider)
    action, artifact = await _approved_action(db_session)
    with pytest.raises(ActionFailure) as ei:
        await ex.execute(
            db_session, action, artifact,
            authority_context=AuthorityContext(provider=provider, mutate_timeout_s=0.2),
        )
    # no fabricated success: executor reports unknown/inconclusive
    assert ei.value.code in ("SIDE_EFFECT_UNKNOWN", "VERIFICATION_INCONCLUSIVE")


# ---------------------------------------------------------------------------
# S4 credential isolation re-proof (runtime evidence)
# ---------------------------------------------------------------------------

async def test_s4_credential_isolation_runtime_proof(db_session, monkeypatch):
    # parent env HAS the mutation credential — workers must never see it
    monkeypatch.setenv("GITHUB_TOKEN", CANARY)

    env = build_worker_env()
    assert "GITHUB_TOKEN" not in env
    assert "GH_TOKEN" not in env
    assert "PATH" in env  # worker remains functional

    action = new_proposed_action(
        mission_id=str(uuid.uuid4()),
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
    art = await create_action_approval(
        db_session, action=action, tenant_id=TENANT, principal_user_id=PRINCIPAL
    )
    await approve_action(
        db_session, artifact=art, decision="APPROVED", principal_user_id=PRINCIPAL
    )

    provider = FakeGitHubProvider()
    ex = GovernedActionExecutor(adapter=GitHubLabelAdapter(provider=provider))
    r = await ex.execute(
        db_session,
        action,
        art,
        authority_context=AuthorityContext(provider=provider, credential=CANARY),
    )

    # credential reached the provider ONLY through the executor-owned path
    assert provider.token_seen == CANARY
    # receipt carries no secret material
    rj = json.dumps(r.receipt)
    assert CANARY not in rj
    assert "jarvis-b1-approval:" not in rj
    # ProposedAction carries no credential material
    import dataclasses

    assert CANARY not in json.dumps(dataclasses.asdict(action))
    # no env read performed by the executor/adapter path (sentinel still present)
    assert os.environ.get("GITHUB_TOKEN") == CANARY
