"""Tests for scripts/ci/validate_release_surface_manifest.py.

Baseline checks run against small temporary git repositories so that the
declared-commit tree, the working-tree checkout and HEAD can genuinely differ.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate_release_surface_manifest as vm

SHA_B = "b" * 40
SHA_C = "c" * 40
REAL_MANIFEST = os.path.join(vm.REPO_ROOT, vm.DEFAULT_MANIFEST)
GIT_ID = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]


def run_git(root: Path, *args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_ID, *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit_file(root: Path, rel: str, text: str = "x = 1\n") -> str:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    run_git(root, "add", "--", rel)
    run_git(root, "commit", "-q", "-m", f"add {rel}")
    return run_git(root, "rev-parse", "HEAD")


@pytest.fixture(scope="module")
def template_repo(tmp_path_factory):
    """Build the small git repository once; each test gets its own copy."""
    root = tmp_path_factory.mktemp("template") / "repo"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main", "--template=")
    commit_file(root, "AGENTS.md", "# owner\n")
    commit_file(root, ".github/workflows/ci.yml", "name: ci\n")
    commit_file(root, "pkg/test_mod.py", "def test_x():\n    pass\n")
    base = commit_file(root, "pkg/mod.py")
    return SimpleNamespace(root=root, base=base)


@pytest.fixture
def repo(template_repo, tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(template_repo.root, root)
    return SimpleNamespace(root=root, base=template_repo.base)


def good_manifest(base: str) -> dict:
    return {
        "manifest_id": "TEST",
        "schema_version": 1,
        "baseline_ref": base,
        "coverage": {
            "status": "PARTIAL",
            "covered_areas": ["alpha", "beta", "gamma"],
            "not_covered": "everything else",
        },
        "entries": [
            {
                "id": "alpha-main",
                "area": "alpha",
                "name": "Alpha",
                "domain": "pkg",
                "owner": "dox:AGENTS.md",
                "ci_lane": [".github/workflows/ci.yml"],
                "presence": "on-main",
                "source_presence": "yes",
                "canonical_status": "candidate",
                "runtime_evidence": "tests-only",
                "verified_ref": base,
                "entrypoints": ["pkg/mod.py"],
                "paths": ["pkg", "pkg/mod.py"],
                "tests": ["pkg/test_mod.py"],
            },
            {
                "id": "beta-pr",
                "area": "beta",
                "name": "Beta",
                "domain": "beta",
                "owner": "UNKNOWN",
                "ci_lane": "UNKNOWN",
                "presence": "branch-only",
                "source_presence": "branch-only",
                "canonical_status": "unresolved",
                "runtime_evidence": "none",
                "branch_refs": [
                    {"pr": 1, "branch": "feat/x", "head_sha": SHA_B},
                    {"pr": 2, "branch": "feat/y", "head_sha": SHA_C},
                ],
            },
            {
                "id": "gamma-ext",
                "area": "gamma",
                "name": "Gamma",
                "domain": "external",
                "owner": "UNKNOWN",
                "ci_lane": "UNKNOWN",
                "presence": "external-not-inspected",
                "source_presence": "unknown",
                "canonical_status": "unresolved",
                "runtime_evidence": "none",
            },
        ],
    }


def errors_for(manifest: object, repo) -> list[str]:
    return vm.validate_manifest(manifest, str(repo.root))


def has(errors: list[str], needle: str) -> bool:
    return any(needle in e for e in errors)


# ---------------------------------------------------------------- happy path


def test_good_manifest_passes_against_real_baseline_commit(repo):
    assert errors_for(good_manifest(repo.base), repo) == []


def test_main_exit_codes_and_output(repo, capsys):
    manifest_path = repo.root / "registry" / "release_surface_manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(json.dumps(good_manifest(repo.base)))
    assert vm.main(["--repo-root", str(repo.root)]) == 0
    assert "passed (coverage: PARTIAL)" in capsys.readouterr().out
    bad = good_manifest(repo.base)
    bad["entries"][0]["paths"].append("pkg/nope.py")
    manifest_path.write_text(json.dumps(bad))
    assert vm.main(["--repo-root", str(repo.root)]) == 1
    assert "FAILED" in capsys.readouterr().out


# ---------------------------------------------------- baseline git-object checks


def test_path_present_now_but_absent_from_claimed_commit_fails(repo):
    commit_file(repo.root, "pkg/added_later.py")
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"].append("pkg/added_later.py")
    errors = errors_for(manifest, repo)
    assert (repo.root / "pkg" / "added_later.py").exists()
    assert has(errors, "path absent at baseline")
    assert not has(errors, "not found in checkout")


def test_path_in_baseline_but_removed_from_checkout_fails(repo):
    run_git(repo.root, "rm", "-q", "pkg/mod.py")
    run_git(repo.root, "commit", "-q", "-m", "remove")
    errors = errors_for(good_manifest(repo.base), repo)
    assert has(errors, "not found in checkout")
    assert not has(errors, "absent at baseline")


def test_exact_case_enforced_against_baseline_tree(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"] = ["pkg/MOD.py"]
    errors = errors_for(manifest, repo)
    assert has(errors, "absent at baseline")
    assert has(errors, "(exact case)")


def test_directory_path_resolved_in_baseline_tree(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"] = ["pkg", ".github/workflows/ci.yml"]
    assert errors_for(manifest, repo) == []


def test_file_used_as_directory_fails(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"] = ["pkg/mod.py/inner"]
    assert has(errors_for(manifest, repo), "baseline")


def test_verified_ref_must_equal_baseline(repo):
    head = commit_file(repo.root, "pkg/other.py")
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["verified_ref"] = head
    assert has(errors_for(manifest, repo), "verified_ref must equal baseline_ref")


def test_missing_verified_ref_on_main_fails(repo):
    manifest = good_manifest(repo.base)
    del manifest["entries"][0]["verified_ref"]
    assert has(errors_for(manifest, repo), "verified_ref must equal baseline_ref")


def test_unavailable_baseline_object_fails_and_never_falls_back_to_head(repo):
    manifest = good_manifest("c" * 40)
    manifest["entries"][0]["verified_ref"] = "c" * 40
    errors = errors_for(manifest, repo)
    assert has(errors, "not available in this checkout")
    assert has(errors, "never substitutes HEAD")
    assert errors, "a missing baseline must never validate"


def test_shallow_clone_without_baseline_commit_is_reported(repo, tmp_path):
    commit_file(repo.root, "pkg/later.py")
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", repo.root.as_uri(), str(shallow)],
        check=True,
        capture_output=True,
    )
    errors = vm.validate_manifest(good_manifest(repo.base), str(shallow))
    assert has(errors, "not available in this checkout")
    assert has(errors, "fetch full history")


def test_non_ancestor_baseline_fails(repo):
    run_git(repo.root, "checkout", "-q", "-b", "side", repo.base)
    side = commit_file(repo.root, "pkg/side_only.py")
    run_git(repo.root, "checkout", "-q", "main")
    commit_file(repo.root, "pkg/main_only.py")
    manifest = good_manifest(side)
    errors = errors_for(manifest, repo)
    assert has(errors, "not an ancestor of the checked-out HEAD")


def test_not_a_git_repository_reports_unavailable_baseline(tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / "pkg").mkdir()
    (root / "pkg" / "mod.py").write_text("x = 1\n")
    manifest = good_manifest("a" * 40)
    manifest["entries"][0]["verified_ref"] = "a" * 40
    manifest["entries"][0]["owner"] = "UNKNOWN"
    manifest["entries"][0]["ci_lane"] = "UNKNOWN"
    errors = vm.validate_manifest(manifest, str(root))
    assert has(errors, "not available in this checkout")


def test_baseline_symlink_entry_is_rejected(repo):
    blob = run_git(repo.root, "hash-object", "-w", "--stdin", stdin="target")
    run_git(repo.root, "update-index", "--add", "--cacheinfo", f"120000,{blob},pkg/lnk")
    run_git(repo.root, "commit", "-q", "-m", "symlink")
    base = run_git(repo.root, "rev-parse", "HEAD")
    manifest = good_manifest(base)
    manifest["entries"][0]["paths"] = ["pkg/lnk"]
    assert has(errors_for(manifest, repo), "symlink or submodule at baseline")


def test_owner_and_ci_lane_paths_verified_at_baseline(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["owner"] = "dox:missing/AGENTS.md"
    manifest["entries"][0]["ci_lane"] = [".github/workflows/missing.yml"]
    errors = errors_for(manifest, repo)
    assert has(errors, "missing/AGENTS.md")
    assert has(errors, "missing.yml")


def test_owner_must_be_unknown_or_dox_path(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["owner"] = "alice"
    assert has(errors_for(manifest, repo), "owner must be")


# ------------------------------------------------------------- path safety


@pytest.mark.parametrize(
    "bad",
    [
        "/etc/passwd",
        "C:/Windows",
        "c:rel",
        "pkg\\mod.py",
        "../outside",
        "pkg/../mod.py",
        "pkg//mod.py",
        "pkg/./mod.py",
        "pkg/",
        "",
        "pkg/mo:d.py",
        "pkg/mod.py.",
        "pkg/mod.py ",
        "pkg/mo\x00d.py",
        "pkg/mo\x1fd.py",
        "pkg/mo*d.py",
    ],
    ids=repr,
)
def test_malformed_or_unsafe_paths_rejected(repo, bad):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"] = [bad]
    errors = errors_for(manifest, repo)
    assert errors
    assert not has(errors, "Traceback")


def _make_dir_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
    pytest.skip(
        "platform limitation: this account cannot create symlinks or junctions, "
        "so the outside-root containment boundary was not exercised here"
    )


def test_link_resolving_outside_root_rejected(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("s")
    _make_dir_link(root / "link", outside)
    problem = vm.checkout_problem(str(root), "link/secret.txt")
    assert problem is not None
    assert "outside the repository root" in problem


def test_link_resolving_inside_root_is_contained(tmp_path):
    root = tmp_path / "root"
    (root / "real").mkdir(parents=True)
    (root / "real" / "f.txt").write_text("f")
    _make_dir_link(root / "alias", root / "real")
    assert vm.checkout_problem(str(root), "alias/f.txt") is None


def test_checkout_exact_case_not_weakened(tmp_path):
    (tmp_path / "Dir").mkdir()
    (tmp_path / "Dir" / "File.txt").write_text("f")
    assert vm.checkout_problem(str(tmp_path), "Dir/File.txt") is None
    assert vm.checkout_problem(str(tmp_path), "dir/File.txt") is not None
    assert vm.checkout_problem(str(tmp_path), "Dir/file.txt") is not None


# ------------------------------------------- source presence / branch evidence


@pytest.mark.parametrize("value", ["no", "yes", "branch-only", "maybe"])
def test_external_entry_source_presence_must_be_unknown(repo, value):
    manifest = good_manifest(repo.base)
    manifest["entries"][2]["source_presence"] = value
    assert has(errors_for(manifest, repo), "requires source_presence 'unknown'")


def test_external_entry_unknown_source_presence_is_valid(repo):
    assert errors_for(good_manifest(repo.base), repo) == []


@pytest.mark.parametrize(("presence_index", "value"), [(0, "unknown"), (1, "unknown"), (0, "no")])
def test_unknown_source_presence_only_for_external(repo, presence_index, value):
    manifest = good_manifest(repo.base)
    manifest["entries"][presence_index]["source_presence"] = value
    assert errors_for(manifest, repo)


def test_external_entry_with_paths_or_verified_ref_rejected(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][2]["paths"] = ["pkg"]
    manifest["entries"][2]["verified_ref"] = repo.base
    errors = errors_for(manifest, repo)
    assert has(errors, "must not record paths")
    assert has(errors, "must not carry verified_ref")


def test_branch_only_candidates_need_full_sha_each(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"][1]["head_sha"] = "abc1234"
    assert has(errors_for(manifest, repo), "full 40-hex head_sha")


def test_branch_only_rejects_prose_verified_ref(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["verified_ref"] = "head SHAs recorded per branch"
    assert has(errors_for(manifest, repo), "belongs in branch_refs[].head_sha")


def test_branch_only_requires_branch_pr_and_unique_prs(repo):
    manifest = good_manifest(repo.base)
    refs = manifest["entries"][1]["branch_refs"]
    refs[0]["branch"] = ""
    refs[1]["pr"] = 1
    errors = errors_for(manifest, repo)
    assert has(errors, "needs branch name")
    assert has(errors, "duplicate pr 1")


def test_branch_only_with_main_paths_rejected(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["paths"] = ["pkg"]
    assert has(errors_for(manifest, repo), "must not record main-checkout paths")


def test_branch_only_requires_branch_refs(repo):
    manifest = good_manifest(repo.base)
    del manifest["entries"][1]["branch_refs"]
    assert has(errors_for(manifest, repo), "requires non-empty branch_refs")


def test_branch_only_cannot_claim_runtime_evidence(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["runtime_evidence"] = "tests-only"
    assert has(errors_for(manifest, repo), "only on-main entries")


# ------------------------------------------------------- coverage and enums


def test_coverage_must_be_partial(repo):
    manifest = good_manifest(repo.base)
    manifest["coverage"]["status"] = "COMPLETE"
    assert has(errors_for(manifest, repo), "coverage.status")


def test_coverage_requires_not_covered_statement(repo):
    manifest = good_manifest(repo.base)
    manifest["coverage"]["not_covered"] = ""
    assert has(errors_for(manifest, repo), "not_covered")


def test_covered_area_without_entry_fails(repo):
    manifest = good_manifest(repo.base)
    manifest["coverage"]["covered_areas"].append("delta")
    assert has(errors_for(manifest, repo), "covered area has no entry: delta")


def test_entry_area_outside_coverage_fails(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["area"] = "zeta"
    assert has(errors_for(manifest, repo), "not in coverage.covered_areas")


def test_duplicate_id_fails(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["id"] = "alpha-main"
    assert has(errors_for(manifest, repo), "duplicate entry id")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("presence", "everywhere"),
        ("source_presence", "maybe"),
        ("canonical_status", "ratified"),
        ("runtime_evidence", "certified"),
    ],
)
def test_unknown_enum_values_fail(repo, field, value):
    manifest = good_manifest(repo.base)
    manifest["entries"][0][field] = value
    assert has(errors_for(manifest, repo), field)


def test_certified_lane_evidence_format_accepted(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["runtime_evidence"] = "certified-lane:postgres-race"
    assert errors_for(manifest, repo) == []


def test_tests_only_requires_tests(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["tests"] = []
    assert has(errors_for(manifest, repo), "requires listed tests")


def test_missing_required_entry_field_fails(repo):
    manifest = good_manifest(repo.base)
    del manifest["entries"][0]["canonical_status"]
    assert has(errors_for(manifest, repo), "canonical_status")


def test_ws00_metadata_fields_required_even_when_unknown(repo):
    manifest = good_manifest(repo.base)
    del manifest["entries"][1]["domain"]
    del manifest["entries"][1]["owner"]
    del manifest["entries"][1]["ci_lane"]
    errors = errors_for(manifest, repo)
    assert has(errors, "domain")
    assert has(errors, "owner must be")
    assert has(errors, "ci_lane must be")


# ---------------------------------------- null / malformed JSON shapes (no crash)

BAD_VALUES = [None, [], {}, ["x"], {"k": "v"}, 7, 1.5, True, ""]


@pytest.mark.parametrize("root_value", [None, [], "text", 3, True])
def test_non_object_manifest_root_reports_error(repo, root_value):
    assert errors_for(root_value, repo) == ["manifest root must be an object"]


@pytest.mark.parametrize("field", ["manifest_id", "schema_version", "baseline_ref", "coverage", "entries"])
@pytest.mark.parametrize("bad", BAD_VALUES, ids=repr)
def test_malformed_header_values_report_errors_not_exceptions(repo, field, bad):
    manifest = good_manifest(repo.base)
    manifest[field] = bad
    errors = errors_for(manifest, repo)
    assert errors
    assert all(isinstance(e, str) for e in errors)


@pytest.mark.parametrize("field", ["status", "covered_areas", "not_covered"])
@pytest.mark.parametrize("bad", BAD_VALUES, ids=repr)
def test_malformed_coverage_values_report_errors(repo, field, bad):
    manifest = good_manifest(repo.base)
    manifest["coverage"][field] = bad
    assert errors_for(manifest, repo)


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "area",
        "name",
        "domain",
        "owner",
        "ci_lane",
        "presence",
        "source_presence",
        "canonical_status",
        "runtime_evidence",
        "verified_ref",
        "paths",
        "tests",
        "entrypoints",
    ],
)
@pytest.mark.parametrize("bad", BAD_VALUES, ids=repr)
def test_malformed_on_main_entry_values_report_errors(repo, field, bad):
    manifest = good_manifest(repo.base)
    manifest["entries"][0][field] = bad
    errors = errors_for(manifest, repo)
    assert all(isinstance(e, str) for e in errors)
    if bad in ([], "") and field in ("tests", "entrypoints"):
        return  # empty list/string for optional-ish lists is covered by other tests
    if bad == [] and field == "ci_lane":
        assert has(errors, "ci_lane must be")
        return
    assert errors, f"{field}={bad!r} must not validate"


_NON_SCALAR_OR_EMPTY = [None, [], {}, ["x"], {"k": "v"}, True, ""]
# Invalid values differ per field: PR 7 and branch name "1" are legitimate.
BRANCH_REF_INVALID = (
    [("pr", v) for v in [*_NON_SCALAR_OR_EMPTY, 1.5, "1", "7", -3, 0]]
    + [("branch", v) for v in [*_NON_SCALAR_OR_EMPTY, 7, 1.5]]
    + [("head_sha", v) for v in [*_NON_SCALAR_OR_EMPTY, 7, 1.5, "1", -3, 0]]
)


@pytest.mark.parametrize(("field", "bad"), BRANCH_REF_INVALID, ids=repr)
def test_malformed_branch_ref_values_report_errors(repo, field, bad):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"][0][field] = bad
    assert errors_for(manifest, repo)


@pytest.mark.parametrize(("field", "value"), [("pr", 7), ("pr", 100000), ("branch", "1"), ("branch", "release/v1.2")])
def test_legitimate_branch_ref_values_accepted(repo, field, value):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"][0][field] = value
    assert errors_for(manifest, repo) == []


TRAILING = ["\n", " ", "\t", "\r\n", "\x00"]


@pytest.mark.parametrize("suffix", TRAILING, ids=repr)
def test_branch_head_sha_with_trailing_characters_rejected(repo, suffix):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"][0]["head_sha"] = SHA_B + suffix
    assert has(errors_for(manifest, repo), "full 40-hex head_sha")


@pytest.mark.parametrize("suffix", TRAILING, ids=repr)
def test_baseline_and_verified_ref_with_trailing_characters_rejected(repo, suffix):
    manifest = good_manifest(repo.base + suffix)
    assert errors_for(manifest, repo)
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["verified_ref"] = repo.base + suffix
    assert has(errors_for(manifest, repo), "verified_ref must equal baseline_ref")


@pytest.mark.parametrize("suffix", TRAILING, ids=repr)
def test_runtime_evidence_with_trailing_characters_rejected(repo, suffix):
    for value in ("tests-only", "none", "certified-lane:lane-1"):
        manifest = good_manifest(repo.base)
        manifest["entries"][0]["runtime_evidence"] = value + suffix
        assert has(errors_for(manifest, repo), "unknown runtime_evidence"), repr(value + suffix)


def test_uppercase_or_short_sha_rejected(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"][0]["head_sha"] = SHA_B.upper()
    assert has(errors_for(manifest, repo), "full 40-hex head_sha")
    manifest["entries"][1]["branch_refs"][0]["head_sha"] = SHA_B[:-1]
    assert has(errors_for(manifest, repo), "full 40-hex head_sha")


@pytest.mark.parametrize("bad_item", [None, [], "x", 5, True])
def test_non_object_entries_and_branch_refs_report_errors(repo, bad_item):
    manifest = good_manifest(repo.base)
    manifest["entries"].append(bad_item)
    assert has(errors_for(manifest, repo), "entry must be an object")
    manifest = good_manifest(repo.base)
    manifest["entries"][1]["branch_refs"].append(bad_item)
    assert has(errors_for(manifest, repo), "branch_refs item must be an object")


def test_path_list_items_of_wrong_type_report_errors(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["paths"] = [None, ["pkg"], {"a": 1}, 5]
    assert errors_for(manifest, repo)


def test_unhashable_id_and_area_do_not_crash(repo):
    manifest = good_manifest(repo.base)
    manifest["entries"][0]["id"] = ["a"]
    manifest["entries"][0]["area"] = {"a": 1}
    assert errors_for(manifest, repo)


def test_missing_manifest_file_reports_error(tmp_path):
    assert vm.load_and_validate(str(tmp_path)) == [f"manifest not found: {vm.DEFAULT_MANIFEST}"]


@pytest.mark.parametrize("content", ["{not json", "", "null", "[1, 2]", '"s"'])
def test_unparsable_or_wrong_shape_manifest_file_reports_error(tmp_path, content):
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry" / "release_surface_manifest.json").write_text(content)
    errors = vm.load_and_validate(str(tmp_path))
    assert errors
    assert "unreadable" in errors[0] or "must be an object" in errors[0]


# ------------------------------------------------------- the real manifest


def _real() -> dict:
    with open(REAL_MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def test_real_manifest_valid_against_baseline_and_checkout():
    assert vm.load_and_validate(vm.REPO_ROOT) == []


def test_real_manifest_declares_partial_and_five_areas():
    manifest = _real()
    assert manifest["coverage"]["status"] == "PARTIAL"
    assert sorted(manifest["coverage"]["covered_areas"]) == sorted(
        ["mission-control", "agents", "hermes", "ike-bot", "agent-commons"]
    )
    assert manifest["baseline_ref"] == "051e2594c67a805ceacc66ea2a6fc6db9c0bc793"


def test_real_manifest_keeps_agent_commons_unresolved_with_both_candidates():
    commons = [e for e in _real()["entries"] if e["area"] == "agent-commons"]
    assert len(commons) == 1
    entry = commons[0]
    assert entry["presence"] == "branch-only"
    assert entry["canonical_status"] == "unresolved"
    assert {r["pr"]: r["head_sha"] for r in entry["branch_refs"]} == {
        244: "68f17304d27ffe7f10851021c8dca6b5d51eac95",
        346: "eb60476a74b84e41fce9d89d97889c4393da27f9",
    }


def test_real_manifest_external_entry_source_presence_unknown():
    external = [e for e in _real()["entries"] if e["presence"] == "external-not-inspected"]
    assert external
    assert all(e["source_presence"] == "unknown" for e in external)


def test_real_manifest_separates_source_canonical_and_runtime_concepts():
    for entry in _real()["entries"]:
        assert {"source_presence", "canonical_status", "runtime_evidence"} <= set(entry)


def test_real_manifest_mutation_of_baseline_is_detected():
    manifest = copy.deepcopy(_real())
    manifest["baseline_ref"] = "0" * 40
    errors = vm.validate_manifest(manifest, vm.REPO_ROOT)
    assert has(errors, "not available in this checkout")
