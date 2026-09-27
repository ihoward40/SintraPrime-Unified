"""Canonical enums for the Collaborative Agent Fabric."""

from enum import Enum


class ChannelType(str, Enum):
    OPERATIONS = "operations"
    ENGINEERING = "engineering"
    RESEARCH = "research"
    LEGAL_DRAFTING = "legal_drafting"
    CONSUMER_REMEDY = "consumer_remedy"
    CONTENT = "content"
    SUPPORT = "support"
    PRIVATE = "private"
    SYSTEM = "system"


class ChannelVisibility(str, Enum):
    PRIVATE = "private"
    TENANT = "tenant"
    INVITE_ONLY = "invite_only"
    PUBLIC_READ = "public_read"


class ChannelStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


class ActorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"


class MembershipRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    CONTRIBUTOR = "contributor"
    OBSERVER = "observer"
    AGENT = "agent"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    LEFT = "left"
    REMOVED = "removed"
    BANNED = "banned"


class EventType(str, Enum):
    CHANNEL_MESSAGE_CREATED = "channel_message_created"
    CHANNEL_MEMBER_JOINED = "channel_member_joined"
    CHANNEL_MEMBER_LEFT = "channel_member_left"
    AGENT_MENTIONED = "agent_mentioned"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    ARTIFACT_CREATED = "artifact_created"
    REACTION_ADDED = "reaction_added"
    COMMAND_CREATED = "command_created"
    COMMAND_BLOCKED = "command_blocked"
    HANDOFF_CREATED = "handoff_created"
    HANDOFF_COMPLETED = "handoff_completed"
    HANDOFF_FAILED = "handoff_failed"
    AGENT_ADDED_TO_CHANNEL = "agent_added_to_channel"


class EventDispatchStatus(str, Enum):
    DISPATCHED = "dispatched"
    SKIPPED_NOT_SUBSCRIBED = "skipped_not_subscribed"
    SKIPPED_POLICY = "skipped_policy"
    SKIPPED_RATE_LIMIT = "skipped_rate_limit"
    SKIPPED_BUDGET = "skipped_budget"
    SKIPPED_LOOP_GUARD = "skipped_loop_guard"
    SKIPPED_DEDUP = "skipped_dedup"
    SKIPPED_AGENT_STOPPED = "skipped_agent_stopped"
    SKIPPED_SHADOW = "skipped_shadow"
    SKIPPED_NO_MEMBERSHIP = "skipped_no_membership"
    BLOCKED_KILL_SWITCH = "blocked_kill_switch"
    QUEUED = "queued"


class AgentResponseMode(str, Enum):
    MENTION_ONLY = "mention_only"
    OWNER_ONLY = "owner_only"
    ALLOWLIST = "allowlist"
    EVENT_TRIGGERED = "event_triggered"
    PASSIVE = "passive"
    ALL_MESSAGES = "all_messages"


class HandoffStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class RuntimeStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    FAULTED = "faulted"


class AgentPresenceState(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    THINKING = "thinking"
    RUNNING_TOOL = "running_tool"
    WAITING = "waiting"
    BLOCKED = "blocked"
    PAUSED = "paused"
    ERROR = "error"


class ContentType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"
    ARTIFACT = "artifact"
    WORKFLOW = "workflow"
    APPROVAL = "approval"
    AGENT_STATUS = "agent_status"


class HostType(str, Enum):
    LOCAL_WORKSTATION = "local_workstation"
    SERVER = "server"
    CONTAINER = "container"
    VPS = "vps"
    GPU_WORKER = "gpu_worker"
    CLOUD_RUNNER = "cloud_runner"


class HostTrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    BASIC = "basic"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"


class SecurityClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class TrustZone(str, Enum):
    T0_PUBLIC = "T0_public"
    T1_EXTERNAL_AUTHENTICATED = "T1_external_authenticated"
    T2_INTERNAL = "T2_internal"
    T3_SENSITIVE = "T3_sensitive"
    T4_RESTRICTED = "T4_restricted"


class QuietMode(str, Enum):
    QUIET = "quiet"
    NORMAL = "normal"
    ACTIVE = "active"


class NotificationThreshold(str, Enum):
    CRITICAL_ONLY = "critical_only"
    DECISION_REQUIRED = "decision_required"
    BLOCKING_FAILURE = "blocking_failure"
    BUDGET_WARNING = "budget_warning"
    SECURITY_EVENT = "security_event"
    MEANINGFUL_COMPLETION = "meaningful_completion"
    ALL = "all"
