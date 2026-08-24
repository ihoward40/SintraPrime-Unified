"""L1 GitHub Single Comment Execution Runner.

This module implements the narrowly scoped L1 execution runner for exactly
one Principal-approved certification comment on PR #285.

IMPLEMENTATION AUTHORITY ONLY - NO LIVE EXECUTION AUTHORITY.
The actual execution requires separate fresh Principal approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from sintra_live.github_app.auth import GitHubAppAuthenticator, GitHubAppAuthSession
from sintra_live.github_comment.capability import (
    GitHubCommentActionEnvelope,
    M2B_TARGET_REPOSITORY,
    create_comment_action_envelope,
    verify_action_envelope,
)
from sintra_live.github_comment.evidence import GitHubCommentEvidenceChain


def create_approval_hash(content: str) -> str:
    """Create approval hash from content string."""
    return hashlib.sha256(content.encode()).hexdigest()


class L1ExecutionStatus(Enum):
    """L1 execution status."""
    NOT_STARTED = "NOT_STARTED"
    PRE_FLIGHT = "PRE_FLIGHT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AUTHORITY_VERIFIED = "AUTHORITY_VERIFIED"
    EXECUTING = "EXECUTING"
    POST_COMPLETED = "POST_COMPLETED"
    READBACK_VERIFIED = "READBACK_VERIFIED"
    EVIDENCE_SEALED = "EVIDENCE_SEALED"
    AUTHORITY_CONSUMED = "AUTHORITY_CONSUMED"
    FAILED = "FAILED"


class L1FailureReason(Enum):
    """Reasons for L1 failure."""
    BODY_HASH_MISMATCH = "BODY_HASH_MISMATCH"
    REPO_MISMATCH = "REPO_MISMATCH"
    PR_MISMATCH = "PR_MISMATCH"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    INSTALLATION_SCOPE_MISMATCH = "INSTALLATION_SCOPE_MISMATCH"
    PERMISSIONS_INSUFFICIENT = "PERMISSIONS_INSUFFICIENT"
    PR_CLOSED = "PR_CLOSED"
    APPROVAL_MISSING = "APPROVAL_MISSING"
    APPROVAL_STALE = "APPROVAL_STALE"
    APPROVAL_HASH_MISMATCH = "APPROVAL_HASH_MISMATCH"
    NONCE_ALREADY_CONSUMED = "NONCE_ALREADY_CONSUMED"
    DUPLICATE_COMMENT_EXISTS = "DUPLICATE_COMMENT_EXISTS"
    PROVIDER_RESPONSE_AMBIGUOUS = "PROVIDER_RESPONSE_AMBIGUOUS"
    TIMEOUT_BEFORE_OUTCOME = "TIMEOUT_BEFORE_OUTCOME"
    READBACK_VERIFICATION_FAILED = "READBACK_VERIFICATION_FAILED"
    SECOND_POST_ATTEMPTED = "SECOND_POST_ATTEMPTED"
    BROADER_GITHUB_OPERATION_ATTEMPTED = "BROADER_GITHUB_OPERATION_ATTEMPTED"
    TOKEN_LEAKAGE_DETECTED = "TOKEN_LEAKAGE_DETECTED"


@dataclass(frozen=True)
class L1ExecutionNonce:
    """Single-use execution nonce."""
    nonce: str
    created_at: float
    consumed_at: Optional[float] = None
    consumed: bool = False

    def mark_consumed(self) -> 'L1ExecutionNonce':
        return L1ExecutionNonce(
            nonce=self.nonce,
            created_at=self.created_at,
            consumed_at=time.time(),
            consumed=True
        )

    @classmethod
    def generate(cls) -> 'L1ExecutionNonce':
        return cls(nonce=str(uuid.uuid4()), created_at=time.time())


class ExecutionState(Enum):
    """Durable execution states for replay prevention."""
    PREPARED = "PREPARED"
    APPROVED = "APPROVED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    PROVIDER_ATTEMPT_RECORDED = "PROVIDER_ATTEMPT_RECORDED"
    VERIFIED = "VERIFIED"
    CONSUMED = "CONSUMED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class DurableExecutionState:
    """Persisted execution state for crash/replay durability."""
    execution_id: str
    nonce: str
    state: ExecutionState
    approval_hash: str
    body_hash: str
    target_repository: str
    target_pr: int
    created_at: float
    updated_at: float
    provider_response_hash: Optional[str] = None

    @classmethod
    def create(cls, execution_id: str, nonce: str, approval_hash: str,
               body_hash: str, target_repository: str, target_pr: int) -> 'DurableExecutionState':
        now = time.time()
        return cls(
            execution_id=execution_id,
            nonce=nonce,
            state=ExecutionState.PREPARED,
            approval_hash=approval_hash,
            body_hash=body_hash,
            target_repository=target_repository,
            target_pr=target_pr,
            created_at=now,
            updated_at=now
        )

    def with_state(self, new_state: ExecutionState, provider_response_hash: Optional[str] = None) -> 'DurableExecutionState':
        return DurableExecutionState(
            execution_id=self.execution_id,
            nonce=self.nonce,
            state=new_state,
            approval_hash=self.approval_hash,
            body_hash=self.body_hash,
            target_repository=self.target_repository,
            target_pr=self.target_pr,
            created_at=self.created_at,
            updated_at=time.time(),
            provider_response_hash=provider_response_hash or self.provider_response_hash
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "nonce": self.nonce,
            "state": self.state.value,
            "approval_hash": self.approval_hash,
            "body_hash": self.body_hash,
            "target_repository": self.target_repository,
            "target_pr": self.target_pr,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provider_response_hash": self.provider_response_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DurableExecutionState':
        return cls(
            execution_id=data["execution_id"],
            nonce=data["nonce"],
            state=ExecutionState(data["state"]),
            approval_hash=data["approval_hash"],
            body_hash=data["body_hash"],
            target_repository=data["target_repository"],
            target_pr=data["target_pr"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            provider_response_hash=data.get("provider_response_hash")
        )


@dataclass(frozen=True)
class L1ApprovalRecord:
    """Fresh Principal approval record."""
    approval_id: str
    principal_id: str
    account: str
    repository: str
    pr_number: int
    capability: str
    body_hash: str
    max_executions: int
    nonce: str
    timestamp: float
    approval_hash: str

    @classmethod
    def create(
        cls,
        principal_id: str,
        account: str,
        repository: str,
        pr_number: int,
        capability: str,
        body_hash: str,
        max_executions: int,
        nonce: str
    ) -> 'L1ApprovalRecord':
        approval_hash = create_approval_hash(
            f"{principal_id}|{account}|{repository}|{pr_number}|{capability}|{body_hash}|{max_executions}|{nonce}"
        )
        return cls(
            approval_id=str(uuid.uuid4()),
            principal_id=principal_id,
            account=account,
            repository=repository,
            pr_number=pr_number,
            capability=capability,
            body_hash=body_hash,
            max_executions=max_executions,
            nonce=nonce,
            timestamp=time.time(),
            approval_hash=approval_hash
        )

    def verify(self) -> bool:
        """Verify approval hash integrity."""
        expected = create_approval_hash(
            f"{self.principal_id}|{self.account}|{self.repository}|{self.pr_number}|"
            f"{self.capability}|{self.body_hash}|{self.max_executions}|{self.nonce}"
        )
        return expected == self.approval_hash


@dataclass(frozen=True)
class L1ExecutionResult:
    """Result of L1 execution attempt."""
    execution_id: str
    status: L1ExecutionStatus
    approval: Optional[L1ApprovalRecord]
    nonce: Optional[L1ExecutionNonce]
    provider_response: Optional[Dict[str, Any]]
    readback_verification: Optional[Dict[str, Any]]
    failure_reason: Optional[L1FailureReason]
    error_message: Optional[str]
    evidence_chain_root: Optional[str]
    timestamp: float = field(default_factory=time.time)


class L1CommentRunner:
    """L1 Single Comment Execution Runner - Implementation Authority Only."""

    # Authorized constants (hash-bound, immutable)
    AUTHORIZED_REPOSITORY = "ihoward40/SintraPrime-Unified"
    AUTHORIZED_PR_NUMBER = 285
    AUTHORIZED_COMMENT_BODY = (
        "SintraPrime SP-LIVE-001 governed-action certification: "
        "Principal-approved external action successfully executed and verified."
    )
    AUTHORIZED_BODY_HASH = "9fac685186ee96aa62ff60eb818fe65857530f69e188c74997a035e5b5f842b1"
    AUTHORIZED_CAPABILITY = "provider.github-issue-comment-create-v1"
    AUTHORIZED_ACCOUNT = "ihoward40"
    MAX_EXECUTIONS = 1
    APPROVAL_EXPIRY_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        authenticator: GitHubAppAuthenticator,
        principal_id: str = "principal-001",
        binding_id: str = "binding-m2a-certified"
    ):
        self.authenticator = authenticator
        self.principal_id = principal_id
        self.binding_id = binding_id
        self.evidence_chain = GitHubCommentEvidenceChain(chain_id="l1-execution")
        self.status = L1ExecutionStatus.NOT_STARTED
        self.execution_id = str(uuid.uuid4())
        self._nonce: Optional[L1ExecutionNonce] = None
        self._approval: Optional[L1ApprovalRecord] = None
        self._provider_response: Optional[Dict[str, Any]] = None
        self._readback_verification: Optional[Dict[str, Any]] = None

    # ==================== PRE-FLIGHT VERIFICATION ====================

    def run_preflight_checks(self) -> Dict[str, Any]:
        """Run all pre-flight verification checks."""
        self.status = L1ExecutionStatus.PRE_FLIGHT
        results = {
            "authenticated": False,
            "account_match": False,
            "installation_match": False,
            "permissions_match": False,
            "pr_open": False,
            "errors": []
        }

        session = self.authenticator.session
        if not session:
            results["errors"].append("No authenticated session")
            return results

        results["authenticated"] = True

        # 1. Account binding verification
        account_match = session.user.login.lower() == self.AUTHORIZED_ACCOUNT.lower()
        results["account_match"] = account_match
        if not account_match:
            results["errors"].append(f"Account mismatch: {session.user.login} != {self.AUTHORIZED_ACCOUNT}")

        # 2. Installation verification
        installation = session.installation
        if not installation:
            results["errors"].append("No GitHub App installation found")
        else:
            repo_names = [r.get("full_name", "") for r in installation.repositories]
            installation_match = (
                installation.repository_selection == "selected" and
                repo_names == [self.AUTHORIZED_REPOSITORY]
            )
            results["installation_match"] = installation_match
            if not installation_match:
                results["errors"].append(f"Installation scope mismatch: {repo_names}")

            # 3. Permissions verification
            effective_perms = {k: v for k, v in installation.permissions.items() if v != "none"}
            expected_perms = {"pull_requests": "write", "metadata": "read"}
            permissions_match = effective_perms == expected_perms
            results["permissions_match"] = permissions_match
            if not permissions_match:
                results["errors"].append(f"Permissions mismatch: {effective_perms}")

        # 4. PR verification
        if installation:
            pr_check = self.authenticator.verify_pr_access(
                "ihoward40", "SintraPrime-Unified", self.AUTHORIZED_PR_NUMBER
            )
            pr_open = pr_check.get("accessible", False) and pr_check.get("state") == "open"
            results["pr_open"] = pr_open
            if not pr_open:
                results["errors"].append(f"PR #{self.AUTHORIZED_PR_NUMBER} not accessible or not open")

        # Record preflight evidence
        self.evidence_chain.append(
            "preflight_checks",
            self.execution_id,
            self.binding_id,
            self.principal_id,
            results
        )

        return results

    def display_preflight_summary(self, results: Dict[str, Any]) -> None:
        """Display preflight results for Principal review."""
        print("\n" + "=" * 70)
        print("L1 PRE-FLIGHT VERIFICATION")
        print("=" * 70)
        print(f"Execution ID: {self.execution_id}")
        print(f"Target: {self.AUTHORIZED_REPOSITORY} PR #{self.AUTHORIZED_PR_NUMBER}")
        print(f"Authorized Account: {self.AUTHORIZED_ACCOUNT}")
        print()
        print("CHECKS:")
        print(f"  Authenticated:         {'✓' if results['authenticated'] else '✗'}")
        print(f"  Account Match:         {'✓' if results['account_match'] else '✗'}")
        print(f"  Installation Match:    {'✓' if results['installation_match'] else '✗'}")
        print(f"  Permissions Match:     {'✓' if results['permissions_match'] else '✗'}")
        print(f"  PR Open:               {'✓' if results['pr_open'] else '✗'}")
        print()
        if results["errors"]:
            print("ERRORS:")
            for err in results["errors"]:
                print(f"  ✗ {err}")
            print()

    # ==================== COMMITMENT DISPLAY ====================

    def display_execution_commitment(self) -> None:
        """Display exact execution commitment for Principal approval."""
        self._nonce = L1ExecutionNonce.generate()

        print("\n" + "=" * 70)
        print("L1 EXECUTION COMMITMENT - PRINCIPAL APPROVAL REQUIRED")
        print("=" * 70)
        print()
        print("EXACT COMMENT TO BE POSTED:")
        print("-" * 50)
        print(self.AUTHORIZED_COMMENT_BODY)
        print("-" * 50)
        print()
        print("COMMITMENT FIELDS:")
        print(f"  Execution ID:      {self.execution_id}")
        print(f"  Execution Nonce:   {self._nonce.nonce}")
        print(f"  Target Account:    {self.AUTHORIZED_ACCOUNT}")
        print(f"  Target Repository: {self.AUTHORIZED_REPOSITORY}")
        print(f"  Target PR:         #{self.AUTHORIZED_PR_NUMBER}")
        print(f"  Capability:        {self.AUTHORIZED_CAPABILITY}")
        print(f"  Comment Body SHA256: {self.AUTHORIZED_BODY_HASH}")
        print(f"  Max Executions:    {self.MAX_EXECUTIONS}")
        print(f"  Timestamp:         {time.time():.0f}")
        print()
        print("APPROVAL WILL BIND TO:")
        print("  - Authenticated GitHub account")
        print("  - Target repository (ihoward40/SintraPrime-Unified)")
        print("  - Target PR (#285)")
        print("  - Capability (provider.github-issue-comment-create-v1)")
        print("  - Exact comment body SHA256")
        print("  - Max executions = 1")
        print("  - Execution nonce (single-use)")
        print("  - Approval timestamp")
        print()
        print("POST WILL BE TO:")
        print(f"  POST /repos/{self.AUTHORIZED_REPOSITORY}/issues/{self.AUTHORIZED_PR_NUMBER}/comments")
        print()
        print("=" * 70)

    # ==================== APPROVAL HANDLING ====================

    def obtain_principal_approval(self) -> L1ApprovalRecord:
        """Obtain explicit Principal approval."""
        self.status = L1ExecutionStatus.AWAITING_APPROVAL

        approval = L1ApprovalRecord.create(
            principal_id=self.principal_id,
            account=self.AUTHORIZED_ACCOUNT,
            repository=self.AUTHORIZED_REPOSITORY,
            pr_number=self.AUTHORIZED_PR_NUMBER,
            capability=self.AUTHORIZED_CAPABILITY,
            body_hash=self.AUTHORIZED_BODY_HASH,
            max_executions=self.MAX_EXECUTIONS,
            nonce=self._nonce.nonce
        )

        # Display approval hash for transparency
        print(f"Approval Hash: {approval.approval_hash}")
        print()

        # In a real implementation, this would be voice/signed approval
        # For this implementation, we simulate the approval capture
        # The actual execution phase will require explicit confirmation

        self._approval = approval

        self.evidence_chain.append(
            "approval_recorded",
            self.execution_id,
            self.binding_id,
            self.principal_id,
            {
                "approval_id": approval.approval_id,
                "approval_hash": approval.approval_hash,
                "nonce": approval.nonce,
                "timestamp": approval.timestamp
            }
        )

        return approval

    def verify_approval(self, approval: L1ApprovalRecord) -> bool:
        """Verify approval integrity and freshness."""
        # Check hash integrity
        if not approval.verify():
            return False

        # Check freshness
        age = time.time() - approval.timestamp
        if age > self.APPROVAL_EXPIRY_SECONDS:
            return False

        # Check binding fields match authorized values
        if (approval.account != self.AUTHORIZED_ACCOUNT or
            approval.repository != self.AUTHORIZED_REPOSITORY or
            approval.pr_number != self.AUTHORIZED_PR_NUMBER or
            approval.capability != self.AUTHORIZED_CAPABILITY or
            approval.body_hash != self.AUTHORIZED_BODY_HASH or
            approval.max_executions != self.MAX_EXECUTIONS or
            approval.nonce != self._nonce.nonce):
            return False

        return True

    # ==================== DURABLE STATE PERSISTENCE ====================

    def _get_state_file_path(self) -> Path:
        """Get path to durable execution state file."""
        state_dir = Path(".l1_execution_state")
        state_dir.mkdir(exist_ok=True)
        return state_dir / f"{self.execution_id}.json"

    def _save_durable_state(self, state: DurableExecutionState) -> None:
        """Persist execution state to disk."""
        path = self._get_state_file_path()
        with open(path, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def _load_durable_state(self) -> Optional[DurableExecutionState]:
        """Load execution state from disk if exists."""
        path = self._get_state_file_path()
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return DurableExecutionState.from_dict(data)
        except Exception:
            return None

    def _check_existing_execution(self) -> Optional[DurableExecutionState]:
        """Check for existing execution state (replay prevention)."""
        return self._load_durable_state()

    def _reconcile_on_restart(self, state: DurableExecutionState) -> L1ExecutionResult:
        """Reconcile execution outcome after restart.
        
        If state is EXECUTION_STARTED or PROVIDER_ATTEMPT_RECORDED,
        read back comments to determine if POST succeeded.
        """
        print(f"Reconciling execution {state.execution_id} in state: {state.state.value}")
        
        if state.state not in [ExecutionState.EXECUTION_STARTED, ExecutionState.PROVIDER_ATTEMPT_RECORDED]:
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=None,
                readback_verification=None,
                failure_reason=L1FailureReason.NONCE_ALREADY_CONSUMED,
                error_message=f"Execution already in terminal state: {state.state.value}",
                evidence_chain_root=None
            )

        # Read back comments to check if comment was created
        dup_check = self.check_duplicate_comment()
        
        if dup_check.get("found"):
            # Comment exists - verify it matches our exact specification
            readback = self.verify_readback({"response": dup_check})
            if readback.get("all_verified"):
                # Verified - mark consumed
                new_state = state.with_state(ExecutionState.VERIFIED, provider_response_hash="verified")
                self._save_durable_state(new_state)
                new_state = state.with_state(ExecutionState.CONSUMED)
                self._save_durable_state(new_state)
                return L1ExecutionResult(
                    execution_id=self.execution_id,
                    status=L1ExecutionStatus.AUTHORITY_CONSUMED,
                    approval=self._approval,
                    nonce=self._nonce,
                    provider_response=dup_check,
                    readback_verification=readback,
                    failure_reason=None,
                    error_message=None,
                    evidence_chain_root=self.evidence_chain.get_chain_root()
                )
            else:
                # Comment exists but doesn't match - unverifiable
                new_state = state.with_state(ExecutionState.UNVERIFIED)
                self._save_durable_state(new_state)
                return L1ExecutionResult(
                    execution_id=self.execution_id,
                    status=L1ExecutionStatus.FAILED,
                    approval=self._approval,
                    nonce=self._nonce,
                    provider_response=dup_check,
                    readback_verification=readback,
                    failure_reason=L1FailureReason.READBACK_VERIFICATION_FAILED,
                    error_message="Comment exists but verification failed",
                    evidence_chain_root=None
                )
        else:
            # No matching comment found - UNVERIFIED
            new_state = state.with_state(ExecutionState.UNVERIFIED)
            self._save_durable_state(new_state)
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=None,
                readback_verification={"verified": False, "error": "No matching comment found after reconciliation"},
                failure_reason=L1FailureReason.TIMEOUT_BEFORE_OUTCOME,
                error_message="Reconciliation: no matching comment found after timeout",
                evidence_chain_root=None
            )

    def check_duplicate_comment(self) -> Dict[str, Any]:
        """Check for existing exact duplicate comment."""
        if not self.authenticator.session:
            return {"found": False, "error": "No session"}

        headers = {
            "Authorization": f"Bearer {self.authenticator._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        import requests
        response = requests.get(
            f"{self.authenticator.config.api_url}/repos/ihoward40/SintraPrime-Unified/issues/{self.AUTHORIZED_PR_NUMBER}/comments",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return {"found": False, "error": f"HTTP {response.status_code}"}

        comments = response.json()
        for comment in comments:
            body = comment.get("body", "")
            if hashlib.sha256(body.encode()).hexdigest() == self.AUTHORIZED_BODY_HASH:
                return {
                    "found": True,
                    "comment_id": comment.get("id"),
                    "author": comment.get("user", {}).get("login"),
                    "created_at": comment.get("created_at")
                }

        return {"found": False}

    def execute_comment_post(self) -> Dict[str, Any]:
        """Execute the single POST to create the comment.
        
        Handles timeout reconciliation and durable state persistence.
        """
        if not self.authenticator.session:
            return {"success": False, "error": "No authenticated session"}

        # Duplicate check
        dup_check = self.check_duplicate_comment()
        if dup_check.get("found"):
            return {
                "success": False,
                "error": "Duplicate comment already exists",
                "duplicate": dup_check
            }

        # Nonce consumption check
        if self._nonce and self._nonce.consumed:
            return {"success": False, "error": "Nonce already consumed"}

        # Persist execution state BEFORE POST
        durable = DurableExecutionState.create(
            execution_id=self.execution_id,
            nonce=self._nonce.nonce if self._nonce else "none",
            approval_hash=self._approval.approval_hash if self._approval else "none",
            body_hash=self.AUTHORIZED_BODY_HASH,
            target_repository=self.AUTHORIZED_REPOSITORY,
            target_pr=self.AUTHORIZED_PR_NUMBER
        )
        durable = durable.with_state(ExecutionState.EXECUTION_STARTED)
        self._save_durable_state(durable)

        headers = {
            "Authorization": f"Bearer {self.authenticator._raw_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }

        import requests
        try:
            response = requests.post(
                f"{self.authenticator.config.api_url}/repos/ihoward40/SintraPrime-Unified/issues/{self.AUTHORIZED_PR_NUMBER}/comments",
                headers=headers,
                json={"body": self.AUTHORIZED_COMMENT_BODY},
                timeout=30
            )
            # Record provider attempt
            durable = durable.with_state(ExecutionState.PROVIDER_ATTEMPT_RECORDED)
            self._save_durable_state(durable)

            if response.status_code == 201:
                # Mark nonce consumed on success
                if self._nonce:
                    self._nonce = self._nonce.mark_consumed()
                # Record provider response hash
                provider_hash = hashlib.sha256(json.dumps(response.json(), sort_keys=True).encode()).hexdigest()
                durable = durable.with_state(ExecutionState.VERIFIED, provider_response_hash=provider_hash)
                self._save_durable_state(durable)
                durable = durable.with_state(ExecutionState.CONSUMED)
                self._save_durable_state(durable)
                return {"success": True, "response": response.json()}
            elif response.status_code == 422:
                # Check if it's a duplicate
                dup_check = self.check_duplicate_comment()
                if dup_check.get("found"):
                    return {
                        "success": False,
                        "error": "Duplicate comment detected on retry",
                        "duplicate": dup_check
                    }
                return {"success": False, "error": f"Validation failed: {response.text}"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except requests.Timeout as e:
            # Timeout after send may have occurred - DO NOT retry
            durable = durable.with_state(ExecutionState.PROVIDER_ATTEMPT_RECORDED)
            self._save_durable_state(durable)
            return {
                "success": False,
                "error": "TIMEOUT_BEFORE_OUTCOME - reconciliation required",
                "timeout": True,
                "provider_may_have_sent": True
            }
        except requests.RequestException as e:
            # Pre-send connection failure - safe to retry
            durable = durable.with_state(ExecutionState.FAILED)
            self._save_durable_state(durable)
            return {
                "success": False,
                "error": f"Connection failure: {str(e)}",
                "timeout": False,
                "provider_may_have_sent": False
            }

    # ==================== READ-BACK VERIFICATION ====================

    def verify_readback(self, provider_response: Dict[str, Any]) -> Dict[str, Any]:
        """Independent read-back verification of the posted comment."""
        comment_id = provider_response.get("response", {}).get("id")
        if not comment_id:
            return {"verified": False, "error": "No comment ID in provider response"}

        headers = {
            "Authorization": f"Bearer {self.authenticator._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        import requests
        response = requests.get(
            f"{self.authenticator.config.api_url}/repos/ihoward40/SintraPrime-Unified/issues/{self.AUTHORIZED_PR_NUMBER}/comments",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return {"verified": False, "error": f"Readback HTTP {response.status_code}"}

        comments = response.json()
        target_comment = None
        for c in comments:
            if c.get("id") == comment_id:
                target_comment = c
                break

        if not target_comment:
            return {"verified": False, "error": "Comment not found in readback"}

        # Verify all fields
        actual_body = target_comment.get("body", "")
        actual_hash = hashlib.sha256(actual_body.encode()).hexdigest()
        author = target_comment.get("user", {}).get("login")

        checks = {
            "target_verified": target_comment.get("id") == comment_id,
            "author_verified": author == self.AUTHORIZED_ACCOUNT,
            "body_hash_verified": actual_hash == self.AUTHORIZED_BODY_HASH,
            "target_pr_verified": True,  # We queried the correct PR endpoint
            "author": author,
            "body": actual_body,
            "body_hash": actual_hash,
            "comment_id": comment_id,
            "comment_url": target_comment.get("html_url"),
            "created_at": target_comment.get("created_at")
        }

        checks["all_verified"] = all([
            checks["target_verified"],
            checks["author_verified"],
            checks["body_hash_verified"],
            checks["target_pr_verified"]
        ])

        return checks

    # ==================== MAIN ORCHESTRATION ====================

    def run_zero_write_preflight(self) -> Dict[str, Any]:
        """Run complete zero-write preflight (no actual POST)."""
        print("\n" + "=" * 70)
        print("L1 ZERO-WRITE PREFLIGHT EXECUTION")
        print("=" * 70)

        # 1. Preflight checks
        preflight = self.run_preflight_checks()
        self.display_preflight_summary(preflight)

        if preflight["errors"]:
            print("✗ PREFLIGHT FAILED - Cannot proceed to approval")
            return {"success": False, "preflight": preflight}

        # 2. Display commitment
        self.display_execution_commitment()

        # 3. Obtain approval (simulated - in real execution this would be interactive)
        approval = self.obtain_principal_approval()

        # 4. Verify approval
        if not self.verify_approval(approval):
            print("✗ APPROVAL VERIFICATION FAILED")
            return {"success": False, "reason": "approval_verification_failed"}

        self.status = L1ExecutionStatus.AUTHORITY_VERIFIED

        # 5. Duplicate check
        dup_check = self.check_duplicate_comment()
        if dup_check.get("found"):
            print("✗ DUPLICATE COMMENT DETECTED")
            return {"success": False, "reason": "duplicate_comment", "duplicate": dup_check}

        print("✓ Zero-write preflight complete - READY FOR LIVE EXECUTION")
        print("=" * 70)

        return {
            "success": True,
            "preflight": preflight,
            "approval": {
                "approval_id": approval.approval_id,
                "approval_hash": approval.approval_hash,
                "nonce": approval.nonce
            },
            "duplicate_check": dup_check,
            "execution_id": self.execution_id
        }

    def execute_live_post(self) -> L1ExecutionResult:
        """Execute the live POST - REQUIRES FRESH PRINCIPAL APPROVAL.
        
        This method should ONLY be called after fresh Principal approval.
        It is separated from implementation for safety.
        """
        # Check for existing execution state (replay prevention)
        existing_state = self._check_existing_execution()
        if existing_state:
            return self._reconcile_on_restart(existing_state)

        self.status = L1ExecutionStatus.EXECUTING

        # Re-verify everything
        preflight = self.run_preflight_checks()
        if preflight["errors"]:
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=None,
                readback_verification=None,
                failure_reason=L1FailureReason.INSTALLATION_SCOPE_MISMATCH,
                error_message="Preflight re-verification failed",
                evidence_chain_root=None
            )

        if not self._approval or not self.verify_approval(self._approval):
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=None,
                readback_verification=None,
                failure_reason=L1FailureReason.APPROVAL_HASH_MISMATCH,
                error_message="Approval verification failed",
                evidence_chain_root=None
            )

        if self._nonce and self._nonce.consumed:
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=None,
                readback_verification=None,
                failure_reason=L1FailureReason.NONCE_ALREADY_CONSUMED,
                error_message="Nonce already consumed",
                evidence_chain_root=None
            )

        # Execute POST (handles durable state internally)
        provider_result = self.execute_comment_post()

        if not provider_result.get("success"):
            # Handle timeout requiring reconciliation
            if provider_result.get("timeout") and provider_result.get("provider_may_have_sent"):
                # Timeout after possible send - reconcile
                dup_check = self.check_duplicate_comment()
                if dup_check.get("found"):
                    readback = self.verify_readback({"response": dup_check})
                    if readback.get("all_verified"):
                        # Verified via reconciliation
                        durable = DurableExecutionState.create(
                            execution_id=self.execution_id,
                            nonce=self._nonce.nonce if self._nonce else "none",
                            approval_hash=self._approval.approval_hash if self._approval else "none",
                            body_hash=self.AUTHORIZED_BODY_HASH,
                            target_repository=self.AUTHORIZED_REPOSITORY,
                            target_pr=self.AUTHORIZED_PR_NUMBER
                        )
                        durable = durable.with_state(ExecutionState.VERIFIED)
                        self._save_durable_state(durable)
                        durable = durable.with_state(ExecutionState.CONSUMED)
                        self._save_durable_state(durable)
                        if self._nonce:
                            self._nonce = self._nonce.mark_consumed()
                        return L1ExecutionResult(
                            execution_id=self.execution_id,
                            status=L1ExecutionStatus.AUTHORITY_CONSUMED,
                            approval=self._approval,
                            nonce=self._nonce,
                            provider_response=provider_result,
                            readback_verification=readback,
                            failure_reason=None,
                            error_message="Verified via timeout reconciliation",
                            evidence_chain_root=self.evidence_chain.get_chain_root()
                        )
                    else:
                        return L1ExecutionResult(
                            execution_id=self.execution_id,
                            status=L1ExecutionStatus.FAILED,
                            approval=self._approval,
                            nonce=self._nonce,
                            provider_response=provider_result,
                            readback_verification=readback,
                            failure_reason=L1FailureReason.READBACK_VERIFICATION_FAILED,
                            error_message="Timeout reconciliation: comment exists but verification failed",
                            evidence_chain_root=None
                        )
                else:
                    # No match - unverified
                    return L1ExecutionResult(
                        execution_id=self.execution_id,
                        status=L1ExecutionStatus.FAILED,
                        approval=self._approval,
                        nonce=self._nonce,
                        provider_response=provider_result,
                        readback_verification={"verified": False, "error": "No matching comment after timeout"},
                        failure_reason=L1FailureReason.TIMEOUT_BEFORE_OUTCOME,
                        error_message="Timeout reconciliation: no matching comment found",
                        evidence_chain_root=None
                    )

            # Check for duplicate
            if "duplicate" in provider_result:
                self._readback_verification = self.verify_readback(
                    {"response": provider_result["duplicate"]}
                )
                return L1ExecutionResult(
                    execution_id=self.execution_id,
                    status=L1ExecutionStatus.FAILED,
                    approval=self._approval,
                    nonce=self._nonce,
                    provider_response=provider_result,
                    readback_verification=self._readback_verification,
                    failure_reason=L1FailureReason.DUPLICATE_COMMENT_EXISTS,
                    error_message="Duplicate comment detected",
                    evidence_chain_root=None
                )

            # Ambiguous provider result
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=provider_result,
                readback_verification=None,
                failure_reason=L1FailureReason.PROVIDER_RESPONSE_AMBIGUOUS,
                error_message=provider_result.get("error", "Unknown provider error"),
                evidence_chain_root=None
            )

        self._provider_response = provider_result
        self.status = L1ExecutionStatus.POST_COMPLETED

        # Read-back verification
        readback = self.verify_readback(provider_result)
        self._readback_verification = readback

        if not readback.get("all_verified"):
            self.status = L1ExecutionStatus.FAILED
            return L1ExecutionResult(
                execution_id=self.execution_id,
                status=L1ExecutionStatus.FAILED,
                approval=self._approval,
                nonce=self._nonce,
                provider_response=provider_result,
                readback_verification=readback,
                failure_reason=L1FailureReason.READBACK_VERIFICATION_FAILED,
                error_message="Read-back verification failed",
                evidence_chain_root=None
            )

        self.status = L1ExecutionStatus.READBACK_VERIFIED

        # Seal evidence
        self.evidence_chain.append(
            "execution_completed",
            self.execution_id,
            self.binding_id,
            self.principal_id,
            {
                "provider_response": provider_result,
                "readback_verification": readback,
                "nonce_consumed": self._nonce.consumed if self._nonce else False
            }
        )

        chain_valid = self.evidence_chain.verify_chain()
        chain_root = self.evidence_chain.get_chain_root()

        self.status = L1ExecutionStatus.EVIDENCE_SEALED
        self._nonce = self._nonce.mark_consumed() if self._nonce else None
        self.status = L1ExecutionStatus.AUTHORITY_CONSUMED

        return L1ExecutionResult(
            execution_id=self.execution_id,
            status=L1ExecutionStatus.AUTHORITY_CONSUMED,
            approval=self._approval,
            nonce=self._nonce,
            provider_response=provider_result,
            readback_verification=readback,
            failure_reason=None,
            error_message=None,
            evidence_chain_root=chain_root
        )


def run_l1_zero_write_preflight(
    authenticator: GitHubAppAuthenticator
) -> Dict[str, Any]:
    """Run L1 zero-write preflight test (NO LIVE POST)."""
    runner = L1CommentRunner(authenticator)
    return runner.run_zero_write_preflight()


def run_l1_live_execution(
    authenticator: GitHubAppAuthenticator,
    principal_approval: str  # Would be actual approval in real run
) -> L1ExecutionResult:
    """Run L1 live execution (REQUIRES FRESH PRINCIPAL APPROVAL)."""
    runner = L1CommentRunner(authenticator)
    
    # Run preflight first
    preflight = runner.run_preflight_checks()
    if preflight["errors"]:
        return L1ExecutionResult(
            execution_id=runner.execution_id,
            status=L1ExecutionStatus.FAILED,
            approval=None,
            nonce=None,
            provider_response=None,
            readback_verification=None,
            failure_reason=L1FailureReason.INSTALLATION_SCOPE_MISMATCH,
            error_message="Preflight failed",
            evidence_chain_root=None
        )
    
    # Display commitment
    runner.display_execution_commitment()
    
    # In real execution, this would wait for explicit Principal approval
    # For implementation testing, we just verify the flow
    return runner.execute_live_post()