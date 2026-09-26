#!/usr/bin/env python
"""SP-CI-DEPENDENCY-COMPLETENESS-001 minimum viable certification.

Proves that the Python environment used for build/test contains the dependencies
implicated by the 2026-09-26 CI incidents, resolvable purely from the
repository-declared dependency authorities (requirements.txt / pyproject.toml).

Run inside a freshly installed environment:
    pip install -r requirements.txt
    python scripts/ci/dependency_completeness_check.py

Exit 0 = every declared-critical dependency imports and reports a version.
Admission criteria (SP-AGENT0-CI-BASELINE-RECOVERY-001 Gate 8):
  - greenlet importable (SQLAlchemy asyncio/concurrency runtime)
  - sqlalchemy in the declared compatible series (2.0.x, <2.1)
  - psycopg2 importable (declared postgres driver; NOT psycopg v3)
  - pytest-timeout importable (certify.py --timeout contract)
  - portal.main importable (portal dependency surface complete)
"""
from __future__ import annotations

import sys
from pathlib import Path

# portal/ is a repo package (not pip-installed); make the repo root importable.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    failures: list[str] = []

    try:
        import greenlet
        print("greenlet: PASS")
    except Exception as exc:  # pragma: no cover
        failures.append(f"greenlet: {exc}")

    try:
        import sqlalchemy

        version = tuple(int(p) for p in sqlalchemy.__version__.split(".")[:2])
        print(f"sqlalchemy: PASS ({sqlalchemy.__version__})")
        if not ((2, 0) <= version < (2, 1)):
            failures.append(
                f"sqlalchemy {sqlalchemy.__version__} outside declared 2.0 series "
                "(>=2.0.0,<2.1); plain postgresql:// URLs resolve to undeclared psycopg v3"
            )
    except Exception as exc:  # pragma: no cover
        failures.append(f"sqlalchemy: {exc}")

    try:
        import psycopg2

        print("psycopg2: PASS")
    except Exception as exc:  # pragma: no cover
        failures.append(f"psycopg2: {exc}")

    try:
        import pytest_timeout

        print("pytest-timeout: PASS")
    except Exception as exc:  # pragma: no cover
        failures.append(
            f"pytest-timeout: {exc} (scripts/certify.py passes --timeout; undeclared "
            "plugin makes every certify lane exit 4)"
        )

    try:
        import portal.main

        print("portal.main: PASS")
    except Exception as exc:  # pragma: no cover
        failures.append(f"portal.main: {exc}")

    if failures:
        print("\nDEPENDENCY COMPLETENESS: FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("\nDEPENDENCY COMPLETENESS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
