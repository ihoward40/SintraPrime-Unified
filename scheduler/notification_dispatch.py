"""
NotificationDispatch — Multi-channel task completion notifications.
Channels: email, Discord, Telegram, Slack, webhook.
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from .task_types import TaskResult

logger = logging.getLogger(__name__)


class NotificationDispatch:
    """
    Sends task results / alerts through configured channels.

    Supported channels:
    - ``email``   — SMTP
    - ``discord`` — Discord webhook
    - ``slack``   — Slack incoming webhook
    - ``telegram``— Telegram Bot API
    - ``webhook`` — Generic HTTP POST
    - ``log``     — Python logger (always available / zero-config)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._digest_buffer: List[TaskResult] = []

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def notify_on_complete(
        self,
        task_result: TaskResult,
        channels: Optional[List[str]] = None,
    ) -> None:
        """Send task completion notification to all specified channels."""
        channels = channels or ["log"]
        for channel in channels:
            try:
                self._dispatch_to_channel(channel, task_result)
            except Exception as exc:
                logger.error("Notification to '%s' failed: %s", channel, exc)

    def alert_on_failure(
        self,
        task_result: TaskResult,
        recipients: Optional[List[str]] = None,
    ) -> None:
        """Send an urgent failure alert to the given recipients (email addresses)."""
        if task_result.success:
            return
        message = self.format_result(task_result, "plain")
        subject = f"[SintraPrime ALERT] Task {task_result.task_id} FAILED"
        self._send_email(
            subject=subject,
            body=message,
            recipients=recipients or self._config.get("alert_emails", []),
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_result(self, task_result: TaskResult, format: str = "markdown") -> str:
        """
        Format a TaskResult for human consumption.

        Formats: ``markdown`` | ``plain`` | ``json``
        """
        if format == "json":
            return json.dumps(task_result.to_dict(), indent=2)

        status = "✅ SUCCESS" if task_result.success else "❌ FAILED"
        ts = task_result.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        duration = f"{task_result.duration_ms:.0f} ms"

        if format == "markdown":
            lines = [
                f"## Task Result — {status}",
                f"- **Task ID**: `{task_result.task_id}`",
                f"- **Time**: {ts}",
                f"- **Duration**: {duration}",
            ]
            if task_result.output is not None:
                lines.append(f"\n**Output:**\n```\n{task_result.output}\n```")
            if task_result.error:
                lines.append(f"\n**Error:**\n```\n{task_result.error}\n```")
            return "\n".join(lines)

        # plain
        lines = [
            f"Task Result — {status}",
            f"Task ID : {task_result.task_id}",
            f"Time    : {ts}",
            f"Duration: {duration}",
        ]
        if task_result.output is not None:
            lines.append(f"Output  : {task_result.output}")
        if task_result.error:
            lines.append(f"Error   : {task_result.error}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Digest / scheduling
    # ------------------------------------------------------------------

    def schedule_digest(
        self,
        channel: str,
        frequency: str = "daily",
        results: Optional[List[TaskResult]] = None,
    ) -> None:
        """
        Buffer results and send a batched digest.

        ``frequency`` is informational here; in production wire this to
        the TaskScheduler recurring task.
        """
        if results:
            self._digest_buffer.extend(results)
        if not self._digest_buffer:
            logger.info("Digest requested but buffer is empty.")
            return

        lines = [f"# SintraPrime Task Digest ({frequency})", ""]
        for r in self._digest_buffer:
            icon = "✅" if r.success else "❌"
            lines.append(
                f"{icon} `{r.task_id}` — {r.timestamp.strftime('%H:%M')} — {r.duration_ms:.0f}ms"
            )
        body = "\n".join(lines)
        self._dispatch_to_channel(channel, body=body)
        self._digest_buffer.clear()

    # ------------------------------------------------------------------
    # Channel implementations
    # ------------------------------------------------------------------

    def _dispatch_to_channel(
        self,
        channel: str,
        task_result: Optional[TaskResult] = None,
        body: Optional[str] = None,
    ) -> None:
        if body is None and task_result is not None:
            body = self.format_result(task_result, "plain")

        ch = channel.lower()
        if ch == "log":
            logger.info("Notification: %s", body)
        elif ch == "email":
            self._send_email(
                subject="[SintraPrime] Task Notification",
                body=body or "",
                recipients=self._config.get("email_recipients", []),
            )
        elif ch == "discord":
            self._send_discord(body or "")
        elif ch == "slack":
            self._send_slack(body or "")
        elif ch == "telegram":
            self._send_telegram(body or "")
        elif ch == "webhook":
            self._send_webhook(
                self._config.get("webhook_url", ""),
                payload={"message": body, "timestamp": datetime.utcnow().isoformat()},
            )
        else:
            logger.warning("Unknown notification channel: '%s'", channel)

    def _send_email(
        self, subject: str, body: str, recipients: List[str]
    ) -> None:
        if not recipients:
            logger.debug("No email recipients configured; skipping.")
            return
        smtp_host = self._config.get("smtp_host", "localhost")
        smtp_port = self._config.get("smtp_port", 25)
        smtp_from = self._config.get("smtp_from", "sintra@localhost")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = ", ".join(recipients)
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
                smtp.sendmail(smtp_from, recipients, msg.as_string())
            logger.info("Email sent to %s", recipients)
        except Exception as exc:
            logger.error("SMTP error: %s", exc)

    def _send_discord(self, message: str) -> None:
        webhook_url = self._config.get("discord_webhook_url")
        if not webhook_url:
            logger.debug("Discord webhook not configured.")
            return
        self._send_webhook(webhook_url, {"content": message[:2000]})

    def _send_slack(self, message: str) -> None:
        webhook_url = self._config.get("slack_webhook_url")
        if not webhook_url:
            logger.debug("Slack webhook not configured.")
            return
        self._send_webhook(webhook_url, {"text": message})

    def _send_telegram(self, message: str) -> None:
        token = self._config.get("telegram_bot_token")
        chat_id = self._config.get("telegram_chat_id")
        if not token or not chat_id:
            logger.debug("Telegram not configured.")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message[:4096], "parse_mode": "Markdown"}
        self._send_webhook(url, payload)

    @staticmethod
    def _send_webhook(url: str, payload: Dict[str, Any]) -> None:
        if not url:
            return
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
            logger.info("Webhook POST to %s succeeded", url)
        except Exception as exc:
            logger.error("Webhook POST failed: %s", exc)
