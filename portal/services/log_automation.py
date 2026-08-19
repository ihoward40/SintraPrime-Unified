import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationRun
from .auditable_trails import auditable_trails

logger = logging.getLogger(__name__)


class DailyLogAutomationService:
    """Collect and verify zero-trust inter-agent communication logs each day."""

    async def collect_and_verify_daily_logs(
        self,
        session: AsyncSession,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Collect logs from the last 24 hours and verify their integrity."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        stmt = select(OrchestrationRun).where(
            OrchestrationRun.tenant_id == tenant_id,
            OrchestrationRun.created_at >= yesterday,
        )
        res = await session.execute(stmt)
        runs = res.scalars().all()

        results: dict[str, Any] = {
            "tenant_id": tenant_id,
            "period_start": yesterday.isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
            "total_runs": len(runs),
            "verified_runs": 0,
            "failed_verifications": [],
            "status": "HEALTHY",
        }

        for run in runs:
            trail = await auditable_trails.generate_execution_trail(
                session,
                str(run.id),
                tenant_id,
            )
            is_valid = await auditable_trails.verify_trail_integrity(trail)
            if is_valid:
                results["verified_runs"] += 1
            else:
                results["failed_verifications"].append(str(run.id))
                results["status"] = "COMPROMISED"

        logger.info(
            "[LOG_AUTOMATION] Daily verification complete for tenant %s. Status: %s",
            tenant_id,
            results["status"],
        )
        return results


log_automation = DailyLogAutomationService()
