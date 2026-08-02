"""Deterministic, policy-first risk classifier for SP-VOICE-001.

Classification runs BEFORE any model-assisted interpretation (directive §3).
It is intentionally deterministic: given the same normalized intent it always
returns the same risk class, so the governance decision is reproducible and
auditable. Model assistance may only *refine wording* downstream; it can never
lower a risk class assigned here.

Precedence (highest wins): PROHIBITED > SENSITIVE_WRITE > WRITE > DRAFT > READ.
An intent that matches no known-safe pattern fails safe to SENSITIVE_WRITE so
that unknown requests require exact-target confirmation rather than silently
executing.

Patterns are regexes matched against the lowercased intent. Two-token patterns
(e.g. ``reveal ... secret``) tolerate intervening words so paraphrases like
"reveal the secret keys" still classify correctly, while single nouns like
"config file" do not trigger verb intents like "file a document".
"""

from __future__ import annotations

import re

from .command_envelope import RiskClass


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Class E — Prohibited. Refused and logged. (directive §3 Class E)
_PROHIBITED = _compile(
    [
        r"\bbypass\b",
        r"\b(skip|override|ignore)\b.*\bconfirm",
        r"\b(disable|turn off|stop)\b.*\b(audit|logging)\b",
        r"\b(reveal|expose|leak|dump|show|print)\b.*\b(secret|secrets|credential|credentials|private key|api key|token)\b",
        r"\bsilently\b",
        r"\bsecretly\b",
        r"\bwithout telling\b",
        r"\bescalate\b.*\b(permission|permissions|privilege|privileges|access)\b",
        r"\bgrant myself\b",
        r"\bkeylog\b",
        r"\bwiretap\b",
    ]
)

# Class D — Sensitive write. Requires exact-target confirmation. (directive §3 Class D)
_SENSITIVE_WRITE = _compile(
    [
        r"\bsend\b",
        r"\bpublish\b",
        r"\bpost\b",
        r"\btweet\b",
        r"\bpush\b",
        r"\bmerge\b",
        r"\bdeploy",
        r"\brelease\b.*\bproduction\b",
        r"\bopen (a |an )?(pull request|pr)\b",
        r"\bdelete\b",
        r"\bwipe\b",
        r"\bpurge\b",
        r"\bdrop table\b",
        r"\bremove permanently\b",
        r"\bchange\b.*\bpermission",
        r"\b(grant|revoke)\b.*\baccess\b",
        r"\bsubmit\b",
        r"\bfile (a |an |the )",
        r"\be-?file\b",
        r"\bpay\b",
        r"\bspend\b",
        r"\bpurchase\b",
        r"\bbuy\b",
        r"\btransfer funds\b",
        r"\bwire\b",
        r"\brefund\b",
    ]
)

# Class C — Write. Uses the same authorization rules as the typed workflow.
_WRITE = _compile(
    [
        r"\bmodify\b",
        r"\bedit\b",
        r"\bupdate\b",
        r"\brename\b",
        r"\bmove file\b",
        r"\b(create|new|checkout)\b.*\bbranch\b",
        r"\bcheckout -b\b",
        r"\brun (the )?tests?\b",
        r"\bexecute tests?\b",
        r"\badd (a )?task\b",
        r"\b(record|log) task\b",
        r"\bcommit\b",
        r"\bstage\b",
    ]
)

# Class B — Draft. May execute to draft state only.
_DRAFT = _compile(
    [
        r"\bdraft\b",
        r"\bprepare\b",
        r"\bcompose\b",
        r"\bwrite up\b",
        r"\bcreate (a )?(report|document|memo|summary)\b",
        r"\bchecklist\b",
    ]
)

# Class A — Read. May execute without a second confirmation on authorized resources.
_READ = _compile(
    [
        r"\b(show|display|read|view|get)\b",
        r"\b(find|search|locate)\b",
        r"\blook up\b",
        r"\bwhat('s| is| are)\b",
        r"\bstatus\b",
        r"\blist\b",
        r"\bsummari(ze|se|zing)\b",
        r"\bsummary\b",
    ]
)

# Ordered by precedence — first bucket that matches wins.
_ORDERED: list[tuple[list[re.Pattern[str]], RiskClass]] = [
    (_PROHIBITED, RiskClass.PROHIBITED),
    (_SENSITIVE_WRITE, RiskClass.SENSITIVE_WRITE),
    (_WRITE, RiskClass.WRITE),
    (_DRAFT, RiskClass.DRAFT),
    (_READ, RiskClass.READ),
]

# Fail-safe default when nothing matches: force exact-target confirmation.
_DEFAULT = RiskClass.SENSITIVE_WRITE


def classify(normalized_intent: str) -> RiskClass:
    """Return the deterministic risk class for a normalized intent.

    Empty or non-string input fails safe to ``SENSITIVE_WRITE``.
    """
    if not isinstance(normalized_intent, str) or not normalized_intent.strip():
        return _DEFAULT
    text = normalized_intent.strip().lower()
    for patterns, risk in _ORDERED:
        if any(p.search(text) for p in patterns):
            return risk
    return _DEFAULT
