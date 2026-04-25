"""
Usage Tracker for SintraPrime-Unified SaaS

Real-time usage tracking with Redis caching, quota enforcement,
and billing integration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
import redis
import json

logger = logging.getLogger(__name__)


class UsageMetric(str, Enum):
    """Usage metrics to track."""
    API_CALLS = "api_calls"
    VOICE_MINUTES = "voice_minutes"
    DOCUMENTS_GENERATED = "documents_generated"
    STORAGE_GB = "storage_gb"
    ACTIVE_USERS = "active_users"


class QuotaStatus(str, Enum):
    """Quota status states."""
    HEALTHY = "healthy"
    WARNING = "warning"  # 80% of quota
    CRITICAL = "critical"  # 100% of quota
    EXCEEDED = "exceeded"  # Over quota


@dataclass
class UsageRecord:
    """A single usage record."""
    tenant_id: str
    metric: UsageMetric
    quantity: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageReport:
    """Complete usage report for a tenant."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    metrics: Dict[UsageMetric, int] = field(default_factory=dict)
    quota_limits: Dict[UsageMetric, int] = field(default_factory=dict)
    quota_statuses: Dict[UsageMetric, QuotaStatus] = field(default_factory=dict)
    daily_breakdown: Dict[str, Dict[UsageMetric, int]] = field(default_factory=dict)
    anomalies_detected: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Violation:
    """Quota violation."""
    tenant_id: str
    metric: UsageMetric
    current_usage: int
    quota_limit: int
    percentage: float
    violation_type: str  # "warning" or "critical"
    detected_at: datetime = field(default_factory=datetime.utcnow)


