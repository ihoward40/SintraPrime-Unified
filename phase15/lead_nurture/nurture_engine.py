"""
Phase 15A — Autonomous Lead Nurture Engine
Handles AI-driven call scheduling, SMS sequences, and video outreach
to automatically convert inbound leads into booked demos.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    NURTURING = "nurturing"
    DEMO_BOOKED = "demo_booked"
    CONVERTED = "converted"
    LOST = "lost"
    UNSUBSCRIBED = "unsubscribed"


class ChannelType(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    VOICE_CALL = "voice_call"
    VIDEO = "video"
    WHATSAPP = "whatsapp"


class SequenceStepType(str, Enum):
    SEND_SMS = "send_sms"
    SEND_EMAIL = "send_email"
    MAKE_CALL = "make_call"
    SEND_VIDEO = "send_video"
    WAIT = "wait"
    BRANCH = "branch"
    BOOK_DEMO = "book_demo"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Lead:
    lead_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    practice_area: str = "general"
    source: str = "website"
    status: LeadStatus = LeadStatus.NEW
    score: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_contacted_at: Optional[datetime] = None
    demo_booked_at: Optional[datetime] = None
    sequence_step: int = 0
    opted_out: bool = False

    def is_contactable(self) -> bool:
        return (
            not self.opted_out
            and self.status not in (LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.UNSUBSCRIBED)
            and (self.phone is not None or self.email is not None)
        )

    def days_since_contact(self) -> Optional[int]:
        if self.last_contacted_at is None:
            return None
        return (datetime.utcnow() - self.last_contacted_at).days


@dataclass
class SequenceStep:
    step_id: str
    step_type: SequenceStepType
    delay_hours: int = 0
    content: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # e.g. "score > 50"
    next_step_on_success: Optional[str] = None
    next_step_on_failure: Optional[str] = None


@dataclass
class NurtureSequence:
    sequence_id: str
    name: str
    practice_area: str
    steps: List[SequenceStep] = field(default_factory=list)
    active: bool = True

    def get_step(self, step_index: int) -> Optional[SequenceStep]:
        if 0 <= step_index < len(self.steps):
            return self.steps[step_index]
        return None


@dataclass
class OutreachResult:
    lead_id: str
    channel: ChannelType
    step_type: SequenceStepType
    success: bool
    message_sid: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_received: bool = False
    demo_booked: bool = False


# ---------------------------------------------------------------------------
# Channel adapters (thin wrappers — real credentials injected at runtime)
# ---------------------------------------------------------------------------

class SMSAdapter:
    """Twilio SMS wrapper."""

    def __init__(self, client=None):
        self._client = client  # twilio.rest.Client or mock

    def send(self, to: str, body: str, from_: str = "+15005550006") -> Dict[str, Any]:
        if self._client is None:
            logger.warning("SMS adapter: no client configured — dry run")
            return {"sid": f"SM{uuid.uuid4().hex[:32]}", "status": "queued", "dry_run": True}
        msg = self._client.messages.create(body=body, from_=from_, to=to)
        return {"sid": msg.sid, "status": msg.status}


class VoiceCallAdapter:
    """Twilio Programmable Voice wrapper."""

    def __init__(self, client=None, twiml_base_url: str = "https://sintra.ai/twiml"):
        self._client = client
        self._twiml_base_url = twiml_base_url

    def call(self, to: str, script_key: str, from_: str = "+15005550006") -> Dict[str, Any]:
        url = f"{self._twiml_base_url}/{script_key}"
        if self._client is None:
            logger.warning("Voice adapter: no client configured — dry run")
            return {"sid": f"CA{uuid.uuid4().hex[:32]}", "status": "queued", "dry_run": True}
        call = self._client.calls.create(url=url, to=to, from_=from_)
        return {"sid": call.sid, "status": call.status}


class VideoOutreachAdapter:
    """Loom / Synthesia personalised video wrapper."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    def send(self, to_email: str, lead_name: str, template_id: str) -> Dict[str, Any]:
        if not self._api_key:
            logger.warning("Video adapter: no API key — dry run")
            return {"video_id": f"VID{uuid.uuid4().hex[:8]}", "status": "queued", "dry_run": True}
        # Real implementation would call Synthesia / Loom API
        return {"video_id": f"VID{uuid.uuid4().hex[:8]}", "status": "rendering"}


class CalendarAdapter:
    """Calendly / Cal.com booking wrapper."""

    def __init__(self, booking_url: str = "https://calendly.com/sintra/demo"):
        self._booking_url = booking_url

    def generate_booking_link(self, lead: Lead) -> str:
        params = f"?name={lead.name.replace(' ', '+')}&email={lead.email or ''}"
        return self._booking_url + params

    def check_booking(self, lead_id: str) -> bool:
        """Returns True if a booking exists for this lead (stub)."""
        return False


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

