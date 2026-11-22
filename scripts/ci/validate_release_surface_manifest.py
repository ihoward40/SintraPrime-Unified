#!/usr/bin/env python3
"""Validate registry/release_surface_manifest.json (SP-RELEASE-SURFACE-MANIFEST-001).

Fails (exit 1) when:
- the manifest is missing, unparsable, or has a malformed shape (wrong JSON
  types are reported as validation errors, never as tracebacks)
- coverage is not declared PARTIAL, or covered_areas / not_covered are missing,
  or a covered area has no entry
- an entry has an unknown area / enum value, a duplicate id, or a missing field
- an ``on-main`` entry's paths, entrypoints, tests, owner or ci_lane files are
  absent (exact case) from the git tree of the declared ``baseline_ref`` commit
  OR from the checkout under test, or resolve outside the repository root
- ``baseline_ref`` is not a locally available commit that is an ancestor of
  HEAD (the validator never fetches and never substitutes HEAD for a missing
  baseline), or an on-main ``verified_ref`` differs from ``baseline_ref``
- a ``branch-only`` candidate lacks a PR number, branch name or full head SHA
- an ``external-not-inspected`` entry records paths or claims known source
  presence (its source presence is ``unknown``)

Standard library plus the ``git`` executable. Deterministic; no network access.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_MANIFEST = os.path.join("registry", "release_surface_manifest.json")
GIT_TIMEOUT_SECONDS = 60

SUPPORTED_SCHEMA_VERSIONS = {1}
COVERAGE_STATUS = {"PARTIAL"}
PRESENCE = {"on-main", "branch-only", "external-not-inspected"}
SOURCE_PRESENCE = {"yes", "branch-only", "unknown"}
CANONICAL_STATUS = {"canonical", "candidate", "unresolved"}
# Matched with fullmatch(): a '$' anchor would accept a trailing newline.
RUNTIME_EVIDENCE_RE = re.compile(r"none|tests-only|certified-lane:[A-Za-z0-9_.\-]+")
SHA_RE = re.compile(r"[0-9a-f]{40}")
UNKNOWN = "UNKNOWN"
OWNER_DOX_PREFIX = "dox:"
BAD_COMPONENT_CHARS = set('<>:"|?*\\')

HEADER_FIELDS = ("manifest_id", "schema_version", "baseline_ref", "coverage", "entries")
ENTRY_FIELDS = (
    "id",
    "area",
    "name",
    "presence",
    "source_presence",
    "canonical_status",
    "runtime_evidence",
    "domain",
    "owner",
    "ci_lane",
)
PATH_LIST_FIELDS = ("paths", "entrypoints", "tests")


def _is_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _in(value: object, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def _is_pr_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


# --------------------------------------------------------------------------
# Repo-relative path syntax and checkout (working tree) verification
# --------------------------------------------------------------------------


def path_syntax_problem(rel: object) -> str | None:
    """Reject absolute, traversal, drive, backslash and malformed components."""
    if not _is_str(rel):
        return "path must be a non-empty string"
    assert isinstance(rel, str)
    if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return f"path must be repo-relative, not absolute: {rel!r}"
    if "\\" in rel:
        return f"path must use forward slashes: {rel!r}"
    for part in rel.split("/"):
        if part in ("", ".", ".."):
            return f"path has empty, '.' or '..' component: {rel!r}"
        if any(ord(ch) < 32 or ch in BAD_COMPONENT_CHARS for ch in part):
            return f"path component has forbidden character: {rel!r}"
        if part.endswith((" ", ".")):
            return f"path component has trailing space or dot: {rel!r}"
    return None


def checkout_problem(root: str, rel: str) -> str | None:
    """Exact-case existence in the working tree and containment under root."""
    parts = rel.split("/")
    current = root
    for part in parts:
        try:
            names = os.listdir(current)
        except OSError:
            return f"path not found in checkout (exact case): {rel}"
        if part not in names:
            return f"path not found in checkout (exact case): {rel}"
        current = os.path.join(current, part)
    real_root = os.path.normcase(os.path.realpath(root))
    real_path = os.path.normcase(os.path.realpath(current))
    try:
        inside = os.path.commonpath([real_root, real_path]) == real_root
    except ValueError:
        inside = False
    if not inside:
        return f"path resolves outside the repository root (symlink/reparse): {rel}"
    return None


# --------------------------------------------------------------------------
# Baseline git-object verification (no network, no HEAD substitution)
# --------------------------------------------------------------------------


def _git(root: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )


class Baseline:
    """Exact-case path lookups in the git tree of a declared baseline commit."""

    def __init__(self, root: str, ref: str) -> None:
        self.root = root
        self.ref = ref
        self._dirs: dict[str, dict[str, tuple[str, str]] | None] = {}
        self.error = self._verify_commit()

    def _verify_commit(self) -> str | None:
        if not _is_sha(self.ref):
            return "baseline_ref must be a 40-hex commit SHA"
        try:
            found = _git(self.root, "rev-parse", "--verify", "--quiet", f"{self.ref}^{{commit}}")
        except (OSError, subprocess.SubprocessError) as exc:
            return f"git unavailable; cannot verify baseline {self.ref}: {exc}"
        if found.returncode != 0 or found.stdout.strip() != self.ref:
            return (
                f"baseline commit {self.ref} is not available in this checkout "
                "(shallow clone or missing object); fetch full history. "
                "The validator never substitutes HEAD or working-tree files for it"
            )
        try:
            ancestor = _git(self.root, "merge-base", "--is-ancestor", self.ref, "HEAD")
        except (OSError, subprocess.SubprocessError) as exc:
            return f"git failed while checking baseline ancestry: {exc}"
        if ancestor.returncode == 1:
            return f"baseline commit {self.ref} is not an ancestor of the checked-out HEAD"
        if ancestor.returncode != 0:
            return f"could not determine whether baseline {self.ref} is an ancestor of HEAD"
        return None

    def _list(self, directory: str) -> dict[str, tuple[str, str]] | None:
        if directory in self._dirs:
            return self._dirs[directory]
        treeish = f"{self.ref}:{directory}" if directory else self.ref
        listing: dict[str, tuple[str, str]] | None = None
        try:
            result = _git(self.root, "ls-tree", "-z", treeish)
        except (OSError, subprocess.SubprocessError):
            result = None
        if result is not None and result.returncode == 0:
            listing = {}
            for record in result.stdout.split("\0"):
                if not record:
                    continue
                meta, _, name = record.partition("\t")
                fields = meta.split()
                if len(fields) == 3 and name:
                    listing[name] = (fields[0], fields[1])
        self._dirs[directory] = listing
        return listing

    def problem(self, rel: str) -> str | None:
        parts = rel.split("/")
        directory = ""
        for index, part in enumerate(parts):
            listing = self._list(directory)
            if listing is None:
                return f"path parent is not a directory at baseline {self.ref[:12]}: {rel}"
            if part not in listing:
                return f"path absent at baseline {self.ref[:12]} (exact case): {rel}"
            mode, kind = listing[part]
            if mode == "120000" or kind == "commit":
                return f"path is a symlink or submodule at baseline {self.ref[:12]}: {rel}"
            if index < len(parts) - 1:
                if kind != "tree":
                    return f"path component is not a directory at baseline: {rel}"
                directory = f"{directory}/{part}" if directory else part
        return None


# --------------------------------------------------------------------------
# Manifest validation
# --------------------------------------------------------------------------


def _check_header(manifest: dict, errors: list[str]) -> list[str]:
    for field in HEADER_FIELDS:
        if field not in manifest:
            errors.append(f"manifest missing required field: {field}")
    if not _is_str(manifest.get("manifest_id")):
        errors.append("manifest_id must be a non-empty string")
    version = manifest.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema_version: {version!r}")
    if not _is_sha(manifest.get("baseline_ref")):
        errors.append("baseline_ref must be a 40-hex commit SHA")

    coverage = manifest.get("coverage")
    covered: list[str] = []
    if not isinstance(coverage, dict):
        errors.append("coverage must be an object")
        return covered
    if not _in(coverage.get("status"), COVERAGE_STATUS):
        errors.append(
            f"coverage.status must be one of {sorted(COVERAGE_STATUS)} "
            f"(got {coverage.get('status')!r}); complete coverage needs a ratified schema change"
        )
    areas = coverage.get("covered_areas")
    if not isinstance(areas, list) or not areas or not all(_is_str(a) for a in areas):
        errors.append("coverage.covered_areas must be a non-empty list of area names")
    else:
        covered = list(areas)
        if len(set(covered)) != len(covered):
            errors.append("coverage.covered_areas contains duplicates")
    if not _is_str(coverage.get("not_covered")):
        errors.append("coverage.not_covered must state what is not inventoried")
    return covered


def _check_branch_refs(label: str, entry: dict, errors: list[str]) -> None:
    refs = entry.get("branch_refs")
    if not isinstance(refs, list) or not refs:
        errors.append(f"{label}: branch-only entry requires non-empty branch_refs")
        return
    seen_prs: set[int] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            errors.append(f"{label}: branch_refs item must be an object")
            continue
        pr = ref.get("pr")
        if not _is_pr_number(pr):
            errors.append(f"{label}: branch_refs item needs positive integer pr")
        elif pr in seen_prs:
            errors.append(f"{label}: duplicate pr {pr} in branch_refs")
        else:
            seen_prs.add(pr)
        if not _is_str(ref.get("branch")):
            errors.append(f"{label}: branch_refs item needs branch name")
        if not _is_sha(ref.get("head_sha")):
            errors.append(f"{label}: branch_refs item needs full 40-hex head_sha")


def _check_path_list(label: str, entry: dict, field: str, errors: list[str]) -> list[str]:
    value = entry.get(field, [])
    if not isinstance(value, list):
        errors.append(f"{label}: {field} must be a list")
        return []
    clean: list[str] = []
    for item in value:
        problem = path_syntax_problem(item)
        if problem:
            errors.append(f"{label}: {field}: {problem}")
        else:
            clean.append(item)
    return clean


def _verify_main_paths(
    label: str, rels: list[str], root: str, baseline: Baseline | None, errors: list[str]
) -> None:
    for rel in rels:
        if baseline is not None and baseline.error is None:
            problem = baseline.problem(rel)
            if problem:
                errors.append(f"{label}: {problem}")
        problem = checkout_problem(root, rel)
        if problem:
            errors.append(f"{label}: {problem}")


def _owner_and_lane_paths(label: str, entry: dict, errors: list[str]) -> list[str]:
    paths: list[str] = []
    owner = entry.get("owner")
    if not _is_str(owner):
        errors.append(f"{label}: owner must be {UNKNOWN!r} or '{OWNER_DOX_PREFIX}<AGENTS.md path>'")
    elif owner != UNKNOWN:
        if owner.startswith(OWNER_DOX_PREFIX):
            rel = owner[len(OWNER_DOX_PREFIX) :]
            problem = path_syntax_problem(rel)
            if problem:
                errors.append(f"{label}: owner: {problem}")
            else:
                paths.append(rel)
        else:
            errors.append(f"{label}: owner must be {UNKNOWN!r} or '{OWNER_DOX_PREFIX}<path>'")
    lane = entry.get("ci_lane")
    if lane == UNKNOWN:
        return paths
    if not isinstance(lane, list) or not lane:
        errors.append(f"{label}: ci_lane must be {UNKNOWN!r} or a non-empty list of workflow paths")
        return paths
    for item in lane:
        problem = path_syntax_problem(item)
        if problem:
            errors.append(f"{label}: ci_lane: {problem}")
        else:
            paths.append(item)
    return paths


def _check_entry(
    root: str,
    baseline: Baseline | None,
    manifest: dict,
    entry: object,
    covered: list[str],
    errors: list[str],
) -> str | None:
    if not isinstance(entry, dict):
        errors.append("entry must be an object")
        return None
    entry_id = entry.get("id")
    label = f"entry {entry_id if isinstance(entry_id, str) else '<no id>'}"
    for field in ENTRY_FIELDS:
        if field in ("owner", "ci_lane"):
            continue
        if not _is_str(entry.get(field)):
            errors.append(f"{label}: missing or non-string required field {field}")
    area = entry.get("area")
    if covered and _is_str(area) and area not in covered:
        errors.append(f"{label}: area {area!r} not in coverage.covered_areas")
    presence = entry.get("presence")
    if not _in(presence, PRESENCE):
        errors.append(f"{label}: unknown presence {presence!r}")
    if not _in(entry.get("source_presence"), SOURCE_PRESENCE):
        errors.append(f"{label}: unknown source_presence {entry.get('source_presence')!r}")
    if not _in(entry.get("canonical_status"), CANONICAL_STATUS):
        errors.append(f"{label}: unknown canonical_status {entry.get('canonical_status')!r}")
    evidence = entry.get("runtime_evidence")
    if not (isinstance(evidence, str) and RUNTIME_EVIDENCE_RE.fullmatch(evidence)):
        errors.append(f"{label}: unknown runtime_evidence {evidence!r}")

    paths = _check_path_list(label, entry, "paths", errors)
    tests = _check_path_list(label, entry, "tests", errors)
    entrypoints = _check_path_list(label, entry, "entrypoints", errors)
    aux_paths = _owner_and_lane_paths(label, entry, errors)
    any_paths = bool(entry.get("paths") or entry.get("tests") or entry.get("entrypoints"))

    if presence == "on-main":
        if not paths:
            errors.append(f"{label}: on-main entry requires at least one valid path")
        if entry.get("source_presence") != "yes":
            errors.append(f"{label}: on-main entry requires source_presence 'yes'")
        if entry.get("verified_ref") != manifest.get("baseline_ref"):
            errors.append(f"{label}: on-main verified_ref must equal baseline_ref")
        _verify_main_paths(label, paths + tests + entrypoints + aux_paths, root, baseline, errors)
    elif presence == "branch-only":
        _check_branch_refs(label, entry, errors)
        if entry.get("source_presence") != "branch-only":
            errors.append(f"{label}: branch-only entry requires source_presence 'branch-only'")
        if any_paths:
            errors.append(f"{label}: branch-only entry must not record main-checkout paths")
        if "verified_ref" in entry:
            errors.append(f"{label}: branch-only evidence belongs in branch_refs[].head_sha, not verified_ref")
    elif presence == "external-not-inspected":
        if any_paths:
            errors.append(f"{label}: external-not-inspected entry must not record paths")
        if entry.get("source_presence") != "unknown":
            errors.append(f"{label}: external-not-inspected entry requires source_presence 'unknown'")
        if "verified_ref" in entry:
            errors.append(f"{label}: external-not-inspected entry must not carry verified_ref")

    if evidence == "tests-only" and not tests:
        errors.append(f"{label}: runtime_evidence 'tests-only' requires listed tests")
    if presence != "on-main" and evidence != "none":
        errors.append(f"{label}: only on-main entries may claim runtime_evidence above 'none'")
    return entry_id if isinstance(entry_id, str) else None


def validate_manifest(manifest: object, root: str) -> list[str]:
    """Return a list of error strings; empty means the manifest is valid."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest root must be an object"]
    covered = _check_header(manifest, errors)
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries must be a non-empty list")
        return errors
    baseline: Baseline | None = None
    if any(isinstance(e, dict) and e.get("presence") == "on-main" for e in entries):
        baseline = Baseline(root, str(manifest.get("baseline_ref", "")))
        if baseline.error:
            errors.append(baseline.error)
    seen: set[str] = set()
    areas_with_entries: set[str] = set()
    for entry in entries:
        entry_id = _check_entry(root, baseline, manifest, entry, covered, errors)
        if entry_id is not None:
            if entry_id in seen:
                errors.append(f"duplicate entry id: {entry_id}")
            seen.add(entry_id)
        if isinstance(entry, dict) and _is_str(entry.get("area")):
            areas_with_entries.add(entry["area"])
    for area in covered:
        if area not in areas_with_entries:
            errors.append(f"covered area has no entry: {area}")
    return errors


def load_and_validate(root: str, manifest_rel: str = DEFAULT_MANIFEST) -> list[str]:
    path = os.path.join(root, manifest_rel)
    if not os.path.isfile(path):
        return [f"manifest not found: {manifest_rel}"]
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]
    return validate_manifest(manifest, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=REPO_ROOT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="repo-relative manifest path")
    args = parser.parse_args(argv)
    errors = load_and_validate(args.repo_root, args.manifest)
    if errors:
        print("Release-surface manifest validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Release-surface manifest validation passed (coverage: PARTIAL).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
