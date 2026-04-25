from __future__ import annotations

"""
Multi-Channel Docket Alert System

Intelligent alerting with email, SMS, Slack, webhooks, and digest modes.
Respects quiet hours, prioritizes alerts, and tracks acknowledgment.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, date
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Set
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PUSH = "push"


class AlertType(Enum):
    """Types of docket alerts"""
    NEW_FILING = "new_filing"
    HEARING_SCHEDULED = "hearing_scheduled"
    JUDGMENT_ENTERED = "judgment_entered"
    DEADLINE_APPROACHING = "deadline_approaching"
    APPEAL_FILED = "appeal_filed"
    SETTLEMENT = "settlement"
    EMERGENCY_MOTION = "emergency_motion"
    MOTION_FILED = "motion_filed"
    ORDER_ISSUED = "order_issued"


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AlertRule:
    """Configuration for alert rules"""
    rule_id: str
    case_id: Optional[str]  # None for global rules
    alert_type: AlertType
    enabled: bool = True
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.EMAIL])
    priority: AlertPriority = AlertPriority.MEDIUM
    suppress_quiet_hours: bool = False  # Allow critical alerts during quiet hours
    conditions: Dict[str, Any] = field(default_factory=dict)  # Custom conditions
    created_date: datetime = field(default_factory=datetime.now)
    
    def matches(self, alert_type: AlertType, case_id: str, context: Dict[str, Any]) -> bool:
        """Check if rule matches alert"""
        if not self.enabled:
            return False
        
        # Type must match
        if self.alert_type != alert_type:
            return False
        
        # Case ID must match if specified
        if self.case_id and self.case_id != case_id:
            return False
        
        # Check custom conditions
        for key, value in self.conditions.items():
            if key not in context or context[key] != value:
                return False
        
        return True


@dataclass
class Alert:
    """Individual alert instance"""
    alert_id: str
    case_id: str
    case_name: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    description: str
    created_date: datetime = field(default_factory=datetime.now)
    sent_date: Optional[datetime] = None
    acknowledged_date: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    channels_sent: List[AlertChannel] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    is_acknowledged: bool = False


@dataclass
class AlertDigest:
    """Digest of non-urgent alerts"""
    digest_id: str
    date_created: date
    alerts: List[Alert] = field(default_factory=list)
    recipient: str = ""
    sent_date: Optional[datetime] = None


class AlertSystem:
    """
    Multi-channel alert system for docket monitoring.
    
    Manages alert rules, delivery channels, quiet hours, digest mode,
    and acknowledgment tracking.
    """

    def __init__(self):
        """Initialize alert system"""
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_history: List[Alert] = []
        self.pending_alerts: List[Alert] = []
        self.acknowledged_alerts: Set[str] = set()
        
        # Quiet hours configuration
        self.quiet_hours_enabled = True
        self.quiet_hours_start = time(22, 0)  # 10 PM
        self.quiet_hours_end = time(8, 0)     # 8 AM
        
        # Digest configuration
        self.digest_enabled = True
        self.digest_time = time(9, 0)  # 9 AM
        self.pending_digest: List[Alert] = []
        
        # Channel handlers (to be registered)
        self.channel_handlers: Dict[AlertChannel, Callable] = {}
        
        # Default rules
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Set up default alert rules"""
        # Critical alerts always go through
        critical_rule = AlertRule(
            rule_id=str(uuid.uuid4()),
            case_id=None,
            alert_type=AlertType.EMERGENCY_MOTION,
            channels=[AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.SLACK],
            priority=AlertPriority.CRITICAL,
            suppress_quiet_hours=True
        )
        self.alert_rules[critical_rule.rule_id] = critical_rule

    def create_alert_rule(
        self,
        case_id: Optional[str],
        alert_type: AlertType,
        channels: List[AlertChannel],
        priority: AlertPriority = AlertPriority.MEDIUM,
        suppress_quiet_hours: bool = False,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create alert rule.
        
        Args:
            case_id: Case ID or None for global rule
            alert_type: Type of alert
            channels: Delivery channels
            priority: Alert priority
            suppress_quiet_hours: Allow during quiet hours
            conditions: Custom match conditions
            
        Returns:
            Rule ID
        """
        rule_id = str(uuid.uuid4())
        rule = AlertRule(
            rule_id=rule_id,
            case_id=case_id,
            alert_type=alert_type,
            channels=channels,
            priority=priority,
            suppress_quiet_hours=suppress_quiet_hours,
            conditions=conditions or {}
        )
        
        self.alert_rules[rule_id] = rule
        logger.info(f"Created alert rule {rule_id} for {alert_type}")
        return rule_id

    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Deleted alert rule {rule_id}")
            return True
        return False

    def send_alert(
        self,
        case_id: str,
        case_name: str,
        alert_type: AlertType,
        title: str,
        description: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Send alert based on matching rules.
        
        Args:
            case_id: Case identifier
            case_name: Case name for display
            alert_type: Type of alert
            title: Alert title
            description: Alert description
            priority: Priority level
            details: Additional details
            
        Returns:
            Alert object
        """
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            case_id=case_id,
            case_name=case_name,
            alert_type=alert_type,
            priority=priority,
            title=title,
            description=description,
            details=details or {}
        )
        
        # Find matching rules
        matching_rules = [
            rule for rule in self.alert_rules.values()
            if rule.matches(alert_type, case_id, details or {})
        ]
        
        # Always record alert in history
        self.alert_history.append(alert)
        
        # Check quiet hours
        if self._is_quiet_hours() and not any(r.suppress_quiet_hours for r in matching_rules):
            if priority != AlertPriority.CRITICAL:
                logger.info(f"Alert {alert.alert_id} deferred to digest (quiet hours)")
                self.pending_digest.append(alert)
                return alert
        
        # Send through channels
        if matching_rules:
            for rule in matching_rules:
                self._dispatch_alert(alert, rule.channels)
        else:
            # Send through default channel if no rules match
            self._dispatch_alert(alert, [AlertChannel.EMAIL])
        
        alert.sent_date = datetime.now()
        
        logger.info(f"Sent alert {alert.alert_id} ({alert_type}) for case {case_id}")
        return alert

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """Acknowledge alert to suppress further notifications"""
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                alert.is_acknowledged = True
                alert.acknowledged_date = datetime.now()
                alert.acknowledged_by = acknowledged_by
                self.acknowledged_alerts.add(alert_id)
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        return False

    def get_alert_history(
        self,
        case_id: str,
        days: int = 30
    ) -> List[Alert]:
        """
        Get alert history for case.
        
        Args:
            case_id: Case identifier
            days: Number of days of history
            
        Returns:
            List of alerts
        """
        cutoff = datetime.now() - timedelta(days=days)
        return [
            a for a in self.alert_history
            if a.case_id == case_id and a.created_date >= cutoff
        ]

    def get_pending_alerts(self) -> List[Alert]:
        """Get pending (unsent) alerts"""
        return [a for a in self.alert_history if not a.sent_date]

    def send_digest(self, recipient: str) -> Optional[AlertDigest]:
        """
        Send digest of pending alerts.
        
        Args:
            recipient: Email or contact for digest
            
        Returns:
            Digest object or None
        """
        if not self.pending_digest:
            return None
        
        from datetime import date
        
        digest = AlertDigest(
            digest_id=str(uuid.uuid4()),
            date=date.today(),
            alerts=self.pending_digest.copy(),
            recipient=recipient
        )
        
        # Send digest through email channel
        if AlertChannel.EMAIL in self.channel_handlers:
            try:
                self.channel_handlers[AlertChannel.EMAIL](digest)
                digest.sent_date = datetime.now()
                logger.info(f"Sent digest {digest.digest_id} to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send digest: {e}")
                return None
        
        # Clear pending digest
        self.pending_digest = []
        
        return digest

    def register_channel_handler(
        self,
        channel: AlertChannel,
        handler: Callable[[Alert], None]
    ) -> None:
        """
        Register handler for alert channel.
        
        Args:
            channel: Alert channel
            handler: Function to handle alert delivery
        """
        self.channel_handlers[channel] = handler
        logger.info(f"Registered handler for {channel}")

    def _dispatch_alert(
        self,
        alert: Alert,
        channels: List[AlertChannel]
    ) -> None:
        """Dispatch alert to specified channels"""
        for channel in channels:
            if channel in self.channel_handlers:
                try:
                    self.channel_handlers[channel](alert)
                    alert.channels_sent.append(channel)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
            else:
                logger.warning(f"No handler registered for channel {channel}")

    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours"""
        if not self.quiet_hours_enabled:
            return False
        
        now = datetime.now().time()
        
        if self.quiet_hours_start < self.quiet_hours_end:
            # Normal case: e.g., 10 AM to 5 PM
            return self.quiet_hours_start <= now < self.quiet_hours_end
        else:
            # Wraps midnight: e.g., 10 PM to 8 AM
            return now >= self.quiet_hours_start or now < self.quiet_hours_end

    def set_quiet_hours(
        self,
        start: time,
        end: time,
        enabled: bool = True
    ) -> None:
        """Configure quiet hours"""
        self.quiet_hours_enabled = enabled
        self.quiet_hours_start = start
        self.quiet_hours_end = end
        logger.info(f"Quiet hours set: {start} - {end}")

    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total = len(self.alert_history)
        acknowledged = len(self.acknowledged_alerts)
        by_type = {}
        
        for alert in self.alert_history:
            alert_type = alert.alert_type.value
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
        
        return {
            "total_alerts": total,
            "acknowledged": acknowledged,
            "pending": len(self.pending_alerts),
            "by_type": by_type,
            "rules_count": len(self.alert_rules)
        }

    def clear_history(self, days_older_than: int = 90) -> int:
        """Clear alert history older than N days"""
        cutoff = datetime.now() - timedelta(days=days_older_than)
        before = len(self.alert_history)
        
        self.alert_history = [
            a for a in self.alert_history
            if a.created_date >= cutoff
        ]
        
        removed = before - len(self.alert_history)
        logger.info(f"Cleared {removed} alerts older than {days_older_than} days")
        return removed
