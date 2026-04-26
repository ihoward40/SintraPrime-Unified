"""
Phase 15D — Real-time Alerts Engine
Sends Slack and Discord notifications for hot leads, payment failures,
deadline reminders, and system health events.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


class AlertChannel(str, Enum):
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


class AlertType(str, Enum):
    HOT_LEAD = "hot_lead"
    PAYMENT_FAILURE = "payment_failure"
    PAYMENT_SUCCESS = "payment_success"
    DEADLINE_REMINDER = "deadline_reminder"
    SYSTEM_ERROR = "system_error"
    DEMO_BOOKED = "demo_booked"
    CONTRACT_SIGNED = "contract_signed"
    NEW_REFERRAL = "new_referral"
    CHURN_RISK = "churn_risk"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AlertRule:
    rule_id: str
    name: str
    alert_type: AlertType
    channels: List[AlertChannel]
    severity: AlertSeverity = AlertSeverity.INFO
    enabled: bool = True
    cooldown_minutes: int = 0  # Minimum minutes between repeated alerts
    conditions: Dict[str, Any] = field(default_factory=dict)
    template: str = ""
    last_triggered_at: Optional[datetime] = None

    def is_on_cooldown(self) -> bool:
        if self.cooldown_minutes == 0 or self.last_triggered_at is None:
            return False
        elapsed = (datetime.utcnow() - self.last_triggered_at).total_seconds() / 60
        return elapsed < self.cooldown_minutes

    def mark_triggered(self) -> None:
        self.last_triggered_at = datetime.utcnow()


@dataclass
class Alert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    channels: List[AlertChannel] = field(default_factory=list)
    sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    rule_id: Optional[str] = None

    def to_slack_payload(self) -> Dict[str, Any]:
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ffcc00",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.SUCCESS: "#2eb886",
        }
        emoji_map = {
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.CRITICAL: ":rotating_light:",
            AlertSeverity.SUCCESS: ":white_check_mark:",
        }
        return {
            "attachments": [
                {
                    "color": color_map.get(self.severity, "#36a64f"),
                    "title": f"{emoji_map.get(self.severity, '')} {self.title}",
                    "text": self.message,
                    "footer": f"SintraPrime Alerts | {self.alert_type.value}",
                    "ts": int(self.created_at.timestamp()),
                    "fields": [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in self.metadata.items()
                    ],
                }
            ]
        }

    def to_discord_payload(self) -> Dict[str, Any]:
        color_map = {
            AlertSeverity.INFO: 0x36A64F,
            AlertSeverity.WARNING: 0xFFCC00,
            AlertSeverity.CRITICAL: 0xFF0000,
            AlertSeverity.SUCCESS: 0x2EB886,
        }
        fields = [
            {"name": k, "value": str(v), "inline": True}
            for k, v in self.metadata.items()
        ]
        return {
            "embeds": [
                {
                    "title": self.title,
                    "description": self.message,
                    "color": color_map.get(self.severity, 0x36A64F),
                    "fields": fields,
                    "footer": {"text": f"SintraPrime | {self.alert_type.value}"},
                    "timestamp": self.created_at.isoformat(),
                }
            ]
        }


@dataclass
class AlertDeliveryResult:
    alert_id: str
    channel: AlertChannel
    success: bool
    response_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Channel adapters
# ---------------------------------------------------------------------------

class SlackAdapter:
    """Sends alerts to Slack via incoming webhooks."""

    def __init__(self, webhook_url: Optional[str] = None, http_client=None):
        self._webhook_url = webhook_url
        self._http = http_client  # requests.Session or mock

    def send(self, alert: Alert) -> AlertDeliveryResult:
        if not self._webhook_url:
            logger.warning("Slack adapter: no webhook URL — dry run")
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.SLACK,
                success=True, response_code=200,
            )
        payload = alert.to_slack_payload()
        try:
            if self._http:
                resp = self._http.post(self._webhook_url, json=payload)
                return AlertDeliveryResult(
                    alert_id=alert.alert_id, channel=AlertChannel.SLACK,
                    success=resp.status_code == 200,
                    response_code=resp.status_code,
                )
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.SLACK, success=True
            )
        except Exception as e:
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.SLACK,
                success=False, error=str(e),
            )


class DiscordAdapter:
    """Sends alerts to Discord via webhook."""

    def __init__(self, webhook_url: Optional[str] = None, http_client=None):
        self._webhook_url = webhook_url
        self._http = http_client

    def send(self, alert: Alert) -> AlertDeliveryResult:
        if not self._webhook_url:
            logger.warning("Discord adapter: no webhook URL — dry run")
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.DISCORD,
                success=True, response_code=204,
            )
        payload = alert.to_discord_payload()
        try:
            if self._http:
                resp = self._http.post(self._webhook_url, json=payload)
                return AlertDeliveryResult(
                    alert_id=alert.alert_id, channel=AlertChannel.DISCORD,
                    success=resp.status_code in (200, 204),
                    response_code=resp.status_code,
                )
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.DISCORD, success=True
            )
        except Exception as e:
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.DISCORD,
                success=False, error=str(e),
            )


class WebhookAdapter:
    """Generic HTTP webhook adapter."""

    def __init__(self, url: Optional[str] = None, http_client=None,
                 headers: Optional[Dict[str, str]] = None):
        self._url = url
        self._http = http_client
        self._headers = headers or {"Content-Type": "application/json"}

    def send(self, alert: Alert) -> AlertDeliveryResult:
        if not self._url:
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.WEBHOOK,
                success=True,
            )
        payload = {
            "alert_id": alert.alert_id,
            "type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "metadata": alert.metadata,
            "timestamp": alert.created_at.isoformat(),
        }
        try:
            if self._http:
                resp = self._http.post(self._url, json=payload, headers=self._headers)
                return AlertDeliveryResult(
                    alert_id=alert.alert_id, channel=AlertChannel.WEBHOOK,
                    success=resp.status_code < 400,
                    response_code=resp.status_code,
                )
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.WEBHOOK, success=True
            )
        except Exception as e:
            return AlertDeliveryResult(
                alert_id=alert.alert_id, channel=AlertChannel.WEBHOOK,
                success=False, error=str(e),
            )


# ---------------------------------------------------------------------------
# Template engine
# ---------------------------------------------------------------------------

ALERT_TEMPLATES: Dict[AlertType, str] = {
    AlertType.HOT_LEAD: (
        "🔥 Hot Lead Alert!\n"
        "**{lead_name}** ({practice_area}) just scored {score}/100.\n"
        "Phone: {phone} | Email: {email}\n"
        "Source: {source} | Respond within 5 minutes for best conversion."
    ),
    AlertType.PAYMENT_FAILURE: (
        "💳 Payment Failed\n"
        "Client: **{client_name}** | Amount: ${amount}\n"
        "Reason: {reason}\n"
        "Action: Retry or contact client immediately."
    ),
    AlertType.PAYMENT_SUCCESS: (
        "✅ Payment Received\n"
        "Client: **{client_name}** | Amount: ${amount}\n"
        "Invoice: {invoice_id}"
    ),
    AlertType.DEADLINE_REMINDER: (
        "⏰ Deadline Reminder\n"
        "Case: **{case_name}** | Client: {client_name}\n"
        "Deadline: {deadline} ({days_remaining} days remaining)\n"
        "Action required: {action}"
    ),
    AlertType.DEMO_BOOKED: (
        "📅 Demo Booked!\n"
        "**{lead_name}** booked a demo for {demo_time}.\n"
        "Practice area: {practice_area} | Source: {source}"
    ),
    AlertType.CONTRACT_SIGNED: (
        "📝 Contract Signed!\n"
        "**{client_name}** signed the {contract_type} agreement.\n"
        "Value: ${contract_value} | Date: {signed_date}"
    ),
    AlertType.NEW_REFERRAL: (
        "🤝 New CPA Referral\n"
        "Case: **{case_type}** for {client_name}\n"
        "Assigned to: {partner_name} | Fee: ${fee_amount}"
    ),
    AlertType.CHURN_RISK: (
        "⚠️ Churn Risk Detected\n"
        "Client: **{client_name}** | Last activity: {last_activity}\n"
        "Risk score: {risk_score}/100\n"
        "Suggested action: {action}"
    ),
    AlertType.SYSTEM_ERROR: (
        "🚨 System Error\n"
        "Component: **{component}**\n"
        "Error: {error_message}\n"
        "Time: {timestamp}"
    ),
}


def render_alert_message(alert_type: AlertType, data: Dict[str, Any]) -> str:
    template = ALERT_TEMPLATES.get(alert_type, "{message}")
    try:
        return template.format(**{k: v for k, v in data.items()})
    except KeyError:
        # Return template with unfilled placeholders replaced by "N/A"
        keys = re.findall(r"\{(\w+)\}", template)
        filled = {k: data.get(k, "N/A") for k in keys}
        return template.format(**filled)


# ---------------------------------------------------------------------------
# Deadline monitor
# ---------------------------------------------------------------------------

@dataclass
class Deadline:
    deadline_id: str
    case_name: str
    client_name: str
    due_date: datetime
    action: str
    reminder_days: List[int] = field(default_factory=lambda: [7, 3, 1])
    alerted_days: List[int] = field(default_factory=list)

    def days_remaining(self) -> int:
        return (self.due_date.date() - datetime.utcnow().date()).days

    def needs_alert(self) -> Optional[int]:
        remaining = self.days_remaining()
        for days in self.reminder_days:
            if remaining == days and days not in self.alerted_days:
                return days
        return None


# ---------------------------------------------------------------------------
# Main Alerts Engine
# ---------------------------------------------------------------------------

class AlertsEngine:
    """
    Central alert dispatcher for SintraPrime.
    Manages rules, routes alerts to Slack/Discord/webhooks,
    and monitors deadlines.
    """

    def __init__(
        self,
        slack_adapter: Optional[SlackAdapter] = None,
        discord_adapter: Optional[DiscordAdapter] = None,
        webhook_adapter: Optional[WebhookAdapter] = None,
        on_alert_sent: Optional[Callable[[Alert, List[AlertDeliveryResult]], None]] = None,
    ):
        self._slack = slack_adapter or SlackAdapter()
        self._discord = discord_adapter or DiscordAdapter()
        self._webhook = webhook_adapter or WebhookAdapter()
        self._on_alert_sent = on_alert_sent
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._deadlines: Dict[str, Deadline] = {}
        self._delivery_results: List[AlertDeliveryResult] = []
        self._load_default_rules()

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        return self._rules.get(rule_id)

    def disable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.enabled = False
        return True

    def enable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.enabled = True
        return True

    # ------------------------------------------------------------------
    # Alert dispatch
    # ------------------------------------------------------------------

    def send_alert(
        self,
        alert_type: AlertType,
        title: str,
        data: Dict[str, Any],
        severity: AlertSeverity = AlertSeverity.INFO,
        channels: Optional[List[AlertChannel]] = None,
        rule_id: Optional[str] = None,
    ) -> Alert:
        message = render_alert_message(alert_type, data)
        alert = Alert(
            alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metadata=data,
            channels=channels or self._default_channels_for_type(alert_type),
            rule_id=rule_id,
        )
        results = self._dispatch(alert)
        alert.sent = any(r.success for r in results)
        alert.sent_at = datetime.utcnow() if alert.sent else None
        self._alerts.append(alert)
        self._delivery_results.extend(results)

        if self._on_alert_sent:
            self._on_alert_sent(alert, results)

        return alert

    def send_hot_lead_alert(self, lead_data: Dict[str, Any]) -> Alert:
        return self.send_alert(
            alert_type=AlertType.HOT_LEAD,
            title="🔥 Hot Lead Detected",
            data=lead_data,
            severity=AlertSeverity.CRITICAL,
        )

    def send_payment_failure_alert(self, payment_data: Dict[str, Any]) -> Alert:
        return self.send_alert(
            alert_type=AlertType.PAYMENT_FAILURE,
            title="💳 Payment Failed",
            data=payment_data,
            severity=AlertSeverity.CRITICAL,
        )

    def send_payment_success_alert(self, payment_data: Dict[str, Any]) -> Alert:
        return self.send_alert(
            alert_type=AlertType.PAYMENT_SUCCESS,
            title="✅ Payment Received",
            data=payment_data,
            severity=AlertSeverity.SUCCESS,
        )

    def send_demo_booked_alert(self, demo_data: Dict[str, Any]) -> Alert:
        return self.send_alert(
            alert_type=AlertType.DEMO_BOOKED,
            title="📅 Demo Booked",
            data=demo_data,
            severity=AlertSeverity.SUCCESS,
        )

    def send_system_error_alert(self, error_data: Dict[str, Any]) -> Alert:
        return self.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            title="🚨 System Error",
            data=error_data,
            severity=AlertSeverity.CRITICAL,
        )

    # ------------------------------------------------------------------
    # Deadline management
    # ------------------------------------------------------------------

    def add_deadline(self, deadline: Deadline) -> None:
        self._deadlines[deadline.deadline_id] = deadline

    def check_deadlines(self) -> List[Alert]:
        """Check all deadlines and send alerts for those that are due."""
        alerts_sent: List[Alert] = []
        for deadline in self._deadlines.values():
            days = deadline.needs_alert()
            if days is not None:
                alert = self.send_alert(
                    alert_type=AlertType.DEADLINE_REMINDER,
                    title=f"⏰ Deadline in {days} day(s): {deadline.case_name}",
                    data={
                        "case_name": deadline.case_name,
                        "client_name": deadline.client_name,
                        "deadline": deadline.due_date.strftime("%Y-%m-%d"),
                        "days_remaining": days,
                        "action": deadline.action,
                    },
                    severity=AlertSeverity.WARNING if days > 1 else AlertSeverity.CRITICAL,
                )
                deadline.alerted_days.append(days)
                alerts_sent.append(alert)
        return alerts_sent

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._alerts)
        sent = sum(1 for a in self._alerts if a.sent)
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for a in self._alerts:
            by_type[a.alert_type.value] = by_type.get(a.alert_type.value, 0) + 1
            by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        return {
            "total_alerts": total,
            "sent_successfully": sent,
            "delivery_rate": round(sent / total * 100, 1) if total else 0.0,
            "by_type": by_type,
            "by_severity": by_severity,
            "total_delivery_attempts": len(self._delivery_results),
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        return sorted(self._alerts, key=lambda a: a.created_at, reverse=True)[:limit]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch(self, alert: Alert) -> List[AlertDeliveryResult]:
        results: List[AlertDeliveryResult] = []
        for channel in alert.channels:
            if channel == AlertChannel.SLACK:
                results.append(self._slack.send(alert))
            elif channel == AlertChannel.DISCORD:
                results.append(self._discord.send(alert))
            elif channel == AlertChannel.WEBHOOK:
                results.append(self._webhook.send(alert))
        return results

    def _default_channels_for_type(self, alert_type: AlertType) -> List[AlertChannel]:
        critical_types = {
            AlertType.HOT_LEAD, AlertType.PAYMENT_FAILURE,
            AlertType.SYSTEM_ERROR, AlertType.CHURN_RISK,
        }
        if alert_type in critical_types:
            return [AlertChannel.SLACK, AlertChannel.DISCORD]
        return [AlertChannel.SLACK]

    def _load_default_rules(self) -> None:
        self._rules["hot_lead"] = AlertRule(
            rule_id="hot_lead",
            name="Hot Lead Alert",
            alert_type=AlertType.HOT_LEAD,
            channels=[AlertChannel.SLACK, AlertChannel.DISCORD],
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=5,
        )
        self._rules["payment_failure"] = AlertRule(
            rule_id="payment_failure",
            name="Payment Failure Alert",
            alert_type=AlertType.PAYMENT_FAILURE,
            channels=[AlertChannel.SLACK],
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=0,
        )
        self._rules["demo_booked"] = AlertRule(
            rule_id="demo_booked",
            name="Demo Booked Alert",
            alert_type=AlertType.DEMO_BOOKED,
            channels=[AlertChannel.SLACK],
            severity=AlertSeverity.SUCCESS,
            cooldown_minutes=0,
        )
        self._rules["deadline_reminder"] = AlertRule(
            rule_id="deadline_reminder",
            name="Deadline Reminder",
            alert_type=AlertType.DEADLINE_REMINDER,
            channels=[AlertChannel.SLACK, AlertChannel.DISCORD],
            severity=AlertSeverity.WARNING,
            cooldown_minutes=60,
        )
