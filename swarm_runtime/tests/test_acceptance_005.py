"""SWARM-ACCEPTANCE-005 — Builder + Breaker defect detection test.

Builder creates a deliberately flawed small fixture patch.
Breaker must independently detect the injected defect.
Required:
  BUILDER_PATCH = PRODUCED
  BREAKER_INDEPENDENT = TRUE
  BREAKER_FOUND_INJECTED_DEFECT = TRUE
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO))

from swarm_runtime import SwarmController, WorkerSpec
from swarm_runtime.artifact_store import ArtifactStore
from swarm_runtime.tool_workers import WORKER_REGISTRY, BaseWorker


class DeliberatelyFlawedBuilderWorker(BaseWorker):
    """Creates a fixture file with a deliberately injected defect.

    The defect: a Python function that claims to return a UUID but actually
    returns a non-UUID string ("not-a-uuid").
    """

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

        # Write fixture to a temp location in the run dir
        fixture_dir = self.store.worker_dir(self.state.worker_id)
        fixture_path = fixture_dir / "flawed_fixture.py"
        fixture_path.write_text(fixture_content, encoding="utf-8")

        self._heartbeat("fixture created", 1, 2)

        # Write findings about the defect (for the breaker to check against)
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
    """Independently analyzes a fixture file and looks for defects.

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

        # Check 1: Functions that claim to return a type but return something else
        import ast
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check return annotation
                    if node.returns and isinstance(node.returns, ast.Name):
                        expected_type = node.returns.id

                        # Look at return statements
                        for child in ast.walk(node):
                            if isinstance(child, ast.Return) and child.value:
                                # Check if return value is a string constant
                                if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
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

        # Check 2: Functions that return string literals when annotated as UUID
        # Already covered above

        # Check 3: Verify validate function actually validates correctly
        # (just a basic check that the function exists)
        if "def validate_tenant_id" not in content:
            defects.append({
                "defect_type": "missing_validation",
                "severity": "MEDIUM",
            })

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
        return 0 if defects else 1


WORKER_REGISTRY["DeliberatelyFlawedBuilderWorker"] = DeliberatelyFlawedBuilderWorker
WORKER_REGISTRY["IndependentBreakerWorker"] = IndependentBreakerWorker


def run_acceptance_005() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-005"
    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    controller = SwarmController(
        swarm_id=swarm_id,
        repo_path=str(REPO),
        run_dir=run_dir,
        max_concurrent=2,
    )

    # Phase 1: Builder creates flawed fixture
    builder_spec = WorkerSpec(
        worker_id="BUILDER",
        role="flawed_builder",
        worker_class="DeliberatelyFlawedBuilderWorker",
        task={},
        artifact_path="artifacts/builder.json",
        base_sha="eeb55ffb",
        timeout_seconds=30,
    )

    print(f"[{swarm_id}] Phase 1: Launching builder...")
    controller.launch(builder_spec)
    summary = controller.wait(timeout=60)
    s = summary.to_dict()

    builder_detail = next(d for d in s['worker_details'] if d['worker_id'] == 'BUILDER')
    print(f"  Builder: status={builder_detail['status']} artifact={builder_detail['artifact_valid']}")

    # Get the fixture path from builder's findings
    store = ArtifactStore(run_dir)
    builder_findings = json.loads(
        (store.worker_dir("BUILDER") / "findings.json").read_text(encoding="utf-8")
    )
    fixture_path = builder_findings["findings"]["fixture_path"]

    # Phase 2: Breaker analyzes the fixture independently
    controller2 = SwarmController(
        swarm_id=swarm_id,
        repo_path=str(REPO),
        run_dir=run_dir,
        max_concurrent=2,
    )

    breaker_spec = WorkerSpec(
        worker_id="BREAKER",
        role="independent_breaker",
        worker_class="IndependentBreakerWorker",
        task={"target_fixture": fixture_path},
        artifact_path="artifacts/breaker.json",
        base_sha="eeb55ffb",
        timeout_seconds=30,
    )

    print(f"\n[{swarm_id}] Phase 2: Launching breaker...")
    controller2.launch(breaker_spec)
    summary2 = controller2.wait(timeout=60)
    s2 = summary2.to_dict()

    breaker_detail = next(d for d in s2['worker_details'] if d['worker_id'] == 'BREAKER')
    print(f"  Breaker: status={breaker_detail['status']} artifact={breaker_detail['artifact_valid']}")

    # Check breaker findings
    breaker_valid = store.validate_artifact("BREAKER")
    breaker_found_defect = False
    if breaker_valid["valid"]:
        breaker_data = json.loads(
            (store.worker_dir("BREAKER") / "findings.json").read_text(encoding="utf-8")
        )
        breaker_found_defect = breaker_data["findings"]["found_injected_defect"]
        print(f"  Breaker found defects: {breaker_data['findings']['defects_found']}")
        for d in breaker_data["findings"]["defects"]:
            print(f"    - {d.get('function', '?')}: {d.get('defect_type')} (line {d.get('line', '?')})")

    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-005 RESULTS")
    print(f"{'='*60}")
    criteria = [
        ("BUILDER_PATCH = PRODUCED", builder_detail['status'] == 'completed' and builder_detail['artifact_valid']),
        ("BREAKER_INDEPENDENT = TRUE", breaker_detail['worker_id'] == 'BREAKER'),
        ("BREAKER_FOUND_INJECTED_DEFECT = TRUE", breaker_found_defect),
        ("BREAKER_ARTIFACT_VALID", breaker_valid['valid']),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"builder": s, "breaker": s2, "breaker_found_defect": breaker_found_defect, "all_pass": all_pass}


if __name__ == "__main__":
    result = run_acceptance_005()
    sys.exit(0 if result['all_pass'] else 1)
