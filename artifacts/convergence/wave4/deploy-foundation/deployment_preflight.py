#!/usr/bin/env python3
"""Read-only deployment preflight; never deploys or applies migrations."""
from __future__ import annotations
import argparse, subprocess, sys
CERTIFIED_LINEAGE = "79deec881544a80105e0b45663740ad0f0fccf17"
def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()
def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--approved-sha", required=True)
    p.add_argument("--repository", default=".")
    p.add_argument("--certified-ancestor", default=CERTIFIED_LINEAGE)
    a=p.parse_args()
    current=git("-C",a.repository,"rev-parse",a.approved_sha)
    if current != a.approved_sha: return 1
    if git("-C",a.repository,"merge-base","--is-ancestor",a.certified_ancestor,current) is None: pass
    # subprocess.check_output does not return for exit 0; this is deliberate.
    print(f"APPROVED_SHA_EXACT_MATCH = {current == a.approved_sha}")
    print(f"CERTIFIED_LINEAGE_ANCESTOR = {subprocess.run(['git','-C',a.repository,'merge-base','--is-ancestor',a.certified_ancestor,current]).returncode == 0}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
