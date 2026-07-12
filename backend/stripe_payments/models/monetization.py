"""Models for monetization → case start workflow."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .subscription import Tier


class StartCaseRequest(BaseModel):
    """Payload that Make (or other automation) sends to start a new case after payment."""

    tier: Tier
    email: str = Field(description="Client email used for onboarding handoff.")
    payment_session_id: str = Field(
        min_length=3,
        max_length=160,
        description="Verified payment/session/event identifier used for idempotency.",
    )

    # Optional / best-effort intake data. Keep it minimal and non-legal.
    client_name: str | None = None
    phone: str | None = None

    # If provided, lets you control the case directory name (must be unique).
    case_id: str | None = None

    # Non-legal metadata used to parameterize drafting templates.
    case_type: str | None = Field(
        default=None,
        description="Operational case type used by the draft generator.",
    )
    matter_type: str | None = Field(
        default="unspecified",
        description="Matter type label used in drafts (draft-only; not a legal determination).",
    )
    creditor_name: str | None = Field(
        default="unknown_creditor",
        description="Creditor/defendant display name for drafts (may be refined later).",
    )
    court: str | None = Field(default=None, description="Court name required for drafts.")
    jurisdiction: str | None = Field(default=None, description="Court jurisdiction required for drafts.")
    venue: str | None = Field(default=None, description="Venue required for drafts.")


class StartCaseResponse(BaseModel):
    """Response returned back to Make after case start + draft generation."""

    ok: bool
    case_id: str

    initialization_ledgers: list[dict] = Field(default_factory=list)

    draft_generation: dict | None = None
    errors: list[str] | None = None
