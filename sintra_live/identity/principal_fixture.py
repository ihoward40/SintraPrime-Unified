"""Principal identity fixture for offline integration."""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PrincipalIdentity:
    """Immutable principal identity for offline missions."""
    principal_id: str
    session_id: str
    display_name: str
    authority_level: str
    verified_at: float
    verification_record_hash: str = ""
    session_binding: str = ""

    def __post_init__(self):
        if not self.verification_record_hash:
            content = f"{self.principal_id}|{self.session_id}|{self.authority_level}|{self.verified_at}"
            object.__setattr__(self, 'verification_record_hash', hashlib.sha256(content.encode()).hexdigest())
        if not self.session_binding:
            content = f"{self.principal_id}|{self.session_id}|{self.verified_at}"
            object.__setattr__(self, 'session_binding', hashlib.sha256(content.encode()).hexdigest()[:32])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "session_id": self.session_id,
            "display_name": self.display_name,
            "authority_level": self.authority_level,
            "verified_at": self.verified_at,
            "verification_record_hash": self.verification_record_hash,
            "session_binding": self.session_binding
        }


class PrincipalFixture:
    """Provides fixed principal identities for synthetic missions."""

    FIXTURES = {
        "principal-001": PrincipalIdentity(
            principal_id="principal-001",
            session_id="session-001",
            display_name="Isiah Howard",
            authority_level="PRINCIPAL",
            verified_at=time.time()
        ),
        "principal-002": PrincipalIdentity(
            principal_id="principal-002",
            session_id="session-002",
            display_name="Test Principal",
            authority_level="PRINCIPAL",
            verified_at=time.time()
        ),
    }

    @classmethod
    def get(cls, principal_id: str) -> PrincipalIdentity:
        if principal_id not in cls.FIXTURES:
            raise ValueError(f"Unknown principal fixture: {principal_id}")
        return cls.FIXTURES[principal_id]

    @classmethod
    def authenticate(cls, voice_input) -> PrincipalIdentity:
        """Authenticate principal from synthetic voice input."""
        return cls.get(voice_input.principal_id)

    @classmethod
    def is_valid(cls, identity: PrincipalIdentity) -> bool:
        """Validate that identity is a known fixture with current session."""
        return (
            identity.principal_id in cls.FIXTURES and
            identity.session_id == cls.FIXTURES[identity.principal_id].session_id
        )

    @classmethod
    def create_session_binding(cls, principal_id: str, session_id: str) -> str:
        """Create an explicit session binding hash."""
        content = f"{principal_id}|{session_id}|{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]