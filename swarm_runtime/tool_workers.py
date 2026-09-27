"""Tool-first deterministic workers.

Many swarm tasks (code search, AST analysis, schema inventory) do NOT require
LLM inference. These workers use deterministic Python tooling and produce
structured artifacts. The model should synthesize output AFTER extraction.

Architecture: TOOLS → STRUCTURED FACTS → MODEL REASONING (optional)

Worker classes:
  CodeSearchWorker     — grep/ripgrep-based code search
  ASTAnalysisWorker    — Python AST parsing for model definitions
  DatabaseSchemaWorker — SQL schema file parsing
  TestRunnerWorker     — pytest execution and result capture
  GitDiffWorker        — git diff analysis
  StaticAnalysisWorker — ruff/bandit/static analysis
  ModelReasoningWorker — LLM-based reasoning (with provider failover)
  BreakerWorker        — independent verification/disproof
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .artifact_store import ArtifactStore
from .worker import WorkerState, WorkerStatus


class BaseWorker:
    """Base class for all tool-first workers."""

    def __init__(self, state: WorkerState, store: ArtifactStore, repo_path: str) -> None:
        self.state = state
        self.store = store
        self.repo_path = Path(repo_path)
        self.findings: dict[str, Any] = {}
        self.evidence: list[dict] = []

    def run(self) -> int:
        """Execute the worker. Returns exit code (0 = success)."""
        try:
            self.state.status = WorkerStatus.RUNNING
            self.state.start_time = time.time()
            self.state.touch_heartbeat()
            self.store.write_status(self.state.worker_id, self.state)
            self.store.write_heartbeat(self.state.worker_id, self.state)
            self.store.record_event(__import__('swarm_runtime.worker', fromlist=['SwarmEvent']).SwarmEvent(
                timestamp=time.time(), swarm_id=self.state.swarm_id,
                worker_id=self.state.worker_id, event="WORKER_STARTED",
            ))

            result = self.execute()

            if result == 0:
                self.state.status = WorkerStatus.COMPLETED
            else:
                self.state.status = WorkerStatus.FAILED
            self.state.end_time = time.time()
            self.state.exit_code = result
            self.store.write_status(self.state.worker_id, self.state)
            if result == 0:
                self.store.write_findings(
                    self.state.worker_id, self.findings, self.state, self.evidence
                )
                self.store.record_event(__import__('swarm_runtime.worker', fromlist=['SwarmEvent']).SwarmEvent(
                    timestamp=time.time(), swarm_id=self.state.swarm_id,
                    worker_id=self.state.worker_id, event="WORKER_COMPLETED",
                ))
            else:
                self.store.record_event(__import__('swarm_runtime.worker', fromlist=['SwarmEvent']).SwarmEvent(
                    timestamp=time.time(), swarm_id=self.state.swarm_id,
                    worker_id=self.state.worker_id, event="WORKER_FAILED",
                    details={"exit_code": result},
                ))
            return result
        except Exception as e:
            self.state.errors.append(str(e))
            self.state.status = WorkerStatus.FAILED
            self.state.end_time = time.time()
            self.state.exit_code = 1
            self.store.write_status(self.state.worker_id, self.state)
            self.store.record_event(__import__('swarm_runtime.worker', fromlist=['SwarmEvent']).SwarmEvent(
                timestamp=time.time(), swarm_id=self.state.swarm_id,
                worker_id=self.state.worker_id, event="WORKER_FAILED",
                details={"error": str(e)},
            ))
            return 1

    def execute(self) -> int:
        """Override in subclasses."""
        raise NotImplementedError

    def _heartbeat(self, phase: str, processed: int = 0, pending: int = 0) -> None:
        """Update heartbeat and progress."""
        self.state.phase = phase
        self.state.files_processed = processed
        self.state.files_pending = pending
        self.state.touch_heartbeat()
        self.state.last_provider_progress = time.time()
        self.store.write_heartbeat(self.state.worker_id, self.state)

    def _evidence(self, source: str, data: dict) -> None:
        """Record evidence for findings."""
        self.evidence.append({"source": source, "data": data, "timestamp": time.time()})


class CodeSearchWorker(BaseWorker):
    """Deterministic code search using ripgrep/grep.

    Task params:
      pattern: regex pattern to search for
      path: directory to search in (relative to repo)
      file_glob: file pattern filter (e.g. "*.py")
      context_lines: number of context lines (default 0)
    """

    def execute(self) -> int:
        pattern = self.state.task.get("pattern", "")
        search_path = self.state.task.get("path", ".")
        file_glob = self.state.task.get("file_glob", "*.py")
        context_lines = self.state.task.get("context_lines", 0)

        full_path = self.repo_path / search_path
        matches: list[dict] = []

        # Walk files matching the glob
        files = list(full_path.rglob(file_glob))
        total = len(files)
        self._heartbeat("scanning files", 0, total)

        for i, fpath in enumerate(files):
            # Skip __pycache__, .git, .venv
            if any(part in {"__pycache__", ".git", ".venv", "node_modules", ".swarm"}
                   for part in fpath.parts):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                for line_no, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        rel_path = str(fpath.relative_to(self.repo_path)).replace("\\", "/")
                        match = {
                            "file": rel_path,
                            "line": line_no,
                            "content": line.strip(),
                        }
                        if context_lines > 0:
                            lines = content.splitlines()
                            start = max(0, line_no - 1 - context_lines)
                            end = min(len(lines), line_no + context_lines)
                            match["context"] = "\n".join(lines[start:end])
                        matches.append(match)
            except Exception:
                pass

            if (i + 1) % 10 == 0:
                self._heartbeat(f"scanning files ({i+1}/{total})", i + 1, total)

        self.findings = {
            "pattern": pattern,
            "search_path": search_path,
            "file_glob": file_glob,
            "total_files_scanned": total,
            "match_count": len(matches),
            "matches": matches,
        }
        self._evidence("ripgrep_scan", {"files": total, "matches": len(matches)})
        self._heartbeat("completed", total, 0)
        return 0


class ASTAnalysisWorker(BaseWorker):
    """Python AST analysis for SQLAlchemy model definitions.

    Task params:
      path: directory to analyze (relative to repo)
      target: what to extract — "mapped_columns", "foreign_keys", "class_defs"
    """

    def execute(self) -> int:
        search_path = self.repo_path / self.state.task.get("path", "portal/models")
        target = self.state.task.get("target", "mapped_columns")

        files = list(search_path.rglob("*.py"))
        total = len(files)
        self._heartbeat("parsing AST", 0, total)

        all_findings: list[dict] = []
        for i, fpath in enumerate(files):
            if any(part in {"__pycache__", ".git", ".venv"} for part in fpath.parts):
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
                tree = ast.parse(content)
                rel_path = str(fpath.relative_to(self.repo_path)).replace("\\", "/")

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        for child in ast.walk(node):
                            if isinstance(child, ast.AnnAssign) and hasattr(child, 'target'):
                                attr_name = ""
                                if isinstance(child.target, ast.Name):
                                    attr_name = child.target.id
                                elif isinstance(child.target, ast.Attribute):
                                    attr_name = child.target.attr

                                if target == "mapped_columns" and attr_name:
                                    # Look for mapped_column calls
                                    if isinstance(child.value, ast.Call):
                                        call_str = ast.unparse(child.value) if hasattr(ast, 'unparse') else ""
                                        if "mapped_column" in call_str or "Column" in call_str:
                                            annotation = ""
                                            if child.annotation:
                                                annotation = ast.unparse(child.annotation) if hasattr(ast, 'unparse') else ""
                                            all_findings.append({
                                                "file": rel_path,
                                                "class": class_name,
                                                "attribute": attr_name,
                                                "annotation": annotation,
                                                "call": call_str[:200],
                                            })
                                elif target == "foreign_keys":
                                    if isinstance(child.value, ast.Call):
                                        call_str = ast.unparse(child.value) if hasattr(ast, 'unparse') else ""
                                        if "ForeignKey" in call_str:
                                            all_findings.append({
                                                "file": rel_path,
                                                "class": class_name,
                                                "attribute": attr_name,
                                                "call": call_str[:200],
                                            })
                                elif target == "class_defs":
                                    all_findings.append({
                                        "file": rel_path,
                                        "class": class_name,
                                        "bases": [ast.unparse(b) if hasattr(ast, 'unparse') else "" for b in node.bases],
                                    })
            except Exception:
                pass

            if (i + 1) % 5 == 0:
                self._heartbeat(f"parsing AST ({i+1}/{total})", i + 1, total)

        self.findings = {
            "target": target,
            "search_path": str(search_path.relative_to(self.repo_path)).replace("\\", "/"),
            "total_files": total,
            "finding_count": len(all_findings),
            "findings": all_findings,
        }
        self._evidence("ast_analysis", {"files": total, "findings": len(all_findings)})
        self._heartbeat("completed", total, 0)
        return 0


class DatabaseSchemaWorker(BaseWorker):
    """SQL schema file parser.

    Task params:
      path: directory with .sql files (relative to repo)
      extract: what to extract — "identity_columns", "fk_constraints", "rls_policies", "all"
    """

    def execute(self) -> int:
        search_path = self.repo_path / self.state.task.get("path", "portal/migrations")
        extract = self.state.task.get("extract", "all")

        sql_files = list(search_path.rglob("*.sql"))
        total = len(sql_files)
        self._heartbeat("parsing SQL", 0, total)

        identity_columns: list[dict] = []
        fk_constraints: list[dict] = []
        rls_policies: list[dict] = []
        table_defs: list[dict] = []

        create_table_re = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', re.I)
        column_re = re.compile(r'^\s*(\w+)\s+(UUID|VARCHAR\(\d+\)|TEXT|JSONB|INTEGER|BIGINT|BOOLEAN|TIMESTAMP|TEXT\[\])', re.I)
        fk_re = re.compile(r'REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)', re.I)
        rls_enable_re = re.compile(r'ENABLE\s+ROW\s+LEVEL\s+SECURITY\s+ON\s+(\w+)', re.I)
        policy_re = re.compile(r'CREATE\s+POLICY\s+(\w+)\s+ON\s+(\w+)', re.I)
        cast_re = re.compile(r'::uuid|::varchar|CAST\s*\(.*?AS\s+(UUID|VARCHAR)\)', re.I)

        for i, fpath in enumerate(sql_files):
            if any(part in {".git", ".venv"} for part in fpath.parts):
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
                rel_path = str(fpath.relative_to(self.repo_path)).replace("\\", "/")

                # Find CREATE TABLE
                for m in create_table_re.finditer(content):
                    table_defs.append({"file": rel_path, "table": m.group(1)})

                # Find identity columns (id, tenant_id, user_id, etc.)
                for line_no, line in enumerate(content.splitlines(), 1):
                    cm = column_re.match(line)
                    if cm:
                        col_name = cm.group(1)
                        col_type = cm.group(2)
                        if col_name in ("id", "tenant_id", "user_id", "principal_id",
                                        "matter_id", "case_id", "client_id", "document_id",
                                        "agent_id", "service_id", "run_id", "mission_id",
                                        "approval_id"):
                            identity_columns.append({
                                "file": rel_path, "line": line_no,
                                "table": "",  # would need context tracking
                                "column": col_name, "type": col_type.upper(),
                            })

                    # FK constraints
                    for fkm in fk_re.finditer(line):
                        fk_constraints.append({
                            "file": rel_path, "line": line_no,
                            "references_table": fkm.group(1),
                            "references_column": fkm.group(2),
                            "line_content": line.strip()[:200],
                        })

                    # RLS
                    if rls_enable_re.search(line):
                        rls_policies.append({
                            "file": rel_path, "line": line_no,
                            "type": "ENABLE_RLS", "table": rls_enable_re.search(line).group(1),
                        })
                    pm = policy_re.search(line)
                    if pm:
                        casts = cast_re.findall(line)
                        rls_policies.append({
                            "file": rel_path, "line": line_no,
                            "type": "POLICY", "policy_name": pm.group(1),
                            "table": pm.group(2),
                            "casts": casts,
                            "expression": line.strip()[:200],
                        })
            except Exception:
                pass

            self._heartbeat(f"parsing SQL ({i+1}/{total})", i + 1, total)

        self.findings = {
            "extract": extract,
            "sql_files_scanned": total,
            "identity_columns": identity_columns if extract in ("identity_columns", "all") else [],
            "fk_constraints": fk_constraints if extract in ("fk_constraints", "all") else [],
            "rls_policies": rls_policies if extract in ("rls_policies", "all") else [],
            "table_count": len(table_defs),
            "tables": table_defs if extract in ("all",) else [],
        }
        self._evidence("sql_parse", {"files": total})
        self._heartbeat("completed", total, 0)
        return 0


class TestRunnerWorker(BaseWorker):
    """Runs pytest and captures results.

    Task params:
      test_path: pytest test path (e.g. "portal/tests/test_auth.py")
      python_exe: python executable path
    """

    def execute(self) -> int:
        test_path = self.state.task.get("test_path", "")
        import sys as _sys
        python_exe = self.state.task.get("python_exe", _sys.executable if _sys else "python")
        venv = self.state.task.get("venv", "")

        cmd = []
        if venv:
            cmd.append(str(Path(venv) / "Scripts" / "python"))
        else:
            cmd.append(python_exe)
        cmd.extend(["-m", "pytest", test_path, "--tb=short", "-q", "--json-report",
                     f"--json-report-file={self.store.worker_dir(self.state.worker_id) / 'pytest_report.json'}"])

        self._heartbeat("running pytest", 0, 1)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(self.repo_path),
        )

        self.findings = {
            "test_path": test_path,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:5000],
            "stderr": proc.stderr[:2000],
        }
        self._evidence("pytest", {"exit_code": proc.returncode})
        self._heartbeat("completed", 1, 0)
        return 0 if proc.returncode == 0 else 1


class GitDiffWorker(BaseWorker):
    """Git diff analysis.

    Task params:
      base: base commit SHA
      head: head commit SHA (default: HEAD)
    """

    def execute(self) -> int:
        base = self.state.task.get("base", "")
        head = self.state.task.get("head", "HEAD")

        self._heartbeat("computing git diff", 0, 1)
        proc = subprocess.run(
            ["git", "diff", "--stat", base, head],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.repo_path),
        )
        stat_output = proc.stdout

        proc2 = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.repo_path),
        )
        changed_files = [f for f in proc2.stdout.strip().split("\n") if f]

        self.findings = {
            "base": base, "head": head,
            "changed_files": changed_files,
            "changed_file_count": len(changed_files),
            "diff_stat": stat_output,
        }
        self._evidence("git_diff", {"files": len(changed_files)})
        self._heartbeat("completed", 1, 0)
        return 0


class StaticAnalysisWorker(BaseWorker):
    """Runs static analysis tools (ruff, bandit).

    Task params:
      tool: "ruff" or "bandit"
      path: path to analyze
    """

    def execute(self) -> int:
        tool = self.state.task.get("tool", "ruff")
        path = self.state.task.get("path", "portal/")

        cmd = [tool, "check", path, "--output-format=json"]
        self._heartbeat(f"running {tool}", 0, 1)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            cwd=str(self.repo_path),
        )

        findings = []
        with contextlib.suppress(json.JSONDecodeError):
            findings = json.loads(proc.stdout) if proc.stdout else []

        self.findings = {
            "tool": tool, "path": path,
            "exit_code": proc.returncode,
            "finding_count": len(findings),
            "findings": findings[:100],
        }
        self._evidence(tool, {"findings": len(findings)})
        self._heartbeat("completed", 1, 0)
        return 0


class _HealthTrackedInferenceProvider:
    """Wraps a governed provider with swarm health persistence."""

    def __init__(
        self,
        provider: Any,
        router: Any,
        store: Any | None,
        timeout_seconds: int | None = None,
    ) -> None:
        self._provider = provider
        self._router = router
        self._store = store
        self._timeout_seconds = timeout_seconds
        caps = provider.capabilities()
        if self._router.get_health(caps.provider) is None:
            self._router.register_provider(caps.provider, model=caps.model)

    def capabilities(self) -> Any:
        return self._provider.capabilities()

    def estimate_cost(self, request: Any) -> Any:
        return self._provider.estimate_cost(request)

    def current_limits(self) -> Any:
        return self._provider.current_limits()

    def health(self) -> Any:
        from governed_inference.contracts import ProviderHealth as GovernedProviderHealth

        base = self._provider.health()
        tracked = self._router.get_health(self.capabilities().provider)
        if tracked is None:
            return base
        available = tracked.is_available()
        reason = base.reason
        if reason is None and not available:
            reason = f"swarm_{tracked.state.value}"
        return GovernedProviderHealth(
            reachable=base.reachable,
            healthy=base.healthy and available,
            circuit_open=(not available) or base.circuit_open,
            reason=reason,
            checked_at=base.checked_at,
        )

    def invoke(self, request: Any) -> Any:
        return self._invoke_with_health("invoke", request)

    def invoke_stream(self, request: Any) -> Any:
        return self._invoke_with_health("invoke_stream", request)

    def _invoke_with_health(self, method: str, request: Any) -> Any:
        from governed_inference.contracts import InferenceError, ProviderErrorKind

        provider_name = self.capabilities().provider
        started = time.perf_counter()
        try:
            result = getattr(self._provider, method)(request)
            if method == "invoke_stream":
                if hasattr(result, "__aiter__"):
                    return self._wrap_async_stream_with_health(provider_name, result, started)
                if hasattr(result, "__iter__"):
                    return self._wrap_stream_with_health(provider_name, result, started)
        except InferenceError as exc:
            if exc.kind in {
                ProviderErrorKind.TIMEOUT_FIRST_BYTE,
                ProviderErrorKind.TIMEOUT_PROGRESS,
            }:
                self._router.mark_timeout(provider_name)
            else:
                self._router.mark_failure(provider_name)
            self._persist()
            raise
        except asyncio.CancelledError:
            self._persist()
            raise
        except Exception:
            self._router.mark_failure(provider_name)
            self._persist()
            raise
        latency_seconds = max(time.perf_counter() - started, 0.001)
        self._router.mark_success(provider_name, response_time=latency_seconds)
        self._persist()
        return result

    def _wrap_stream_with_health(
        self,
        provider_name: str,
        stream_result: Any,
        started: float,
    ) -> Any:
        from governed_inference.contracts import InferenceError, ProviderErrorKind

        def _iterator() -> Any:
            try:
                yield from stream_result
            except InferenceError as exc:
                if exc.kind in {
                    ProviderErrorKind.TIMEOUT_FIRST_BYTE,
                    ProviderErrorKind.TIMEOUT_PROGRESS,
                }:
                    self._router.mark_timeout(provider_name)
                else:
                    self._router.mark_failure(provider_name)
                self._persist()
                raise
            except asyncio.CancelledError:
                self._persist()
                raise
            except Exception:
                self._router.mark_failure(provider_name)
                self._persist()
                raise
            self._router.mark_success(
                provider_name,
                response_time=max(time.perf_counter() - started, 0.001),
            )
            self._persist()

        return _iterator()

    def _wrap_async_stream_with_health(
        self,
        provider_name: str,
        stream_result: Any,
        started: float,
    ) -> Any:
        from governed_inference.contracts import InferenceError, ProviderErrorKind

        async def _iterator() -> Any:
            try:
                async for item in stream_result:
                    yield item
            except InferenceError as exc:
                if exc.kind in {
                    ProviderErrorKind.TIMEOUT_FIRST_BYTE,
                    ProviderErrorKind.TIMEOUT_PROGRESS,
                }:
                    self._router.mark_timeout(provider_name)
                else:
                    self._router.mark_failure(provider_name)
                self._persist()
                raise
            except asyncio.CancelledError:
                self._persist()
                raise
            except Exception:
                self._router.mark_failure(provider_name)
                self._persist()
                raise
            self._router.mark_success(
                provider_name,
                response_time=max(time.perf_counter() - started, 0.001),
            )
            self._persist()

        return _iterator()

    def _persist(self) -> None:
        if self._store is not None:
            self._store.save(self._router.health_snapshot())


class ModelReasoningWorker(BaseWorker):
    """LLM-based reasoning worker with provider failover.

    This worker is used when LLM inference IS needed. It uses the provider router
    for timeout/failover. For deterministic tasks, use tool-first workers instead.

    Task params:
      prompt: the reasoning prompt
      system_prompt: optional system prompt
    """

    def execute(self) -> int:
        """Execute one governed inference request in the worker subprocess."""
        prompt = self.state.task.get("prompt", "")
        task_id = self.state.task.get("task_id", self.state.worker_id)
        self._heartbeat("model reasoning", 0, 1)

        from governed_inference.contracts import (
            InferencePolicy,
            PerRequestPolicy,
        )
        from governed_inference.router import GovernedInferenceRouter
        from swarm_runtime.health_persistence import ProviderHealthStore
        from swarm_runtime.provider_router import ProviderRouter

        from .inference_adapter import (
            SwarmInferenceAdapter,
            WorkerInferenceRequest,
        )

        health_router = ProviderRouter()
        health_store = ProviderHealthStore(
            self.state.task.get("provider_health_store_dir") or self.store.swarm_dir()
        )
        health_store.apply_to_router(health_router)
        provider_timeout_seconds = self._provider_timeout_seconds()
        providers = self._build_governed_providers(
            provider_timeout_seconds=provider_timeout_seconds,
            health_router=health_router,
            health_store=health_store,
        )
        if not providers:
            self.state.errors.append("no governed providers configured")
            return 1
        priority_source = self.state.task.get("governed_provider_priority") or {}
        policy = InferencePolicy(
            provider_priority={str(key): int(value) for key, value in priority_source.items()},
            per_request=PerRequestPolicy(
                max_input_tokens=int(self.state.task.get("max_input_tokens", 12000)),
                max_output_tokens=int(self.state.task.get("max_output_tokens", 2000)),
                max_attempts=int(self.state.task.get("max_attempts", 3)),
                max_attempts_per_provider=int(self.state.task.get("max_attempts_per_provider", 1)),
                timeout_seconds=provider_timeout_seconds,
            ),
        )
        router = GovernedInferenceRouter(providers, policy=policy)
        adapter = SwarmInferenceAdapter(router)
        result = adapter.invoke(WorkerInferenceRequest(
            worker_id=self.state.worker_id,
            task_id=task_id,
            task_type=self.state.task.get("task_type", "summarization"),
            capability=self.state.task.get("capability", "summarization"),
            messages=[{"role": "user", "content": prompt}],
            tenant_id=self.state.task.get("tenant_id", ""),
            principal_id=self.state.task.get("principal_id", ""),
            mission_id=self.state.task.get("mission_id", ""),
            max_input_tokens=self.state.task.get("max_input_tokens", 12000),
            max_output_tokens=self.state.task.get("max_output_tokens", 2000),
        ))
        if result.error:
            self.state.errors.append(result.error)
            return 1
        self.findings = {
            "prompt": prompt[:500],
            "result": result.content,
            "provider": result.provider,
            "model": result.model,
            "attempts": result.attempts,
            "failover_observed": result.failover_observed,
            "provider_attempts": adapter.get_attempt_log(),
            "providers_attempted": [item["provider"] for item in adapter.get_attempt_log()],
            "provider_attempt_count": len(adapter.get_attempt_log()),
            "failover_count": max(0, len(dict.fromkeys(item["provider"] for item in adapter.get_attempt_log())) - 1),
            "final_provider": result.provider,
            "final_model": result.model,
            "attempt_log": adapter.get_attempt_log(),
            "worker_timeout_seconds": self._worker_timeout_seconds(),
            "configured_provider_timeout_seconds": provider_timeout_seconds,
            "provider_health": health_router.all_health(),
            "provider_health_store_path": str(Path(health_store.store_dir) / "provider_health.json"),
        }
        self._heartbeat("completed", 1, 0)
        return 0

    def _worker_timeout_seconds(self) -> int:
        raw = self.state.task.get("worker_timeout_seconds", 120)
        return max(2, int(raw))

    def _provider_timeout_seconds(self) -> int:
        worker_timeout = self._worker_timeout_seconds()
        requested = int(self.state.task.get("timeout_seconds", 60))
        return max(1, min(requested, worker_timeout - 1))

    def _build_governed_providers(
        self,
        *,
        provider_timeout_seconds: int,
        health_router: Any,
        health_store: Any,
    ) -> list[Any]:
        if "governed_providers" in self.state.task:
            configs = list(self.state.task.get("governed_providers") or [])
        else:
            provider_fixtures = self.state.task.get("provider_fixtures")
            if provider_fixtures:
                configs = [
                    {
                        "kind": "mock",
                        "name": fixture.get("name", "deterministic-local"),
                        "model": fixture.get("model", "deterministic"),
                        "quality": fixture.get("quality", "standard"),
                        "route_tier": fixture.get("route_tier", "LOCAL_PRIVATE"),
                        "capabilities": fixture.get(
                            "capabilities",
                            ("summarization", "classification", "extraction"),
                        ),
                        "fail_times": fixture.get("fail_times", 0),
                        "error_kind": fixture.get("error_kind", "transient"),
                        "estimated_cost_usd": fixture.get("estimated_cost_usd", 0),
                        "cloud": fixture.get("cloud", False),
                        "paid": fixture.get("paid", False),
                    }
                    for fixture in provider_fixtures
                ]
            else:
                configs = self._default_governed_provider_configs()
        return [
            _HealthTrackedInferenceProvider(
                self._build_governed_provider(config, provider_timeout_seconds),
                health_router,
                health_store,
                provider_timeout_seconds,
            )
            for config in configs
        ]

    def _default_governed_provider_configs(self) -> list[dict[str, Any]]:
        configs: list[dict[str, Any]] = [
            {
                "kind": "ollama",
                "base_url": self.state.task.get("ollama_base_url")
                or os.getenv("OLLAMA_BASE_URL")
                or "http://localhost:11434",
                "model": self.state.task.get("ollama_model", "llama3"),
            }
        ]
        if not bool(self.state.task.get("allow_hosted_providers", False)):
            return configs
        if os.getenv("DEEPSEEK_API_KEY"):
            configs.append(
                {
                    "kind": "deepseek",
                    "api_key": os.getenv("DEEPSEEK_API_KEY"),
                    "model": self.state.task.get("deepseek_model", "deepseek-chat"),
                }
            )
        if os.getenv("OPENAI_API_KEY"):
            configs.append(
                {
                    "kind": "openai",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": self.state.task.get("openai_model", "gpt-4o-mini"),
                }
            )
        if os.getenv("ANTHROPIC_API_KEY"):
            configs.append(
                {
                    "kind": "anthropic",
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "model": self.state.task.get(
                        "anthropic_model",
                        "claude-3-5-sonnet-20241022",
                    ),
                }
            )
        return configs

    def _build_governed_provider(
        self,
        config: dict[str, Any],
        provider_timeout_seconds: int,
    ) -> Any:
        from governed_inference.adapters import (
            AnthropicProvider,
            DeepSeekProvider,
            OllamaProvider,
            OpenAIProvider,
        )
        from governed_inference.contracts import ProviderErrorKind, QualityFloor, RouteTier
        from governed_inference.providers import MockProvider

        kind = str(config.get("kind", "mock")).strip().lower()
        api_key = config.get("api_key")

        def _with_metadata_overrides(provider: Any) -> Any:
            if "cloud" in config:
                provider.cloud = bool(config.get("cloud"))
            if "paid" in config:
                provider.paid = bool(config.get("paid"))
            return provider

        if kind == "mock":
            capabilities = tuple(
                config.get(
                    "capabilities",
                    ("summarization", "classification", "extraction", "drafting", "coding", "reasoning"),
                )
            )
            return MockProvider(
                name=str(config.get("name", "deterministic-local")),
                model=str(config.get("model", "deterministic")),
                route_tier=RouteTier(str(config.get("route_tier", RouteTier.LOCAL_PRIVATE.value))),
                capabilities=capabilities,
                fail_times=int(config.get("fail_times", 0)),
                error_kind=ProviderErrorKind(str(config.get("error_kind", ProviderErrorKind.TRANSIENT.value))),
                estimated_cost_usd=config.get("estimated_cost_usd", 0),
                quality=QualityFloor(str(config.get("quality", QualityFloor.STANDARD.value))),
                cloud=bool(config.get("cloud", False)),
                paid=bool(config.get("paid", False)),
            )
        if kind == "ollama":
            return _with_metadata_overrides(OllamaProvider(
                base_url=str(config.get("base_url", "http://localhost:11434")),
                model=str(config.get("model", "llama3")),
                timeout_seconds=provider_timeout_seconds,
                quality=QualityFloor(str(config.get("quality", QualityFloor.STANDARD.value))),
            ))
        if kind == "deepseek":
            if not api_key:
                raise ValueError("deepseek governed provider requires api_key")
            return _with_metadata_overrides(DeepSeekProvider(
                api_key=api_key,
                model=str(config.get("model", "deepseek-chat")),
                timeout_seconds=provider_timeout_seconds,
                quality=QualityFloor(str(config.get("quality", QualityFloor.STANDARD.value))),
            ))
        if kind == "openai":
            if not api_key:
                raise ValueError("openai governed provider requires api_key")
            return _with_metadata_overrides(OpenAIProvider(
                api_key=api_key,
                model=str(config.get("model", "gpt-4o-mini")),
                timeout_seconds=provider_timeout_seconds,
                quality=QualityFloor(str(config.get("quality", QualityFloor.STANDARD.value))),
                estimated_cost_usd=config.get("estimated_cost_usd"),
                pricing_known=bool(config.get("pricing_known", False)),
            ))
        if kind == "anthropic":
            if not api_key:
                raise ValueError("anthropic governed provider requires api_key")
            return _with_metadata_overrides(AnthropicProvider(
                api_key=api_key,
                model=str(config.get("model", "claude-3-5-sonnet-20241022")),
                timeout_seconds=provider_timeout_seconds,
                quality=QualityFloor(str(config.get("quality", QualityFloor.HIGH.value))),
                estimated_cost_usd=config.get("estimated_cost_usd"),
                pricing_known=bool(config.get("pricing_known", False)),
            ))
        raise ValueError(f"unsupported governed provider kind: {kind}")


class BreakerWorker(BaseWorker):
    """Independent verification/disproof worker.

    Task params:
      target_artifact: path to the artifact to verify
      acceptance_criteria: list of criteria to check
    """

    def execute(self) -> int:
        target_path = self.state.task.get("target_artifact", "")
        criteria = self.state.task.get("acceptance_criteria", [])

        self._heartbeat("verifying artifact", 0, len(criteria))

        # Read the target artifact
        full_target = self.store.swarm_dir() / target_path if not os.path.isabs(target_path) else Path(target_path)
        if not full_target.exists():
            self.findings = {"valid": False, "reason": "target artifact not found"}
            return 1

        target_data = json.loads(full_target.read_text(encoding="utf-8"))
        results: list[dict] = []

        for i, criterion in enumerate(criteria):
            check = self._check_criterion(target_data, criterion)
            results.append(check)
            self._heartbeat(f"verifying ({i+1}/{len(criteria)})", i + 1, len(criteria))

        all_pass = all(r.get("pass") for r in results)
        self.findings = {
            "target_artifact": str(target_path),
            "all_criteria_pass": all_pass,
            "criteria_results": results,
        }
        self._evidence("breaker_verification", {"all_pass": all_pass})
        return 0 if all_pass else 1

    def _check_criterion(self, data: dict, criterion: dict) -> dict:
        """Check a single criterion against the artifact data."""
        field = criterion.get("field", "")
        expected = criterion.get("expected")
        operator = criterion.get("operator", "equals")

        actual = data
        for part in field.split("."):
            if isinstance(actual, dict):
                actual = actual.get(part)
            else:
                actual = None
                break

        if operator == "equals":
            passed = actual == expected
        elif operator == "exists":
            passed = actual is not None
        elif operator == "not_empty":
            passed = actual is not None and len(actual) > 0 if hasattr(actual, '__len__') else actual is not None
        elif operator == "greater_than":
            passed = actual is not None and actual > expected
        else:
            passed = False

        return {
            "field": field,
            "expected": expected,
            "actual": actual,
            "operator": operator,
            "pass": passed,
        }


class FailoverTestWorker(BaseWorker):
    """Tests provider failover — simulates a stalled provider then switches.

    Task params:
      stall_duration: how long to simulate provider stall (seconds)
      stall_phase: when to stall ("before_work" or "during_work")
    """

    def execute(self) -> int:
        stall_duration = self.state.task.get("stall_duration", 5)
        stall_phase = self.state.task.get("stall_phase", "before_work")

        # Phase 1: simulate provider stall
        if stall_phase == "before_work":
            self._heartbeat("simulating_provider_stall", 0, 1)
            self.state.provider_state = "WAITING"
            self.store.write_status(self.state.worker_id, self.state)
            time.sleep(stall_duration)

        # Phase 2: failover — simulate switching to fallback provider
        self.state.failover_count += 1
        self.state.status = WorkerStatus.FAILED_OVER
        self.state.provider_state = "FAILED_OVER"
        self.store.write_status(self.state.worker_id, self.state)
        self.store.record_event(__import__('swarm_runtime.worker', fromlist=['SwarmEvent']).SwarmEvent(
            timestamp=time.time(), swarm_id=self.state.swarm_id,
            worker_id=self.state.worker_id, event="PROVIDER_FAILED_OVER",
            details={"from_provider": "simulated_stall", "to_provider": "fallback"},
        ))

        # Phase 3: continue work with fallback
        self.state.status = WorkerStatus.RUNNING
        self.state.provider_state = "RUNNING"
        self.store.write_status(self.state.worker_id, self.state)

        # Do actual work — a simple code search
        pattern = r"mapped_column"
        search_path = self.repo_path / "portal/models"
        matches: list[dict] = []
        files = list(search_path.rglob("*.py"))
        for i, fpath in enumerate(files):
            if any(p in {"__pycache__", ".git", ".venv"} for p in fpath.parts):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                for line_no, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        matches.append({
                            "file": str(fpath.relative_to(self.repo_path)).replace("\\", "/"),
                            "line": line_no,
                            "content": line.strip(),
                        })
            except Exception:
                pass
            self._heartbeat(f"scanning with fallback ({i+1}/{len(files)})", i + 1, len(files))

        self.findings = {
            "failover_test": True,
            "stall_duration": stall_duration,
            "failover_count": self.state.failover_count,
            "matches_after_failover": len(matches),
            "matches": matches[:20],
        }
        self._evidence("failover_test", {"failovers": self.state.failover_count})
        self._heartbeat("completed", len(files), 0)
        return 0


class CrashTestWorker(BaseWorker):
    """Tests crash recovery — deliberately crashes mid-task, expects restart.

    Task params:
      crash_after: number of files to process before crashing
      total_files: total files to process (for checkpoint verification)
    """

    def execute(self) -> int:
        crash_after = self.state.task.get("crash_after", 3)
        search_path = self.repo_path / "portal/models"
        files = sorted(search_path.rglob("*.py"))
        total = len(files)

        self._heartbeat("processing files", 0, total)

        results: list[dict] = []
        for i, fpath in enumerate(files):
            if any(p in {"__pycache__", ".git", ".venv"} for p in fpath.parts):
                continue

            # Check for checkpoint
            ckpt = self.store.read_checkpoint(self.state.worker_id)
            if ckpt and ckpt.get("cursor"):
                if str(fpath) <= ckpt["cursor"]:
                    continue  # skip already-processed

            results.append({
                "file": str(fpath.relative_to(self.repo_path)).replace("\\", "/"),
                "size": fpath.stat().st_size,
            })

            # Write checkpoint
            self.state.cursor = str(fpath)
            self.state.partial_findings = results
            self.store.write_checkpoint(self.state.worker_id, self.state)

            self._heartbeat(f"processing ({i+1}/{total})", i + 1, total)

            # Crash after crash_after files
            if i + 1 >= crash_after and self.state.task.get("should_crash", True):
                # Optional delay before crash — gives external killer time to act
                crash_delay = self.state.task.get("crash_delay", 0)
                if crash_delay > 0:
                    self._heartbeat(f"waiting at crash point ({crash_delay}s)", i + 1, total)
                    time.sleep(crash_delay)
                self.state.errors.append(f"deliberate_crash_after_{crash_after}_files")
                self.store.write_status(self.state.worker_id, self.state)
                # Simulate crash — exit non-zero
                return 99

        self.findings = {
            "crash_test": True,
            "total_files_processed": len(results),
            "files": results,
        }
        self._evidence("crash_test", {"files_processed": len(results)})
        self._heartbeat("completed", total, 0)
        return 0


class BuilderWorker(BaseWorker):
    """Creates a fixture file in an isolated worktree and commits it.

    Task params:
      fixture_path: path for the fixture file (absolute or relative to worktree)
      content: content to write
      worktree_path: path to git worktree (empty = write to fixture_path directly)
    """

    def execute(self) -> int:
        fixture_path = self.state.task.get("fixture_path", "")
        content = self.state.task.get("content", "# fixture\n")
        worktree_path = self.state.task.get("worktree_path", "")

        self._heartbeat("creating fixture file", 0, 2)

        # Create fixture file (use path directly — can be absolute or relative)
        target = Path(fixture_path)
        # If path is relative and we're in a worktree, resolve relative to worktree
        if not target.is_absolute() and worktree_path:
            target = Path(worktree_path) / fixture_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._heartbeat("fixture created", 1, 2)

        commit_sha = "no_worktree"
        if worktree_path:
            work_dir = Path(worktree_path)
            proc = subprocess.run(
                ["git", "add", fixture_path],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            if proc.returncode != 0:
                self.state.errors.append(f"git_add_failed: {proc.stderr}")
                return 1
            proc = subprocess.run(
                ["git", "commit", "-m", f"fixture: builder {self.state.worker_id}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            if proc.returncode != 0:
                self.state.errors.append(f"git_commit_failed: {proc.stderr}")
                return 1
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            commit_sha = proc.stdout.strip()

        self.findings = {
            "builder_id": self.state.worker_id,
            "fixture_path": fixture_path,
            "commit_sha": commit_sha,
            "content_written": content,
        }
        self._evidence("builder", {"commit": commit_sha, "file": fixture_path})
        self._heartbeat("completed", 2, 0)
        return 0


class DeliberatelyFlawedBuilderWorker(BaseWorker):
    """Creates a fixture file with a deliberately injected defect for breaker testing."""

    def execute(self) -> int:
        fixture_content = '''"""Fixture with an injected defect for SWARM-ACCEPTANCE-005."""
import uuid


def generate_tenant_id() -> uuid.UUID:
    """Generate a valid tenant ID.

    BUG INJECTED: returns a non-UUID string instead of a uuid.UUID.
    """
    return "not-a-uuid"  # This is the defect — not a uuid.UUID


def validate_tenant_id(tid: str) -> bool:
    """Validate that a tenant ID is a proper UUID string."""
    try:
        uuid.UUID(tid)
        return True
    except (ValueError, AttributeError):
        return False
'''

        self._heartbeat("creating flawed fixture", 0, 2)
        fixture_dir = self.store.worker_dir(self.state.worker_id)
        fixture_path = fixture_dir / "flawed_fixture.py"
        fixture_path.write_text(fixture_content, encoding="utf-8")
        self._heartbeat("fixture created", 1, 2)

        self.findings = {
            "builder_id": self.state.worker_id,
            "fixture_path": str(fixture_path),
            "injected_defect": {
                "function": "generate_tenant_id",
                "expected_return": "uuid.UUID",
                "actual_return": "str ('not-a-uuid')",
                "defect_type": "type_mismatch",
                "line": 10,
            },
        }
        self._evidence("flawed_builder", {"fixture": str(fixture_path)})
        self._heartbeat("completed", 2, 0)
        return 0


class IndependentBreakerWorker(BaseWorker):
    """Independently analyzes a fixture file and looks for defects via AST.

    Task params:
      target_fixture: path to the fixture file to analyze
    """

    def execute(self) -> int:
        target_fixture = self.state.task.get("target_fixture", "")

        self._heartbeat("analyzing fixture", 0, 3)

        if not target_fixture:
            self.findings = {"error": "no target_fixture specified"}
            return 1

        fixture_path = Path(target_fixture)
        if not fixture_path.exists():
            self.findings = {"error": f"fixture not found: {target_fixture}"}
            return 1

        content = fixture_path.read_text(encoding="utf-8")
        self._heartbeat("file read", 1, 3)

        defects: list[dict] = []

        import ast as _ast
        try:
            tree = _ast.parse(content)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.FunctionDef):
                    # Handle both Name (e.g. 'bool') and Attribute (e.g. 'uuid.UUID') return annotations
                    expected_type = ""
                    if node.returns and isinstance(node.returns, _ast.Name):
                        expected_type = node.returns.id
                    elif node.returns and isinstance(node.returns, _ast.Attribute):
                        expected_type = f"{node.returns.value.id}.{node.returns.attr}" if hasattr(node.returns.value, 'id') else node.returns.attr

                    if expected_type:
                        for child in _ast.walk(node):
                            if isinstance(child, _ast.Return) and child.value:
                                if isinstance(child.value, _ast.Constant) and isinstance(child.value.value, str):
                                    if expected_type == "uuid.UUID":
                                        defects.append({
                                            "function": node.name,
                                            "defect_type": "type_mismatch",
                                            "expected_return": expected_type,
                                            "actual_return": f"str ('{child.value.value}')",
                                            "line": child.lineno,
                                            "severity": "HIGH",
                                        })
        except SyntaxError as e:
            defects.append({"defect_type": "syntax_error", "error": str(e)})

        self._heartbeat("AST analysis done", 2, 3)

        if "def validate_tenant_id" not in content:
            defects.append({"defect_type": "missing_validation", "severity": "MEDIUM"})

        self._heartbeat("analysis complete", 3, 3)

        self.findings = {
            "breaker_id": self.state.worker_id,
            "target_fixture": target_fixture,
            "defects_found": len(defects),
            "defects": defects,
            "found_injected_defect": any(
                d.get("defect_type") == "type_mismatch" and "generate_tenant_id" in d.get("function", "")
                for d in defects
            ),
        }
        self._evidence("breaker", {"defects": len(defects)})
        # Breaker returns 0 when it successfully analyzed the file,
        # regardless of whether defects were found — finding defects is success
        return 0


# Worker class registry
WORKER_REGISTRY: dict[str, type[BaseWorker]] = {
    "CodeSearchWorker": CodeSearchWorker,
    "ASTAnalysisWorker": ASTAnalysisWorker,
    "DatabaseSchemaWorker": DatabaseSchemaWorker,
    "TestRunnerWorker": TestRunnerWorker,
    "GitDiffWorker": GitDiffWorker,
    "StaticAnalysisWorker": StaticAnalysisWorker,
    "ModelReasoningWorker": ModelReasoningWorker,
    "BreakerWorker": BreakerWorker,
    "FailoverTestWorker": FailoverTestWorker,
    "CrashTestWorker": CrashTestWorker,
    "BuilderWorker": BuilderWorker,
    "DeliberatelyFlawedBuilderWorker": DeliberatelyFlawedBuilderWorker,
    "IndependentBreakerWorker": IndependentBreakerWorker,
}
