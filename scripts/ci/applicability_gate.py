#!/usr/bin/env python3
"""Fail-closed applicability proof for always-run CI lanes.

The gate has exactly three states:
- applicable: the scoped files changed; the substantive lane must run.
- not_applicable_with_proof: the diff is known and no scoped file changed.
- unknown: the event or diff cannot be established; exit non-zero.

This helper never treats an unknown applicability decision as success.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import PurePosixPath


def _event() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        raise RuntimeError("GITHUB_EVENT_PATH is unavailable")
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise RuntimeError("GitHub event is not an object")
    return value


def _subjects(event: dict) -> tuple[str, str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    if event_name == "pull_request":
        pull = event.get("pull_request")
        if not isinstance(pull, dict):
            raise RuntimeError("pull_request event payload is incomplete")
        base = pull.get("base", {}).get("sha")
        head = pull.get("head", {}).get("sha")
    elif event_name == "push":
        base = event.get("before")
        head = event.get("after") or os.environ.get("GITHUB_SHA")
    else:
        raise RuntimeError(f"unsupported event for applicability proof: {event_name!r}")
    if not isinstance(base, str) or not base or set(base) == {"0"}:
        raise RuntimeError("event did not provide a usable base commit")
    if not isinstance(head, str) or not head:
        raise RuntimeError("event did not provide a usable head commit")
    return base, head


def _changed_files(base: str, head: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"cannot establish the subject diff: {detail}")
    return sorted({line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()})


def _matches(path: str, pattern: str) -> bool:
    normalized = pattern.strip().lstrip("./")
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, normalized) or PurePosixPath(path).match(normalized)


def _write_outputs(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", required=True)
    parser.add_argument("--paths", nargs="+", required=True)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args()

    receipt = {"area": args.area, "patterns": args.paths}
    try:
        event = _event()
        base, head = _subjects(event)
        changed = _changed_files(base, head)
        matched = [path for path in changed if any(_matches(path, pattern) for pattern in args.paths)]
        state = "applicable" if matched else "not_applicable_with_proof"
        proof = (
            f"{state}: diff {base[:12]}...{head[:12]}; "
            f"matched={len(matched)}; changed={len(changed)}"
        )
        receipt.update(
            {
                "state": state,
                "base": base,
                "head": head,
                "changed_files": changed,
                "matched_files": matched,
                "proof": proof,
            }
        )
        _write_outputs({"state": state, "proof": proof})
        if args.receipt:
            with open(args.receipt, "w", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2)
        print(json.dumps(receipt, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        receipt.update({"state": "unknown", "proof": str(exc)})
        _write_outputs({"state": "unknown", "proof": str(exc)})
        if args.receipt:
            with open(args.receipt, "w", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2)
        print(json.dumps(receipt, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
