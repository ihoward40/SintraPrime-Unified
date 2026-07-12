"""Secure monetization start-case workflow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import socket
import subprocess
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..models.monetization import StartCaseRequest, StartCaseResponse
from .artifact_schemas import validate_artifact_tree
from .case_idempotency import (
    FAILED_RETRYABLE,
    PROCESSING,
    IdempotencyConflictError,
    SQLiteIdempotencyStore,
)
from .case_security import (
    CaseSecurityError,
    VerifiedPaymentEvent,
    contained_child,
    stable_idempotency_key,
    validate_case_id,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WrittenFile:
    rel_path: str
    sha256: str


class CaseStartConflictError(ValueError):
    """Raised when a duplicate or concurrent case start is detected."""


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_repo_relative(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def receipt_key_for_file(*, case_id: str, rel_path: str, artifact_sha256: str, operation: str) -> str:
    payload = "\n".join([
        "ledger-receipt.v1",
        case_id,
        normalize_repo_relative(rel_path),
        artifact_sha256,
        operation,
    ])
    return sha256_bytes(payload.encode("utf-8"))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def tel_verify_write_text(expected_text: str, file_path: Path) -> dict[str, Any]:
    expected_hash = sha256_bytes(expected_text.encode("utf-8"))
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    read1 = file_path.read_text(encoding="utf-8")
    read2 = file_path.read_text(encoding="utf-8")
    read_back = read1 == expected_text
    return {
        "read_back": read_back,
        "multi_read_match": read1 == read2,
        "diff_match": read_back,
        "head_match": None,
        "sha256_match": sha256_bytes(read1.encode("utf-8")) == expected_hash,
    }


def write_json_verified(repo_root: Path, *, rel_path: str, obj: dict[str, Any]) -> tuple[WrittenFile, dict[str, Any]]:
    target = repo_root / rel_path
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write_text(target, text)
    verification = tel_verify_write_text(text, target)
    return WrittenFile(rel_path=rel_path.replace("\\", "/"), sha256=sha256_bytes(text.encode("utf-8"))), verification


def record_ledger_for_file(
    *,
    repo_root: Path,
    agent: str,
    operation: str,
    rel_path: str,
    verification: dict[str, Any],
    status: str,
    expected_outcome: str | None = None,
    actual_outcome: str | None = None,
) -> dict[str, Any]:
    ledger_script = repo_root / "ledger" / "record_ledger_entry.py"
    cmd = [
        "python",
        str(ledger_script),
        "--agent",
        agent,
        "--operation",
        operation,
        "--target",
        rel_path.replace("\\", "/"),
        "--status",
        status,
        "--expected_outcome",
        expected_outcome or "",
        "--actual_outcome",
        actual_outcome or "",
        "--snapshot",
        "--verification",
        json.dumps(verification, ensure_ascii=False),
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Ledger recording failed for {rel_path}: {proc.stderr or proc.stdout}")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ledger recording returned non-JSON output: {proc.stdout!r}") from exc


class CaseLock:
    def __init__(self, lock_path: Path, *, case_id: str, timeout_seconds: int = 900) -> None:
        self.lock_path = lock_path
        self.case_id = case_id
        self.timeout_seconds = timeout_seconds
        self.fd: int | None = None
        self._metadata: dict[str, Any] | None = None
        self._owns_lock = False

    def _pid_is_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _load_existing(self) -> dict[str, Any]:
        try:
            return json.loads(self.lock_path.read_text(encoding='utf-8'))
        except Exception as exc:
            raise CaseStartConflictError('malformed case lock file') from exc

    def _is_stale(self, data: dict[str, Any]) -> bool:
        created_at = data.get('created_at')
        if not isinstance(created_at, str):
            return True
        try:
            started = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(UTC)
        except ValueError:
            return True
        return (datetime.now(UTC) - started).total_seconds() > self.timeout_seconds

    def _lock_payload(self) -> dict[str, Any]:
        return {
            'schema_version': 'case_lock.v1',
            'case_id': self.case_id,
            'pid': os.getpid(),
            'hostname': socket.gethostname(),
            'created_at': utc_now_iso(),
            'process_start_marker': f"{os.getpid()}:{time.time_ns()}",
        }

    def __enter__(self) -> CaseLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                existing = self._load_existing()
                if existing.get('case_id') not in {None, self.case_id}:
                    raise CaseStartConflictError('lock belongs to a different case') from None
                if self._is_stale(existing):
                    pid = int(existing.get('pid') or -1)
                    if self._pid_is_alive(pid):
                        raise CaseStartConflictError('stale lock is still owned by an active process') from None
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        continue
                    continue
                raise CaseStartConflictError('case generation is already in progress') from None
            else:
                self._metadata = self._lock_payload()
                os.write(self.fd, json.dumps(self._metadata, indent=2, sort_keys=True).encode('utf-8'))
                self._owns_lock = True
                return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self.fd is not None:
            os.close(self.fd)
        if not self._owns_lock or self._metadata is None:
            return
        try:
            current = json.loads(self.lock_path.read_text(encoding='utf-8'))
        except Exception:
            return
        if current.get('pid') == self._metadata.get('pid') and current.get('hostname') == self._metadata.get('hostname') and current.get('case_id') == self._metadata.get('case_id'):
            with suppress(FileNotFoundError):
                self.lock_path.unlink()


class CaseStarterService:
    """Creates a new case scaffold and runs draft generation transactionally."""

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.run_root = self.repo_root / ".case_runs"
        self.idempotency_root = self.run_root / "idempotency"
        self.manifest_root = self.run_root / "manifests"
        self.lock_root = self.run_root / "locks"
        self.lock_timeout_seconds = int(os.getenv("MONETIZATION_CASE_LOCK_TIMEOUT_SECONDS", "900"))
        self.idempotency_store = SQLiteIdempotencyStore(self.idempotency_root / "events.sqlite3")

    async def start_case(
        self,
        request: StartCaseRequest,
        *,
        verified_event: VerifiedPaymentEvent,
    ) -> StartCaseResponse:
        return await asyncio.to_thread(self._start_case_sync, request, verified_event)

    def _start_case_sync(self, request: StartCaseRequest, verified_event: VerifiedPaymentEvent) -> StartCaseResponse:
        idem_key = stable_idempotency_key(verified_event.event_id)

        case_id = validate_case_id(request.case_id or verified_event.case_id)
        final_client_dir = contained_child(self.repo_root / "clients", case_id)
        final_artifact_dir = (self.repo_root / "artifacts" / "court" / case_id).resolve()
        artifacts_root = (self.repo_root / "artifacts").resolve()
        if final_artifact_dir.parent != artifacts_root / "court":
            raise CaseSecurityError("artifact path escaped artifacts/court")

        required_fields = {
            "case_type": request.case_type,
            "court": request.court,
            "jurisdiction": request.jurisdiction,
            "venue": request.venue,
        }
        missing = sorted(k for k, value in required_fields.items() if not value)
        if missing:
            raise CaseSecurityError(f"missing required case fields: {', '.join(missing)}")

        claim = self.idempotency_store.claim(
            event_id=verified_event.event_id,
            body_digest=verified_event.body_sha256,
            case_id=case_id,
            payment_session_id=verified_event.payment_session_id,
        )
        if claim.action == "replay" and claim.response_json is not None:
            return StartCaseResponse.model_validate(claim.response_json)

        manifest_path = self.manifest_root / f"{idem_key}.json"
        if final_client_dir.exists() or final_artifact_dir.exists():
            recovered = self._recover_published_run(
                manifest_path=manifest_path,
                case_id=case_id,
                verified_event=verified_event,
                final_client_dir=final_client_dir,
                final_artifact_dir=final_artifact_dir,
            )
            if recovered is not None:
                self.idempotency_store.mark_succeeded(verified_event.event_id, recovered.model_dump())
                return recovered
            raise CaseStartConflictError(f"case_id already exists: {case_id}")

        run_dir = self.run_root / "active" / f"{idem_key}-{uuid.uuid4().hex}"
        temp_repo = run_dir / "repo"
        temp_clients_root = temp_repo / "clients"
        temp_artifacts_root = temp_repo / "artifacts"
        temp_case_dir = temp_clients_root / case_id

        lock_path = self.lock_root / f"{case_id}.lock"
        try:
            with CaseLock(lock_path, case_id=case_id, timeout_seconds=self.lock_timeout_seconds):
                temp_case_dir.mkdir(parents=True, exist_ok=False)
                self.idempotency_store.set_status(verified_event.event_id, PROCESSING)
                self._failpoint("after_claim")
                response = self._generate_publish_and_ledger(
                    request=request,
                    case_id=case_id,
                    verified_event=verified_event,
                    manifest_path=manifest_path,
                    temp_repo=temp_repo,
                    temp_clients_root=temp_clients_root,
                    temp_artifacts_root=temp_artifacts_root,
                    final_client_dir=final_client_dir,
                    final_artifact_dir=final_artifact_dir,
                )
                self.idempotency_store.mark_succeeded(verified_event.event_id, response.model_dump())
                shutil.rmtree(run_dir, ignore_errors=True)
                return response
        except Exception as exc:
            failed_dir = self.run_root / "failed" / run_dir.name
            failed_dir.parent.mkdir(parents=True, exist_ok=True)
            if run_dir.exists():
                shutil.move(str(run_dir), str(failed_dir))
            failure_payload = {
                "case_id": case_id,
                "event_id_sha256": idem_key,
                "failed_at": utc_now_iso(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            atomic_write_text(failed_dir / "failure.json", json.dumps(failure_payload, indent=2) + "\n")
            if not isinstance(exc, (CaseSecurityError, IdempotencyConflictError, CaseStartConflictError)):
                self.idempotency_store.set_status(verified_event.event_id, FAILED_RETRYABLE, error_code=type(exc).__name__)
            raise


    def _failpoint(self, name: str) -> None:
        if os.getenv("CASE_START_FAIL_AT") == name:
            raise RuntimeError(f"Injected failure at {name}")

    def _write_manifest(self, manifest_path: Path, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload["updated_at"] = utc_now_iso()
        atomic_write_text(manifest_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _manifest_payload(
        self,
        *,
        stage: str,
        case_id: str,
        verified_event: VerifiedPaymentEvent,
        run_id: str,
        files: list[dict[str, Any]],
        draft_generation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": "case_run_manifest.v1",
            "stage": stage,
            "case_id": case_id,
            "event_id": verified_event.event_id,
            "body_sha256": verified_event.body_sha256,
            "payment_session_id": verified_event.payment_session_id,
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "files": files,
            "draft_generation": draft_generation,
        }

    def _collect_finalizable_files(self, temp_case_dir: Path, temp_artifact_case_dir: Path, *, case_id: str) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        for path in sorted([*temp_case_dir.glob("*.json"), *temp_artifact_case_dir.glob("*.json"), *temp_artifact_case_dir.glob("*.md")]):
            final_rel = path.relative_to(temp_case_dir.parents[1]).as_posix()
            digest = sha256_file(path)
            files.append({
                "relative_path": final_rel,
                "artifact_sha256": digest,
                "receipt_key": receipt_key_for_file(case_id=case_id, rel_path=final_rel, artifact_sha256=digest, operation="write_file"),
                "ledger_entry_id": None,
                "receipt_status": "PENDING",
                "operation": "write_file",
            })
        return files

    def _record_receipts_for_files(
        self,
        *,
        manifest_path: Path,
        manifest: dict[str, Any],
        verified_event: VerifiedPaymentEvent,
    ) -> dict[str, Any]:
        receipts: dict[str, Any] = {}
        files = manifest.setdefault("files", [])
        for item in files:
            rel_path = item["relative_path"]
            artifact_sha256 = item["artifact_sha256"]
            receipt_key = item["receipt_key"]
            if item.get("receipt_status") == "VERIFIED" and item.get("ledger_entry_id"):
                receipts[rel_path] = {"ledger_id": item["ledger_entry_id"], "reused": True}
                continue
            path = self.repo_root / rel_path
            if not path.exists() or sha256_file(path) != artifact_sha256:
                raise RuntimeError(f"published artifact does not match manifest: {rel_path}")
            verification = {
                "read_back": True,
                "multi_read_match": True,
                "diff_match": True,
                "head_match": None,
                "sha256_match": True,
                "event_id_sha256": sha256_bytes(verified_event.event_id.encode("utf-8")),
                "receipt_key": receipt_key,
                "receipt_status": "VERIFIED",
            }
            result = record_ledger_for_file(
                repo_root=self.repo_root,
                agent="monetization-start-case",
                operation=item.get("operation", "write_file"),
                rel_path=rel_path,
                verification=verification,
                status="PASS",
                expected_outcome="artifact generated, schema-validated, and published",
                actual_outcome=f"file verified on disk: {rel_path}",
            )
            item["ledger_entry_id"] = result["ledger_id"]
            item["receipt_status"] = "VERIFIED"
            receipts[rel_path] = result
            self._write_manifest(manifest_path, manifest)
        return receipts

    def _recover_published_run(
        self,
        *,
        manifest_path: Path,
        case_id: str,
        verified_event: VerifiedPaymentEvent,
        final_client_dir: Path,
        final_artifact_dir: Path,
    ) -> StartCaseResponse | None:
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("case_id") != case_id or manifest.get("event_id") != verified_event.event_id:
            return None
        stage = manifest.get("stage")
        if stage == "COMPLETED" and manifest.get("response"):
            return StartCaseResponse.model_validate(manifest["response"])
        if stage not in {"LEDGER_PENDING", "PUBLISHED"}:
            return None
        if not final_client_dir.exists() or not final_artifact_dir.exists():
            return None
        for item in manifest.get("files", []):
            path = self.repo_root / item["relative_path"]
            if not path.exists() or sha256_file(path) != item["artifact_sha256"]:
                raise RuntimeError(f"published artifact does not match manifest: {item['relative_path']}")
        receipts = self._record_receipts_for_files(
            manifest_path=manifest_path,
            manifest=manifest,
            verified_event=verified_event,
        )
        if any(item.get("receipt_status") != "VERIFIED" for item in manifest.get("files", [])):
            raise RuntimeError("manifest did not reach VERIFIED receipt state")
        response = StartCaseResponse(
            ok=True,
            case_id=case_id,
            initialization_ledgers=list(receipts.values()),
            draft_generation=manifest.get("draft_generation"),
            errors=None,
        )
        manifest["stage"] = "COMPLETED"
        manifest["response"] = response.model_dump()
        self._write_manifest(manifest_path, manifest)
        return response

    def _generate_publish_and_ledger(
        self,
        *,
        request: StartCaseRequest,
        case_id: str,
        verified_event: VerifiedPaymentEvent,
        manifest_path: Path,
        temp_repo: Path,
        temp_clients_root: Path,
        temp_artifacts_root: Path,
        final_client_dir: Path,
        final_artifact_dir: Path,
    ) -> StartCaseResponse:
        now = utc_now_iso()
        idem_key = stable_idempotency_key(verified_event.event_id)
        temp_case_dir = temp_clients_root / case_id

        case_json = {
            "schema_version": "case.v1",
            "case_id": case_id,
            "case_type": request.case_type,
            "case_summary": "Auto-created from verified payment event. Draft-only enforcement/court filings; evidence verification pending.",
            "court": request.court,
            "creditor": request.creditor_name,
            "jurisdiction": request.jurisdiction,
            "matter_type": request.matter_type,
            "opened_date": now,
            "venue": request.venue,
        }
        evidence_manifest = {
            "schema_version": "evidence_manifest.v1",
            "verification_summary": {"verified": 0, "partial": 0, "missing": 1},
            "evidence_items": [
                {
                    "evidence_id": "delivery_proof_missing",
                    "description": "Proof of delivery / delivery tracking evidence (pending)",
                    "status": "missing",
                }
            ],
        }
        violation_candidates = {"schema_version": "violation_candidates.v1", "violation_candidates": []}
        readiness_report = {
            "schema_version": "readiness_report.v1",
            "status": "BLOCKED",
            "overall_readiness_score": 0,
            "blocked_reasons": ["Evidence verification pending"],
        }

        for name, obj in [
            ("case.json", case_json),
            ("evidence_manifest.json", evidence_manifest),
            ("violation_candidates.json", violation_candidates),
            ("readiness_report.json", readiness_report),
        ]:
            write_json_verified(temp_repo, rel_path=f"clients/{case_id}/{name}", obj=obj)

        validate_artifact_tree(temp_case_dir)

        draft_cmd = [
            "python",
            str(self.repo_root / "orchestration" / "enforcement" / "court_filing_draft_center.py"),
            "--only-case",
            case_id,
            "--clients-root",
            str(temp_clients_root),
            "--artifacts-root",
            str(temp_artifacts_root),
            "--skip-ledger",
            "--dashboard-mode",
            "run-scoped",
        ]
        proc = subprocess.run(
            draft_cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if proc.returncode != 0:
            stdout_tail = "\n".join(proc.stdout.splitlines()[-30:]) if proc.stdout else ""
            stderr_tail = "\n".join(proc.stderr.splitlines()[-30:]) if proc.stderr else ""
            raise RuntimeError(
                f"Draft generation failed for {case_id}.\nstdout_tail={stdout_tail}\nstderr_tail={stderr_tail}"
            )

        self._failpoint("after_generation")
        temp_artifact_case_dir = temp_artifacts_root / "court" / case_id
        validate_artifact_tree(temp_artifact_case_dir)
        self._failpoint("after_schema_validation")
        parsed = extract_last_json(proc.stdout or "")
        if parsed.get("generated_cases") != 1:
            raise RuntimeError(f"Draft generator did not produce exactly one case: {parsed}")

        files = self._collect_finalizable_files(temp_case_dir, temp_artifact_case_dir, case_id=case_id)
        self._failpoint("after_hash_creation")
        draft_generation = {
            "draft_generator": "court_filing_draft_center.py",
            "result": parsed,
        }
        manifest = self._manifest_payload(
            stage="LEDGER_PENDING",
            case_id=case_id,
            verified_event=verified_event,
            run_id=idem_key,
            files=files,
            draft_generation=draft_generation,
        )
        self._failpoint("before_ledger_prepare")
        self._write_manifest(manifest_path, manifest)
        self._failpoint("after_ledger_prepare")

        if final_client_dir.exists() or final_artifact_dir.exists():
            raise CaseStartConflictError(f"case_id already exists: {case_id}")
        final_client_dir.parent.mkdir(parents=True, exist_ok=True)
        final_artifact_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_case_dir.rename(final_client_dir)
        temp_artifact_case_dir.rename(final_artifact_dir)
        manifest["stage"] = "PUBLISHED"
        self._write_manifest(manifest_path, manifest)
        self._failpoint("after_final_rename")

        receipts = self._record_receipts_for_files(
            manifest_path=manifest_path,
            manifest=manifest,
            verified_event=verified_event,
        )
        self._failpoint("before_idempotency_success")
        response = StartCaseResponse(
            ok=True,
            case_id=case_id,
            initialization_ledgers=list(receipts.values()),
            draft_generation=draft_generation,
            errors=None,
        )
        manifest["stage"] = "COMPLETED"
        manifest["response"] = response.model_dump()
        self._write_manifest(manifest_path, manifest)
        return response


def extract_last_json(stdout_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    matches: list[dict[str, Any]] = []
    for index, char in enumerate(stdout_text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stdout_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            matches.append(obj)
    if not matches:
        raise ValueError("No valid JSON found in generator stdout")
    return matches[-1]


case_starter_service = CaseStarterService()
