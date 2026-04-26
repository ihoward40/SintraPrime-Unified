"""
SintraPrime Push Notification Service
======================================
Web Push Protocol (RFC 8030) implementation with VAPID authentication,
notification type management, and user preference storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import struct
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.request import Request as URLRequest, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("sintra.push_notifications")

# ─── Storage ───────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / ".push_data"
VAPID_KEYS_FILE = DATA_DIR / "vapid_keys.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
PREFERENCES_FILE = DATA_DIR / "preferences.json"


# ─── Notification Types ────────────────────────────────────────────────────────
class NotificationType(str, Enum):
    COURT_DEADLINE = "court_deadline"
    CASE_LAW_UPDATE = "case_law_update"
    DOCUMENT_READY = "document_ready"
    AGENT_COMPLETED = "agent_completed"
    EMERGENCY = "emergency"
    GENERAL = "general"


NOTIFICATION_CONFIGS: Dict[NotificationType, Dict] = {
    NotificationType.COURT_DEADLINE: {
        "title_template": "Court Deadline: {title}",
        "urgency": "high",
        "ttl": 86400,
        "icon": "⚖️",
        "require_interaction": True,
    },
    NotificationType.CASE_LAW_UPDATE: {
        "title_template": "New Case Law: {title}",
        "urgency": "normal",
        "ttl": 604800,
        "icon": "📖",
        "require_interaction": False,
    },
    NotificationType.DOCUMENT_READY: {
        "title_template": "Document Ready: {title}",
        "urgency": "high",
        "ttl": 259200,
        "icon": "📄",
        "require_interaction": True,
    },
    NotificationType.AGENT_COMPLETED: {
        "title_template": "Agent Task Complete: {title}",
        "urgency": "normal",
        "ttl": 86400,
        "icon": "🤖",
        "require_interaction": False,
    },
    NotificationType.EMERGENCY: {
        "title_template": "🚨 URGENT: {title}",
        "urgency": "very-high",
        "ttl": 3600,
        "icon": "🚨",
        "require_interaction": True,
    },
    NotificationType.GENERAL: {
        "title_template": "{title}",
        "urgency": "normal",
        "ttl": 86400,
        "icon": "ℹ️",
        "require_interaction": False,
    },
}


# ─── Models ────────────────────────────────────────────────────────────────────
@dataclass
class VAPIDKeys:
    private_key_b64: str
    public_key_b64: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PushSubscription:
    subscription_id: str
    endpoint: str
    p256dh: str
    auth: str
    user_id: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: Optional[str] = None
    active: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class NotificationPreferences:
    user_id: str
    enabled_types: Set[NotificationType] = field(
        default_factory=lambda: set(NotificationType)
    )
    quiet_hours_start: Optional[int] = None  # hour 0-23
    quiet_hours_end: Optional[int] = None
    deadline_reminders: List[int] = field(
        default_factory=lambda: [24, 72, 168]  # hours before deadline
    )
    min_urgency: str = "normal"

    def is_quiet_hour(self) -> bool:
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False
        now_hour = datetime.now().hour
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now_hour < self.quiet_hours_end
        return now_hour >= self.quiet_hours_start or now_hour < self.quiet_hours_end

    def allows_type(self, notif_type: NotificationType) -> bool:
        return notif_type in self.enabled_types

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "enabled_types": [t.value for t in self.enabled_types],
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "deadline_reminders": self.deadline_reminders,
            "min_urgency": self.min_urgency,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "NotificationPreferences":
        prefs = cls(user_id=data["user_id"])
        prefs.enabled_types = {NotificationType(t) for t in data.get("enabled_types", [])}
        prefs.quiet_hours_start = data.get("quiet_hours_start")
        prefs.quiet_hours_end = data.get("quiet_hours_end")
        prefs.deadline_reminders = data.get("deadline_reminders", [24, 72, 168])
        prefs.min_urgency = data.get("min_urgency", "normal")
        return prefs


@dataclass
class NotificationPayload:
    notification_type: NotificationType
    title: str
    body: str
    url: str = "/"
    case_id: Optional[str] = None
    data: Optional[Dict] = None

    def to_json_bytes(self) -> bytes:
        config = NOTIFICATION_CONFIGS[self.notification_type]
        payload = {
            "type": self.notification_type.value,
            "title": config["title_template"].format(title=self.title),
            "body": self.body,
            "url": self.url,
            "icon": config["icon"],
            "requireInteraction": config["require_interaction"],
        }
        if self.case_id:
            payload["caseId"] = self.case_id
        if self.data:
            payload["data"] = self.data
        return json.dumps(payload).encode("utf-8")


# ─── VAPID Key Management ──────────────────────────────────────────────────────
class VAPIDManager:
    """Generates and manages VAPID key pairs for Web Push."""

    def __init__(self, keys_file: Path = VAPID_KEYS_FILE):
        self.keys_file = keys_file
        self._keys: Optional[VAPIDKeys] = None
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load_or_generate()

    def _load_or_generate(self):
        if self.keys_file.exists():
            try:
                data = json.loads(self.keys_file.read_text())
                self._keys = VAPIDKeys(**data)
                logger.info("Loaded existing VAPID keys")
                return
            except Exception as e:
                logger.warning("Failed to load VAPID keys: %s", e)
        self._generate()

    def _generate(self):
        """Generate a new VAPID key pair (simulated for environments without crypto libs)."""
        # In production use pywebpush or cryptography library
        # Here we generate a secure random key pair representation
        private_key_bytes = secrets.token_bytes(32)
        # Simulate EC P-256 public key derivation (placeholder)
        public_key_bytes = hashlib.sha256(b"sintra-vapid-public" + private_key_bytes).digest()
        # Pad to 65 bytes (uncompressed EC point format)
        public_key_full = b'\x04' + public_key_bytes + secrets.token_bytes(32)

        self._keys = VAPIDKeys(
            private_key_b64=base64.urlsafe_b64encode(private_key_bytes).decode().rstrip("="),
            public_key_b64=base64.urlsafe_b64encode(public_key_full).decode().rstrip("="),
        )
        self.keys_file.write_text(json.dumps(self._keys.to_dict(), indent=2))
        logger.info("Generated new VAPID key pair")

    @property
    def public_key(self) -> str:
        return self._keys.public_key_b64 if self._keys else ""

    @property
    def private_key(self) -> str:
        return self._keys.private_key_b64 if self._keys else ""

    def rotate_keys(self) -> VAPIDKeys:
        """Generate fresh VAPID keys (invalidates existing subscriptions)."""
        self._generate()
        return self._keys

    def create_vapid_jwt(self, audience: str, subject: str = "mailto:admin@sintra.prime") -> str:
        """Create VAPID JWT token for push authorization."""
        now = int(time.time())
        header = base64.urlsafe_b64encode(
            json.dumps({"typ": "JWT", "alg": "ES256"}).encode()
        ).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({
                "aud": audience,
                "exp": now + 43200,  # 12 hours
                "sub": subject,
                "iat": now,
            }).encode()
        ).decode().rstrip("=")
        # Signature (simplified — production should use proper ES256)
        signing_input = f"{header}.{payload}"
        sig_bytes = hmac.new(
            self.private_key.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        sig = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
        return f"{signing_input}.{sig}"


# ─── Subscription Store ────────────────────────────────────────────────────────
class SubscriptionStore:
    def __init__(self, file: Path = SUBSCRIPTIONS_FILE):
        self.file = file
        self._subs: Dict[str, PushSubscription] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text())
                for sid, sub_data in data.items():
                    self._subs[sid] = PushSubscription(**sub_data)
            except Exception as e:
                logger.warning("Failed to load subscriptions: %s", e)

    def _save(self):
        self.file.write_text(
            json.dumps({sid: sub.to_dict() for sid, sub in self._subs.items()}, indent=2)
        )

    def add(self, endpoint: str, p256dh: str, auth: str,
            user_id: Optional[str] = None, user_agent: Optional[str] = None) -> PushSubscription:
        sub_id = hashlib.sha256(endpoint.encode()).hexdigest()[:16]
        sub = PushSubscription(
            subscription_id=sub_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_id=user_id,
            user_agent=user_agent,
        )
        self._subs[sub_id] = sub
        self._save()
        return sub

    def get(self, sub_id: str) -> Optional[PushSubscription]:
        return self._subs.get(sub_id)

    def get_by_user(self, user_id: str) -> List[PushSubscription]:
        return [s for s in self._subs.values() if s.user_id == user_id and s.active]

    def get_all_active(self) -> List[PushSubscription]:
        return [s for s in self._subs.values() if s.active]

    def remove(self, sub_id: str) -> bool:
        if sub_id in self._subs:
            self._subs[sub_id].active = False
            self._save()
            return True
        return False

    def count(self) -> int:
        return sum(1 for s in self._subs.values() if s.active)


# ─── Preferences Store ─────────────────────────────────────────────────────────
class PreferencesStore:
    def __init__(self, file: Path = PREFERENCES_FILE):
        self.file = file
        self._prefs: Dict[str, NotificationPreferences] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text())
                for uid, pref_data in data.items():
                    self._prefs[uid] = NotificationPreferences.from_dict(pref_data)
            except Exception as e:
                logger.warning("Failed to load preferences: %s", e)

    def _save(self):
        self.file.write_text(
            json.dumps({uid: p.to_dict() for uid, p in self._prefs.items()}, indent=2)
        )

    def get(self, user_id: str) -> NotificationPreferences:
        return self._prefs.get(user_id, NotificationPreferences(user_id=user_id))

    def set(self, prefs: NotificationPreferences):
        self._prefs[prefs.user_id] = prefs
        self._save()

    def update(self, user_id: str, **kwargs) -> NotificationPreferences:
        prefs = self.get(user_id)
        for key, val in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, val)
        self.set(prefs)
        return prefs


# ─── Push Notification Service ─────────────────────────────────────────────────
class PushNotificationService:
    """Main service for sending Web Push notifications."""

    def __init__(self):
        self.vapid = VAPIDManager()
        self.subscriptions = SubscriptionStore()
        self.preferences = PreferencesStore()
        logger.info(
            "PushNotificationService initialized. VAPID public key: %s...",
            self.vapid.public_key[:20],
        )

    async def subscribe(self, sub_data: Dict) -> PushSubscription:
        """Register a new push subscription from PWA."""
        endpoint = sub_data.get("endpoint", "")
        keys = sub_data.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        if not endpoint or not p256dh or not auth:
            raise ValueError("Invalid subscription data — missing endpoint or keys")

        sub = self.subscriptions.add(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_id=sub_data.get("user_id"),
            user_agent=sub_data.get("user_agent"),
        )
        logger.info("New push subscription: %s", sub.subscription_id)
        return sub

    def unsubscribe(self, sub_id: str) -> bool:
        return self.subscriptions.remove(sub_id)

    async def send_to_user(self, user_id: str, payload: NotificationPayload) -> Dict[str, int]:
        """Send notification to all subscriptions for a user."""
        prefs = self.preferences.get(user_id)
        if not prefs.allows_type(payload.notification_type):
            logger.info("Notification suppressed by user prefs: %s", user_id)
            return {"sent": 0, "suppressed": 1, "failed": 0}
        if prefs.is_quiet_hour() and payload.notification_type != NotificationType.EMERGENCY:
            logger.info("Notification suppressed (quiet hours): %s", user_id)
            return {"sent": 0, "suppressed": 1, "failed": 0}

        subs = self.subscriptions.get_by_user(user_id)
        return await self._send_to_subscriptions(subs, payload)

    async def broadcast(self, payload: NotificationPayload) -> Dict[str, int]:
        """Broadcast notification to all active subscriptions."""
        subs = self.subscriptions.get_all_active()
        return await self._send_to_subscriptions(subs, payload)

    async def _send_to_subscriptions(
        self, subs: List[PushSubscription], payload: NotificationPayload
    ) -> Dict[str, int]:
        results = {"sent": 0, "failed": 0, "suppressed": 0}
        for sub in subs:
            try:
                success = await self._send_push(sub, payload)
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error("Failed to send push to %s: %s", sub.subscription_id, e)
                results["failed"] += 1
        return results

    async def _send_push(self, sub: PushSubscription, payload: NotificationPayload) -> bool:
        """Send a single Web Push notification."""
        config = NOTIFICATION_CONFIGS[payload.notification_type]
        ttl = config["ttl"]
        urgency = config["urgency"]
        payload_bytes = payload.to_json_bytes()

        # Encrypt payload using AES-128-GCM (simplified — production uses real ECDH)
        encrypted = self._encrypt_payload(payload_bytes, sub.p256dh, sub.auth)

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Encoding": "aes128gcm",
            "TTL": str(ttl),
            "Urgency": urgency,
            "Content-Length": str(len(encrypted)),
        }

        # Add VAPID authorization
        audience = "/".join(sub.endpoint.split("/")[:3])
        jwt = self.vapid.create_vapid_jwt(audience)
        headers["Authorization"] = f"vapid t={jwt},k={self.vapid.public_key}"

        try:
            req = URLRequest(sub.endpoint, data=encrypted, headers=headers, method="POST")
            with urlopen(req, timeout=10) as resp:
                status = resp.status
                if status in (200, 201, 202):
                    sub.last_used = datetime.now(timezone.utc).isoformat()
                    return True
                elif status == 410:  # Gone — subscription expired
                    self.subscriptions.remove(sub.subscription_id)
                return False
        except HTTPError as e:
            if e.code == 410:
                self.subscriptions.remove(sub.subscription_id)
            logger.warning("HTTP error sending push: %s", e.code)
            return False
        except (URLError, OSError) as e:
            logger.warning("Network error sending push: %s", e)
            return False

    def _encrypt_payload(self, payload: bytes, p256dh: str, auth: str) -> bytes:
        """
        Simplified payload encryption stub.
        Production implementation uses ECDH key exchange + AES-128-GCM.
        See RFC 8291 for full spec.
        """
        # Salt (16 random bytes)
        salt = secrets.token_bytes(16)
        # In production: derive encryption key via ECDH + HKDF
        # For now: XOR-based placeholder that maintains the message structure
        key = hashlib.pbkdf2_hmac("sha256", auth.encode(), salt, 1000, 16)
        encrypted_body = bytes(b ^ k for b, k in zip(payload, (key * (len(payload) // 16 + 1))[:len(payload)]))
        # Web Push record format: salt (16) + key length (4) + sender public key (65) + payload
        return salt + struct.pack(">I", 4096) + secrets.token_bytes(65) + encrypted_body

    # ─── Deadline Reminders ───────────────────────────────────────────────────
    async def send_deadline_reminder(
        self, user_id: str, case_name: str, deadline_title: str,
        deadline_date: datetime, case_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Send a court deadline reminder notification."""
        now = datetime.now(timezone.utc)
        hours_until = (deadline_date - now).total_seconds() / 3600

        if hours_until < 0:
            body = f"PAST DUE: {deadline_title} in {case_name}"
        elif hours_until < 24:
            body = f"{deadline_title} in {case_name} is due TODAY"
        elif hours_until < 72:
            body = f"{deadline_title} in {case_name} due in {int(hours_until / 24)} day(s)"
        else:
            body = f"{deadline_title} in {case_name} due {deadline_date.strftime('%b %d')}"

        payload = NotificationPayload(
            notification_type=NotificationType.COURT_DEADLINE,
            title=deadline_title,
            body=body,
            url=f"/cases/{case_id}/deadlines" if case_id else "/deadlines",
            case_id=case_id,
        )
        return await self.send_to_user(user_id, payload)

    async def send_case_law_update(
        self, user_id: str, case_name: str, ruling_title: str, case_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Notify user of new relevant case law."""
        payload = NotificationPayload(
            notification_type=NotificationType.CASE_LAW_UPDATE,
            title=ruling_title,
            body=f"New relevant ruling found for {case_name}",
            url=f"/research?case={case_id}" if case_id else "/research",
            case_id=case_id,
        )
        return await self.send_to_user(user_id, payload)

    async def send_document_ready(
        self, user_id: str, document_name: str, document_id: str
    ) -> Dict[str, int]:
        """Notify user that a document is ready for signature."""
        payload = NotificationPayload(
            notification_type=NotificationType.DOCUMENT_READY,
            title=document_name,
            body=f"{document_name} is ready for your signature",
            url=f"/documents/{document_id}/sign",
        )
        return await self.send_to_user(user_id, payload)

    async def send_agent_completed(
        self, user_id: str, task_name: str, result_summary: str, task_id: str
    ) -> Dict[str, int]:
        """Notify user that an AI agent task completed."""
        payload = NotificationPayload(
            notification_type=NotificationType.AGENT_COMPLETED,
            title=task_name,
            body=result_summary,
            url=f"/agents/{task_id}",
        )
        return await self.send_to_user(user_id, payload)

    async def send_emergency(
        self, user_id: str, title: str, body: str, url: str = "/"
    ) -> Dict[str, int]:
        """Send an emergency/time-sensitive legal alert."""
        payload = NotificationPayload(
            notification_type=NotificationType.EMERGENCY,
            title=title,
            body=body,
            url=url,
        )
        return await self.send_to_user(user_id, payload)

    def update_preferences(self, user_id: str, **kwargs) -> NotificationPreferences:
        return self.preferences.update(user_id, **kwargs)

    def get_preferences(self, user_id: str) -> NotificationPreferences:
        return self.preferences.get(user_id)

    def get_vapid_public_key(self) -> str:
        return self.vapid.public_key

    def get_stats(self) -> Dict:
        return {
            "active_subscriptions": self.subscriptions.count(),
            "vapid_public_key_prefix": self.vapid.public_key[:20] + "...",
        }


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    async def demo():
        svc = PushNotificationService()
        print(f"VAPID Public Key: {svc.get_vapid_public_key()[:40]}...")
        print(f"Stats: {svc.get_stats()}")

    asyncio.run(demo())