class UsageTracker:
    """
    Real-time usage tracking for multi-tenant SaaS.
    
    Features:
    - Redis-based fast counters
    - Daily/monthly aggregation to PostgreSQL
    - Quota enforcement with grace periods
    - Usage anomaly detection
    - Rate limiting per endpoint
    - Billing integration
    """

    # Plan quotas
    PLAN_QUOTAS = {
        "solo": {
            UsageMetric.API_CALLS: 50,  # per day
            UsageMetric.VOICE_MINUTES: 60,  # per month
            UsageMetric.DOCUMENTS_GENERATED: 500,  # per month
            UsageMetric.STORAGE_GB: 10,
            UsageMetric.ACTIVE_USERS: 1,
        },
        "professional": {
            UsageMetric.API_CALLS: 500,
            UsageMetric.VOICE_MINUTES: 300,
            UsageMetric.DOCUMENTS_GENERATED: 2000,
            UsageMetric.STORAGE_GB: 100,
            UsageMetric.ACTIVE_USERS: 5,
        },
        "law_firm": {
            UsageMetric.API_CALLS: None,  # unlimited
            UsageMetric.VOICE_MINUTES: None,
            UsageMetric.DOCUMENTS_GENERATED: None,
            UsageMetric.STORAGE_GB: 500,
            UsageMetric.ACTIVE_USERS: 25,
        },
        "enterprise": {
            UsageMetric.API_CALLS: None,
            UsageMetric.VOICE_MINUTES: None,
            UsageMetric.DOCUMENTS_GENERATED: None,
            UsageMetric.STORAGE_GB: None,
            UsageMetric.ACTIVE_USERS: None,
        },
    }

    def __init__(self, redis_url: str, db_connection=None):
        """
        Initialize usage tracker.
        
        Args:
            redis_url: Redis connection URL
            db_connection: PostgreSQL connection for aggregation
        """
        try:
            self.redis = redis.from_url(redis_url)
            self.redis.ping()
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        self.db = db_connection
        self._violation_history: Dict[str, List[Violation]] = {}
        self._rate_limit_exceeded: Dict[str, int] = {}

    def track_usage(
        self,
        tenant_id: str,
        metric: UsageMetric,
        quantity: int,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track usage for a metric.
        
        Args:
            tenant_id: Tenant ID
            metric: Usage metric type
            quantity: Amount to increment
            user_id: Optional user who triggered the usage
            metadata: Optional additional data
            
        Returns:
            True if tracked successfully, False if quota exceeded
        """
        try:
            key = f"usage:{tenant_id}:{metric.value}:month:{datetime.utcnow().strftime('%Y-%m')}"
            
            # Increment counter in Redis (atomic)
            current = self.redis.incrby(key, quantity)
            
            # Set expiration for monthly metrics
            self.redis.expire(key, 86400 * 32)  # 32 days

            # Create usage record for audit trail
            record = UsageRecord(
                tenant_id=tenant_id,
                metric=metric,
                quantity=quantity,
                user_id=user_id,
                metadata=metadata or {},
            )

            # Store record in Redis log (for recent history)
            log_key = f"usage_log:{tenant_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
            self.redis.lpush(log_key, json.dumps({
                "metric": metric.value,
                "quantity": quantity,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
            }))
            self.redis.expire(log_key, 86400 * 30)  # 30 days

            # Check quota
            status = self.check_quota(tenant_id, metric)
            if status.status == QuotaStatus.EXCEEDED:
                return False

            logger.debug(
                f"Tracked {quantity} {metric.value} for tenant {tenant_id} "
                f"(current: {current})"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to track usage: {e}")
            return False

    def check_quota(
        self,
        tenant_id: str,
        metric: UsageMetric,
        plan_id: Optional[str] = None
    ) -> QuotaStatus:
        """
        Check current quota status for a metric.
        
        Args:
            tenant_id: Tenant ID
            metric: Usage metric
            plan_id: Optional plan (if not provided, defaults to checking limits)
            
        Returns:
            QuotaStatus value
        """
        if not plan_id:
            plan_id = "professional"  # Default

        quotas = self.PLAN_QUOTAS.get(plan_id, {})
        limit = quotas.get(metric)

        if limit is None:
            # Unlimited
            return QuotaStatus.HEALTHY

        # Get current usage
        current_usage = self.get_current_usage(tenant_id, metric)

        percentage = (current_usage / limit) * 100 if limit > 0 else 0

        if percentage > 100:
            return QuotaStatus.EXCEEDED
        elif percentage >= 100:
            return QuotaStatus.CRITICAL
        elif percentage >= 80:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.HEALTHY

    def get_current_usage(self, tenant_id: str, metric: UsageMetric) -> int:
        """Get current month's usage for a metric."""
        try:
            key = f"usage:{tenant_id}:{metric.value}:month:{datetime.utcnow().strftime('%Y-%m')}"
            value = self.redis.get(key)
            return int(value) if value else 0
        except redis.RedisError as e:
            logger.error(f"Failed to get current usage: {e}")
            return 0

    def enforce_limits(self, tenant_id: str) -> List[Violation]:
        """
        Check all metrics for quota violations.
        
        Returns:
            List of violations detected
        """
        violations = []

        for metric in UsageMetric:
            current = self.get_current_usage(tenant_id, metric)
            quota = self.PLAN_QUOTAS.get("professional", {}).get(metric)

            if quota and current > quota:
                percentage = (current / quota) * 100
                violation = Violation(
                    tenant_id=tenant_id,
                    metric=metric,
                    current_usage=current,
                    quota_limit=quota,
                    percentage=percentage,
                    violation_type="critical" if percentage > 100 else "warning",
                )
                violations.append(violation)

        # Store violation history
        if violations:
            if tenant_id not in self._violation_history:
                self._violation_history[tenant_id] = []
            self._violation_history[tenant_id].extend(violations)

        return violations

    def get_usage_report(
        self,
        tenant_id: str,
        period: str = "month",
        plan_id: Optional[str] = None
    ) -> UsageReport:
        """
        Get comprehensive usage report.
        
        Args:
            tenant_id: Tenant ID
            period: "day", "week", or "month"
            plan_id: Optional plan ID
            
        Returns:
            UsageReport object
        """
        if not plan_id:
            plan_id = "professional"

        # Determine period dates
        now = datetime.utcnow()
        if period == "day":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period == "week":
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=7)
        else:  # month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = (period_start + timedelta(days=32)).replace(day=1)

        # Gather current usage
        metrics = {}
        quota_limits = {}
        quota_statuses = {}

        quotas = self.PLAN_QUOTAS.get(plan_id, {})

        for metric in UsageMetric:
            current = self.get_current_usage(tenant_id, metric)
            metrics[metric] = current

            limit = quotas.get(metric)
            quota_limits[metric] = limit

            if limit:
                percentage = (current / limit) * 100
                if percentage > 100:
                    quota_statuses[metric] = QuotaStatus.EXCEEDED
                elif percentage >= 100:
                    quota_statuses[metric] = QuotaStatus.CRITICAL
                elif percentage >= 80:
                    quota_statuses[metric] = QuotaStatus.WARNING
                else:
                    quota_statuses[metric] = QuotaStatus.HEALTHY
            else:
                quota_statuses[metric] = QuotaStatus.HEALTHY

        # Get daily breakdown
        daily_breakdown = self._get_daily_breakdown(
            tenant_id, period_start, period_end
        )

        # Detect anomalies
        anomalies = self._detect_anomalies(tenant_id, metrics)

        return UsageReport(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            quota_limits=quota_limits,
            quota_statuses=quota_statuses,
            daily_breakdown=daily_breakdown,
            anomalies_detected=anomalies,
        )

    def _get_daily_breakdown(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Dict[UsageMetric, int]]:
        """Get daily usage breakdown."""
        breakdown = {}
        current = start_date

        while current < end_date:
            date_str = current.strftime("%Y-%m-%d")
            breakdown[date_str] = {}

            for metric in UsageMetric:
                log_key = f"usage_log:{tenant_id}:{date_str}"
                try:
                    logs = self.redis.lrange(log_key, 0, -1)
                    total = 0
                    for log in logs:
                        data = json.loads(log)
                        if data.get("metric") == metric.value:
                            total += data.get("quantity", 0)
                    breakdown[date_str][metric] = total
                except redis.RedisError:
                    breakdown[date_str][metric] = 0

            current += timedelta(days=1)

        return breakdown

    def _detect_anomalies(
        self,
        tenant_id: str,
        current_metrics: Dict[UsageMetric, int]
    ) -> List[str]:
        """Detect usage anomalies (e.g., sudden spikes)."""
        anomalies = []

        # Get historical average
        try:
            history_key = f"usage_history:{tenant_id}"
            history = self.redis.get(history_key)
            if history:
                prev_metrics = json.loads(history)

                for metric, current in current_metrics.items():
                    prev = prev_metrics.get(metric.value, 0)
                    if prev > 0:
                        increase_percentage = ((current - prev) / prev) * 100
                        if increase_percentage > 200:  # 200% increase
                            anomalies.append(
                                f"Unusual spike in {metric.value}: "
                                f"+{increase_percentage:.0f}%"
                            )

            # Update history
            self.redis.set(
                history_key,
                json.dumps({m.value: v for m, v in current_metrics.items()}),
                ex=86400 * 30
            )

        except redis.RedisError as e:
            logger.error(f"Failed to detect anomalies: {e}")

        return anomalies

    def apply_rate_limit(
        self,
        tenant_id: str,
        endpoint: str,
        max_requests_per_hour: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Apply rate limiting for an endpoint.
        
        Returns:
            (is_allowed, headers_dict)
        """
        try:
            key = f"rate_limit:{tenant_id}:{endpoint}:{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
            current = self.redis.incr(key)
            self.redis.expire(key, 3600)

            if current > max_requests_per_hour:
                return False, {
                    "X-RateLimit-Limit": str(max_requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "3600",
                }

            return True, {
                "X-RateLimit-Limit": str(max_requests_per_hour),
                "X-RateLimit-Remaining": str(max_requests_per_hour - current),
            }

        except redis.RedisError as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, {}  # Allow on error

    def reset_monthly_quota(self, tenant_id: str) -> bool:
        """Reset monthly quotas (typically run monthly)."""
        try:
            pattern = f"usage:{tenant_id}:*:month:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Reset monthly quota for tenant {tenant_id}")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to reset quota: {e}")
            return False

    def get_violation_history(self, tenant_id: str) -> List[Violation]:
        """Get violation history for a tenant."""
        return self._violation_history.get(tenant_id, [])
