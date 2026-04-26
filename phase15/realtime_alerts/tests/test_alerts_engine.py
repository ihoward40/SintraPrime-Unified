"""Tests for Phase 15D — Real-time Alerts Engine."""
import sys, os

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from phase15.realtime_alerts.alerts_engine import (
    AlertSeverity, AlertChannel, AlertType, AlertRule, Alert,
    AlertDeliveryResult, SlackAdapter, DiscordAdapter, WebhookAdapter,
    AlertsEngine, Deadline, render_alert_message, ALERT_TEMPLATES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_alert():
    return Alert(
        alert_id="ALT-001",
        alert_type=AlertType.HOT_LEAD,
        severity=AlertSeverity.CRITICAL,
        title="Hot Lead",
        message="Test lead alert",
        metadata={"lead_name": "John", "score": 85},
        channels=[AlertChannel.SLACK, AlertChannel.DISCORD],
    )


@pytest.fixture
def engine():
    return AlertsEngine()


@pytest.fixture
def engine_with_mocks():
    slack = MagicMock(spec=SlackAdapter)
    slack.send.return_value = AlertDeliveryResult(
        alert_id="ALT-001", channel=AlertChannel.SLACK, success=True, response_code=200
    )
    discord = MagicMock(spec=DiscordAdapter)
    discord.send.return_value = AlertDeliveryResult(
        alert_id="ALT-001", channel=AlertChannel.DISCORD, success=True, response_code=204
    )
    webhook = MagicMock(spec=WebhookAdapter)
    webhook.send.return_value = AlertDeliveryResult(
        alert_id="ALT-001", channel=AlertChannel.WEBHOOK, success=True, response_code=200
    )
    return AlertsEngine(
        slack_adapter=slack,
        discord_adapter=discord,
        webhook_adapter=webhook,
    ), slack, discord, webhook


# ---------------------------------------------------------------------------
# Alert model tests
# ---------------------------------------------------------------------------

class TestAlert:
    def test_to_slack_payload_structure(self, basic_alert):
        payload = basic_alert.to_slack_payload()
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1
        attachment = payload["attachments"][0]
        assert "color" in attachment
        assert "title" in attachment
        assert "text" in attachment

    def test_to_slack_payload_critical_color(self, basic_alert):
        basic_alert.severity = AlertSeverity.CRITICAL
        payload = basic_alert.to_slack_payload()
        assert payload["attachments"][0]["color"] == "#ff0000"

    def test_to_slack_payload_success_color(self, basic_alert):
        basic_alert.severity = AlertSeverity.SUCCESS
        payload = basic_alert.to_slack_payload()
        assert payload["attachments"][0]["color"] == "#2eb886"

    def test_to_discord_payload_structure(self, basic_alert):
        payload = basic_alert.to_discord_payload()
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        embed = payload["embeds"][0]
        assert "title" in embed
        assert "description" in embed
        assert "color" in embed

    def test_to_discord_payload_critical_color(self, basic_alert):
        basic_alert.severity = AlertSeverity.CRITICAL
        payload = basic_alert.to_discord_payload()
        assert payload["embeds"][0]["color"] == 0xFF0000

    def test_to_discord_payload_has_fields(self, basic_alert):
        payload = basic_alert.to_discord_payload()
        fields = payload["embeds"][0]["fields"]
        assert len(fields) == 2  # lead_name and score

    def test_to_discord_payload_has_timestamp(self, basic_alert):
        payload = basic_alert.to_discord_payload()
        assert "timestamp" in payload["embeds"][0]


# ---------------------------------------------------------------------------
# AlertRule tests
# ---------------------------------------------------------------------------

class TestAlertRule:
    def test_not_on_cooldown_initially(self):
        rule = AlertRule("R1", "Test", AlertType.HOT_LEAD, [AlertChannel.SLACK])
        assert rule.is_on_cooldown() is False

    def test_on_cooldown_after_trigger(self):
        rule = AlertRule("R2", "Test", AlertType.HOT_LEAD, [AlertChannel.SLACK],
                         cooldown_minutes=30)
        rule.mark_triggered()
        assert rule.is_on_cooldown() is True

    def test_not_on_cooldown_zero_minutes(self):
        rule = AlertRule("R3", "Test", AlertType.HOT_LEAD, [AlertChannel.SLACK],
                         cooldown_minutes=0)
        rule.mark_triggered()
        assert rule.is_on_cooldown() is False

    def test_cooldown_expired(self):
        rule = AlertRule("R4", "Test", AlertType.HOT_LEAD, [AlertChannel.SLACK],
                         cooldown_minutes=1)
        rule.last_triggered_at = datetime.utcnow() - timedelta(minutes=2)
        assert rule.is_on_cooldown() is False


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------

class TestTemplateRendering:
    def test_hot_lead_template(self):
        data = {
            "lead_name": "Alice", "practice_area": "Personal Injury",
            "score": 90, "phone": "+1555", "email": "a@b.com", "source": "Google"
        }
        msg = render_alert_message(AlertType.HOT_LEAD, data)
        assert "Alice" in msg
        assert "90" in msg

    def test_payment_failure_template(self):
        data = {"client_name": "Bob", "amount": "500.00", "reason": "Insufficient funds"}
        msg = render_alert_message(AlertType.PAYMENT_FAILURE, data)
        assert "Bob" in msg
        assert "500.00" in msg

    def test_deadline_reminder_template(self):
        data = {
            "case_name": "Smith v Jones", "client_name": "Smith",
            "deadline": "2025-12-31", "days_remaining": 3, "action": "File motion"
        }
        msg = render_alert_message(AlertType.DEADLINE_REMINDER, data)
        assert "Smith v Jones" in msg
        assert "3" in msg

    def test_missing_keys_replaced_with_na(self):
        data = {"lead_name": "Alice"}  # Missing other keys
        msg = render_alert_message(AlertType.HOT_LEAD, data)
        assert "N/A" in msg  # Missing keys should be N/A

    def test_all_alert_types_have_templates(self):
        for alert_type in AlertType:
            if alert_type == AlertType.CUSTOM:
                continue
            assert alert_type in ALERT_TEMPLATES


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------

class TestSlackAdapter:
    def test_send_without_webhook_dry_run(self, basic_alert):
        adapter = SlackAdapter()
        result = adapter.send(basic_alert)
        assert result.success is True
        assert result.channel == AlertChannel.SLACK

    def test_send_with_mock_http(self, basic_alert):
        mock_http = MagicMock()
        mock_http.post.return_value = MagicMock(status_code=200)
        adapter = SlackAdapter(webhook_url="https://hooks.slack.com/test", http_client=mock_http)
        result = adapter.send(basic_alert)
        assert result.success is True
        assert result.response_code == 200
        mock_http.post.assert_called_once()

    def test_send_failure_returns_error(self, basic_alert):
        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("Connection refused")
        adapter = SlackAdapter(webhook_url="https://hooks.slack.com/test", http_client=mock_http)
        result = adapter.send(basic_alert)
        assert result.success is False
        assert result.error is not None


class TestDiscordAdapter:
    def test_send_without_webhook_dry_run(self, basic_alert):
        adapter = DiscordAdapter()
        result = adapter.send(basic_alert)
        assert result.success is True
        assert result.channel == AlertChannel.DISCORD

    def test_send_with_mock_http_204(self, basic_alert):
        mock_http = MagicMock()
        mock_http.post.return_value = MagicMock(status_code=204)
        adapter = DiscordAdapter(webhook_url="https://discord.com/api/webhooks/test",
                                 http_client=mock_http)
        result = adapter.send(basic_alert)
        assert result.success is True

    def test_send_failure(self, basic_alert):
        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("Timeout")
        adapter = DiscordAdapter(webhook_url="https://discord.com/api/webhooks/test",
                                 http_client=mock_http)
        result = adapter.send(basic_alert)
        assert result.success is False


class TestWebhookAdapter:
    def test_send_without_url_dry_run(self, basic_alert):
        adapter = WebhookAdapter()
        result = adapter.send(basic_alert)
        assert result.success is True

    def test_send_with_mock_http(self, basic_alert):
        mock_http = MagicMock()
        mock_http.post.return_value = MagicMock(status_code=200)
        adapter = WebhookAdapter(url="https://example.com/webhook", http_client=mock_http)
        result = adapter.send(basic_alert)
        assert result.success is True


# ---------------------------------------------------------------------------
# Deadline tests
# ---------------------------------------------------------------------------

class TestDeadline:
    def test_days_remaining_future(self):
        dl = Deadline(
            deadline_id="D1", case_name="Case A", client_name="Client",
            due_date=datetime.utcnow() + timedelta(days=7),
            action="File motion",
        )
        assert dl.days_remaining() == 7

    def test_days_remaining_past(self):
        dl = Deadline(
            deadline_id="D2", case_name="Case B", client_name="Client",
            due_date=datetime.utcnow() - timedelta(days=1),
            action="File motion",
        )
        assert dl.days_remaining() < 0

    def test_needs_alert_at_7_days(self):
        dl = Deadline(
            deadline_id="D3", case_name="Case C", client_name="Client",
            due_date=datetime.utcnow() + timedelta(days=7),
            action="File motion",
            reminder_days=[7, 3, 1],
        )
        assert dl.needs_alert() == 7

    def test_needs_alert_already_alerted(self):
        dl = Deadline(
            deadline_id="D4", case_name="Case D", client_name="Client",
            due_date=datetime.utcnow() + timedelta(days=7),
            action="File motion",
            reminder_days=[7, 3, 1],
            alerted_days=[7],
        )
        assert dl.needs_alert() is None

    def test_needs_alert_not_due_yet(self):
        dl = Deadline(
            deadline_id="D5", case_name="Case E", client_name="Client",
            due_date=datetime.utcnow() + timedelta(days=10),
            action="File motion",
            reminder_days=[7, 3, 1],
        )
        assert dl.needs_alert() is None


# ---------------------------------------------------------------------------
# AlertsEngine tests
# ---------------------------------------------------------------------------

class TestAlertsEngine:
    def test_send_alert_creates_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_alert(
            alert_type=AlertType.HOT_LEAD,
            title="Test Hot Lead",
            data={"lead_name": "Alice", "score": 90, "practice_area": "PI",
                  "phone": "+1555", "email": "a@b.com", "source": "Google"},
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.DISCORD],
        )
        assert alert is not None
        assert alert.sent is True
        slack.send.assert_called_once()
        discord.send.assert_called_once()

    def test_send_hot_lead_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_hot_lead_alert({
            "lead_name": "Bob", "score": 95, "practice_area": "Criminal",
            "phone": "+1555", "email": "b@b.com", "source": "Referral"
        })
        assert alert.alert_type == AlertType.HOT_LEAD
        assert alert.severity == AlertSeverity.CRITICAL

    def test_send_payment_failure_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_payment_failure_alert({
            "client_name": "Carol", "amount": "299.00", "reason": "Card declined"
        })
        assert alert.alert_type == AlertType.PAYMENT_FAILURE

    def test_send_payment_success_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_payment_success_alert({
            "client_name": "Dave", "amount": "1500.00", "invoice_id": "INV-001"
        })
        assert alert.alert_type == AlertType.PAYMENT_SUCCESS
        assert alert.severity == AlertSeverity.SUCCESS

    def test_send_demo_booked_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_demo_booked_alert({
            "lead_name": "Eve", "demo_time": "2025-06-01 14:00",
            "practice_area": "Family Law", "source": "Website"
        })
        assert alert.alert_type == AlertType.DEMO_BOOKED

    def test_send_system_error_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_system_error_alert({
            "component": "DatabaseManager",
            "error_message": "Connection timeout",
            "timestamp": "2025-06-01T10:00:00"
        })
        assert alert.alert_type == AlertType.SYSTEM_ERROR
        assert alert.severity == AlertSeverity.CRITICAL

    def test_on_alert_sent_callback(self):
        callback = MagicMock()
        eng = AlertsEngine(on_alert_sent=callback)
        eng.send_alert(
            alert_type=AlertType.HOT_LEAD,
            title="Test",
            data={"lead_name": "X", "score": 80, "practice_area": "PI",
                  "phone": "+1", "email": "x@x.com", "source": "Web"},
        )
        callback.assert_called_once()

    def test_add_and_get_rule(self, engine):
        rule = AlertRule("custom_rule", "Custom", AlertType.CUSTOM, [AlertChannel.SLACK])
        engine.add_rule(rule)
        assert engine.get_rule("custom_rule") is rule

    def test_disable_enable_rule(self, engine):
        assert engine.disable_rule("hot_lead") is True
        assert engine.get_rule("hot_lead").enabled is False
        assert engine.enable_rule("hot_lead") is True
        assert engine.get_rule("hot_lead").enabled is True

    def test_disable_unknown_rule(self, engine):
        assert engine.disable_rule("nonexistent") is False

    def test_default_rules_loaded(self, engine):
        assert engine.get_rule("hot_lead") is not None
        assert engine.get_rule("payment_failure") is not None
        assert engine.get_rule("demo_booked") is not None

    def test_check_deadlines_sends_alert(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        dl = Deadline(
            deadline_id="D1", case_name="Smith Case", client_name="Smith",
            due_date=datetime.utcnow() + timedelta(days=7),
            action="File response",
            reminder_days=[7, 3, 1],
        )
        eng.add_deadline(dl)
        alerts = eng.check_deadlines()
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DEADLINE_REMINDER

    def test_check_deadlines_no_duplicates(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        dl = Deadline(
            deadline_id="D2", case_name="Jones Case", client_name="Jones",
            due_date=datetime.utcnow() + timedelta(days=7),
            action="File motion",
            reminder_days=[7],
            alerted_days=[7],  # Already alerted
        )
        eng.add_deadline(dl)
        alerts = eng.check_deadlines()
        assert len(alerts) == 0

    def test_get_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats["total_alerts"] == 0
        assert stats["delivery_rate"] == 0.0

    def test_get_stats_with_alerts(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        eng.send_hot_lead_alert({
            "lead_name": "X", "score": 80, "practice_area": "PI",
            "phone": "+1", "email": "x@x.com", "source": "Web"
        })
        stats = eng.get_stats()
        assert stats["total_alerts"] == 1
        assert stats["sent_successfully"] == 1
        assert stats["delivery_rate"] == 100.0
        assert AlertType.HOT_LEAD.value in stats["by_type"]

    def test_get_recent_alerts(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        for i in range(5):
            eng.send_payment_success_alert({
                "client_name": f"Client{i}", "amount": "100.00", "invoice_id": f"INV-{i}"
            })
        recent = eng.get_recent_alerts(limit=3)
        assert len(recent) == 3

    def test_webhook_channel_dispatched(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        eng.send_alert(
            alert_type=AlertType.CUSTOM,
            title="Webhook Test",
            data={"message": "test"},
            channels=[AlertChannel.WEBHOOK],
        )
        webhook.send.assert_called_once()

    def test_alert_sent_flag_set(self, engine_with_mocks):
        eng, slack, discord, webhook = engine_with_mocks
        alert = eng.send_alert(
            alert_type=AlertType.PAYMENT_SUCCESS,
            title="Payment",
            data={"client_name": "X", "amount": "100", "invoice_id": "I1"},
            channels=[AlertChannel.SLACK],
        )
        assert alert.sent is True
        assert alert.sent_at is not None