SCORE_RULES: List[Tuple[str, int]] = [
    ("practice_area:personal_injury", 20),
    ("practice_area:criminal_defense", 15),
    ("practice_area:family_law", 15),
    ("practice_area:immigration", 10),
    ("source:referral", 25),
    ("source:google_ads", 15),
    ("source:organic", 10),
    ("source:social", 5),
    ("has_phone", 10),
    ("has_email", 5),
    ("responded_to_sms", 20),
    ("opened_email", 10),
    ("clicked_link", 15),
    ("visited_pricing", 25),
]


def score_lead(lead: Lead) -> int:
    score = 0
    for rule, points in SCORE_RULES:
        if ":" in rule:
            key, val = rule.split(":", 1)
            if lead.metadata.get(key) == val or getattr(lead, key, None) == val:
                score += points
            elif key == "practice_area" and lead.practice_area == val:
                score += points
            elif key == "source" and lead.source == val:
                score += points
        elif rule == "has_phone" and lead.phone:
            score += points
        elif rule == "has_email" and lead.email:
            score += points
        elif rule in lead.tags:
            score += points
    return min(score, 100)


# ---------------------------------------------------------------------------
# Template renderer
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES: Dict[str, str] = {
    "sms_initial": (
        "Hi {name}, this is SintraPrime Legal AI. You recently reached out about {practice_area} help. "
        "Reply YES to schedule a free 15-min consult, or STOP to opt out."
    ),
    "sms_followup_1": (
        "Hi {name}, just following up! We have availability this week for a free {practice_area} consultation. "
        "Reply YES to book or STOP to opt out."
    ),
    "sms_followup_2": (
        "{name}, last chance — our AI legal assistant can help with your {practice_area} case today. "
        "Book here: {booking_link} or reply STOP to opt out."
    ),
    "sms_hot_lead": (
        "🔥 {name}, your case looks urgent. An attorney is standing by. "
        "Call now: {phone} or book: {booking_link}"
    ),
    "voice_script_initial": "initial_consult_v1",
    "voice_script_followup": "followup_v1",
    "video_template_personal_injury": "pi_intro_v2",
    "video_template_default": "general_intro_v1",
}


def render_template(template_key: str, lead: Lead, booking_link: str = "") -> str:
    template = DEFAULT_TEMPLATES.get(template_key, "")
    return template.format(
        name=lead.name.split()[0],
        practice_area=lead.practice_area.replace("_", " "),
        booking_link=booking_link,
        phone=lead.phone or "",
        email=lead.email or "",
    )


# ---------------------------------------------------------------------------
# Condition evaluator
# ---------------------------------------------------------------------------

def evaluate_condition(condition: str, lead: Lead) -> bool:
    """
    Simple condition evaluator for sequence branching.
    Supports: score > N, score < N, tag:X, status:X
    """
    condition = condition.strip()
    if not condition:
        return True

    score_match = re.match(r"score\s*([><=!]+)\s*(\d+)", condition)
    if score_match:
        op, val = score_match.group(1), int(score_match.group(2))
        s = lead.score
        return (
            (op == ">" and s > val)
            or (op == ">=" and s >= val)
            or (op == "<" and s < val)
            or (op == "<=" and s <= val)
            or (op == "==" and s == val)
            or (op == "!=" and s != val)
        )

    if condition.startswith("tag:"):
        return condition[4:] in lead.tags

    if condition.startswith("status:"):
        return lead.status.value == condition[7:]

    if condition.startswith("practice_area:"):
        return lead.practice_area == condition[14:]

    return False


# ---------------------------------------------------------------------------
# Core nurture engine
# ---------------------------------------------------------------------------

