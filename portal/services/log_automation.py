import logging
import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.orchestration import OrchestrationRun
from .auditable_trails import auditable_trails

logger = logging.getLogger(__name__)

class DailyLogAutomationService:
    """
    Automated daily collection and verification of zero-trust inter-agent communication logs.
    """
    async def collect_and_verify_daily_logs(self, session: AsyncSession, tenant_id: str) -> Dict[str, Any]:
        """Collects all logs from the last 24 hours and verifies their integrity."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        
        # 1. Fetch runs from the last 24 hours
        stmt = select(OrchestrationRun).where(
            OrchestrationRun.tenant_id == tenant_id,
            OrchestrationRun.created_at >= yesterday
        )
        res = await session.execute(stmt)
        runs = res.scalars().all()
        
        results = {
            "tenant_id": tenant_id,
            "period_start": yesterday.isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
            "total_runs": len(runs),
            "verified_runs": 0,
            "failed_verifications": [],
            "status": "HEALTHY"
        }
        
        # 2. Verify each run's audit trail
        for run in runs:
            trail = await auditable_trails.generate_execution_trail(session, str(run.id), tenant_id)
            is_valid = await auditable_trails.verify_trail_integrity(trail)
            
            if is_valid:
                results["verified_runs"] += 1
            else:
                results["failed_verifications"].append(str(run.id))
                results["status"] = "COMPROMISED"
        
        logger.info(f"[LOG_AUTOMATION] Daily verification complete for tenant {tenant_id}. Status: {results['status']}")
        return results

# Global instance
log_automation = DailyLogAutomationService()
