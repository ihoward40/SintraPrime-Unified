"""Administrative Mission Control permission provisioning utility.

Default mode performs drift verification only. Use --dry-run to preview the
exact reconciliation plan, or --apply to reconcile the canonical permission
manifest into the database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portal.database import AsyncSessionLocal
from portal.services.permission_provisioning import (
    inspect_permission_manifest,
    plan_permission_manifest,
    sync_permission_manifest,
)


async def _run(mode: str) -> None:
    async with AsyncSessionLocal() as session:
        if mode == "apply":
            try:
                report = await sync_permission_manifest(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        elif mode == "dry-run":
            report = await plan_permission_manifest(session)
        else:
            report = await inspect_permission_manifest(session)
        print(json.dumps(asdict(report), default=str, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or reconcile Mission Control permissions")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Apply canonical permission reconciliation")
    group.add_argument("--dry-run", action="store_true", help="Preview canonical permission reconciliation")
    args = parser.parse_args()
    mode = "apply" if args.apply else "dry-run" if args.dry_run else "verify"
    asyncio.run(_run(mode))


if __name__ == "__main__":
    main()