class NurtureEngine:
    """
    Orchestrates multi-channel lead nurture sequences.
    Designed to be called by a scheduler (e.g., sintra_scheduler) every 15 minutes.
    """

    def __init__(
        self,
        sms_adapter: Optional[SMSAdapter] = None,
        voice_adapter: Optional[VoiceCallAdapter] = None,
        video_adapter: Optional[VideoOutreachAdapter] = None,
        calendar_adapter: Optional[CalendarAdapter] = None,
        on_demo_booked: Optional[Callable[[Lead], None]] = None,
        on_lead_updated: Optional[Callable[[Lead], None]] = None,
    ):
        self._sms = sms_adapter or SMSAdapter()
        self._voice = voice_adapter or VoiceCallAdapter()
        self._video = video_adapter or VideoOutreachAdapter()
        self._calendar = calendar_adapter or CalendarAdapter()
        self._on_demo_booked = on_demo_booked
        self._on_lead_updated = on_lead_updated
        self._sequences: Dict[str, NurtureSequence] = {}
        self._leads: Dict[str, Lead] = {}
        self._results: List[OutreachResult] = []
        self._load_default_sequences()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_lead(self, lead: Lead) -> Lead:
        lead.score = score_lead(lead)
        self._leads[lead.lead_id] = lead
        logger.info("Lead added: %s (score=%d)", lead.lead_id, lead.score)
        return lead

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        return self._leads.get(lead_id)

    def update_lead_tag(self, lead_id: str, tag: str) -> bool:
        lead = self._leads.get(lead_id)
        if not lead:
            return False
        if tag not in lead.tags:
            lead.tags.append(tag)
        lead.score = score_lead(lead)
        if self._on_lead_updated:
            self._on_lead_updated(lead)
        return True

    def handle_opt_out(self, lead_id: str) -> bool:
        lead = self._leads.get(lead_id)
        if not lead:
            return False
        lead.opted_out = True
        lead.status = LeadStatus.UNSUBSCRIBED
        logger.info("Lead %s opted out", lead_id)
        return True

    def handle_reply(self, lead_id: str, reply_text: str) -> Optional[OutreachResult]:
        lead = self._leads.get(lead_id)
        if not lead:
            return None

        reply_upper = reply_text.strip().upper()

        if reply_upper in ("STOP", "UNSUBSCRIBE", "CANCEL", "QUIT"):
            self.handle_opt_out(lead_id)
            return OutreachResult(
                lead_id=lead_id,
                channel=ChannelType.SMS,
                step_type=SequenceStepType.SEND_SMS,
                success=True,
                response_received=True,
            )

        if reply_upper in ("YES", "Y", "BOOK", "SCHEDULE", "1"):
            self.update_lead_tag(lead_id, "responded_to_sms")
            lead.score = score_lead(lead)
            return self._book_demo(lead)

        # Generic positive signal
        self.update_lead_tag(lead_id, "responded_to_sms")
        return None

    def process_due_leads(self) -> List[OutreachResult]:
        """
        Called by the scheduler. Processes all leads whose next step is due.
        Returns list of outreach results.
        """
        results: List[OutreachResult] = []
        for lead in list(self._leads.values()):
            if not lead.is_contactable():
                continue
            result = self._process_lead(lead)
            if result:
                results.append(result)
                self._results.append(result)
        return results

    def get_results(self) -> List[OutreachResult]:
        return list(self._results)

    def get_hot_leads(self, min_score: int = 70) -> List[Lead]:
        return [l for l in self._leads.values() if l.score >= min_score and l.is_contactable()]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._leads)
        by_status: Dict[str, int] = {}
        for lead in self._leads.values():
            by_status[lead.status.value] = by_status.get(lead.status.value, 0) + 1
        demos = sum(1 for l in self._leads.values() if l.status == LeadStatus.DEMO_BOOKED)
        converted = sum(1 for l in self._leads.values() if l.status == LeadStatus.CONVERTED)
        return {
            "total_leads": total,
            "by_status": by_status,
            "demo_booked": demos,
            "converted": converted,
            "conversion_rate": round(converted / total * 100, 1) if total else 0.0,
            "demo_rate": round(demos / total * 100, 1) if total else 0.0,
            "total_outreach": len(self._results),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_lead(self, lead: Lead) -> Optional[OutreachResult]:
        sequence = self._get_sequence_for_lead(lead)
        if not sequence:
            return None

        step = sequence.get_step(lead.sequence_step)
        if not step:
            lead.status = LeadStatus.LOST
            return None

        # Check delay
        if lead.last_contacted_at is not None:
            elapsed_hours = (datetime.utcnow() - lead.last_contacted_at).total_seconds() / 3600
            if elapsed_hours < step.delay_hours:
                return None  # Not yet due

        # Evaluate condition
        if step.condition and not evaluate_condition(step.condition, lead):
            lead.sequence_step += 1
            return None

        result = self._execute_step(lead, step)
        if result and result.success:
            lead.sequence_step += 1
            lead.last_contacted_at = datetime.utcnow()
            lead.status = LeadStatus.NURTURING if lead.status == LeadStatus.NEW else lead.status
            if self._on_lead_updated:
                self._on_lead_updated(lead)

        return result

    def _execute_step(self, lead: Lead, step: SequenceStep) -> Optional[OutreachResult]:
        booking_link = self._calendar.generate_booking_link(lead)

        if step.step_type == SequenceStepType.SEND_SMS:
            template_key = step.content.get("template", "sms_initial")
            body = render_template(template_key, lead, booking_link)
            if not lead.phone:
                return OutreachResult(
                    lead_id=lead.lead_id, channel=ChannelType.SMS,
                    step_type=step.step_type, success=False, error="no_phone"
                )
            res = self._sms.send(to=lead.phone, body=body)
            return OutreachResult(
                lead_id=lead.lead_id, channel=ChannelType.SMS,
                step_type=step.step_type, success=True,
                message_sid=res.get("sid"),
            )

        elif step.step_type == SequenceStepType.MAKE_CALL:
            script_key = step.content.get("script", "initial_consult_v1")
            if not lead.phone:
                return OutreachResult(
                    lead_id=lead.lead_id, channel=ChannelType.VOICE_CALL,
                    step_type=step.step_type, success=False, error="no_phone"
                )
            res = self._voice.call(to=lead.phone, script_key=script_key)
            return OutreachResult(
                lead_id=lead.lead_id, channel=ChannelType.VOICE_CALL,
                step_type=step.step_type, success=True,
                message_sid=res.get("sid"),
            )

        elif step.step_type == SequenceStepType.SEND_VIDEO:
            template_id = step.content.get(
                "template",
                DEFAULT_TEMPLATES.get(f"video_template_{lead.practice_area}",
                                      DEFAULT_TEMPLATES["video_template_default"])
            )
            if not lead.email:
                return OutreachResult(
                    lead_id=lead.lead_id, channel=ChannelType.VIDEO,
                    step_type=step.step_type, success=False, error="no_email"
                )
            res = self._video.send(
                to_email=lead.email, lead_name=lead.name, template_id=template_id
            )
            return OutreachResult(
                lead_id=lead.lead_id, channel=ChannelType.VIDEO,
                step_type=step.step_type, success=True,
                message_sid=res.get("video_id"),
            )

        elif step.step_type == SequenceStepType.BOOK_DEMO:
            return self._book_demo(lead)

        elif step.step_type == SequenceStepType.WAIT:
            return None  # Handled by delay_hours

        return None

    def _book_demo(self, lead: Lead) -> OutreachResult:
        booking_link = self._calendar.generate_booking_link(lead)
        lead.status = LeadStatus.DEMO_BOOKED
        lead.demo_booked_at = datetime.utcnow()
        if self._on_demo_booked:
            self._on_demo_booked(lead)
        logger.info("Demo booked for lead %s — link: %s", lead.lead_id, booking_link)
        # Send confirmation SMS
        if lead.phone:
            body = f"✅ Your free consultation is booked! Join here: {booking_link}"
            self._sms.send(to=lead.phone, body=body)
        return OutreachResult(
            lead_id=lead.lead_id, channel=ChannelType.SMS,
            step_type=SequenceStepType.BOOK_DEMO, success=True,
            demo_booked=True,
        )

    def _get_sequence_for_lead(self, lead: Lead) -> Optional[NurtureSequence]:
        # Try exact practice area match first
        seq = self._sequences.get(lead.practice_area)
        if seq and seq.active:
            return seq
        # Fall back to default
        return self._sequences.get("default")

    def _load_default_sequences(self) -> None:
        default_steps = [
            SequenceStep(
                step_id="s1", step_type=SequenceStepType.SEND_SMS,
                delay_hours=0, content={"template": "sms_initial"},
            ),
            SequenceStep(
                step_id="s2", step_type=SequenceStepType.MAKE_CALL,
                delay_hours=2, content={"script": "initial_consult_v1"},
            ),
            SequenceStep(
                step_id="s3", step_type=SequenceStepType.SEND_SMS,
                delay_hours=24, content={"template": "sms_followup_1"},
            ),
            SequenceStep(
                step_id="s4", step_type=SequenceStepType.SEND_VIDEO,
                delay_hours=48, content={"template": "general_intro_v1"},
            ),
            SequenceStep(
                step_id="s5", step_type=SequenceStepType.SEND_SMS,
                delay_hours=72, content={"template": "sms_followup_2"},
                condition="score >= 30",
            ),
            SequenceStep(
                step_id="s6", step_type=SequenceStepType.BOOK_DEMO,
                delay_hours=96, condition="score >= 60",
            ),
        ]
        hot_lead_steps = [
            SequenceStep(
                step_id="h1", step_type=SequenceStepType.MAKE_CALL,
                delay_hours=0, content={"script": "initial_consult_v1"},
            ),
            SequenceStep(
                step_id="h2", step_type=SequenceStepType.SEND_SMS,
                delay_hours=0, content={"template": "sms_hot_lead"},
            ),
            SequenceStep(
                step_id="h3", step_type=SequenceStepType.BOOK_DEMO,
                delay_hours=1,
            ),
        ]
        self._sequences["default"] = NurtureSequence(
            sequence_id="default", name="Default Nurture", practice_area="default",
            steps=default_steps,
        )
        self._sequences["personal_injury"] = NurtureSequence(
            sequence_id="pi", name="Personal Injury Hot Lead", practice_area="personal_injury",
            steps=hot_lead_steps,
        )

    def add_sequence(self, sequence: NurtureSequence) -> None:
        self._sequences[sequence.practice_area] = sequence
