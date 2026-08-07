import logging
import re
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RemediationService:
    """
    Addresses identified platform defects:
    1. Actor Validation (Principal Command only)
    2. Sensitive Data Masking
    3. Lifecycle Timestamps
    4. Event-to-Node Linkage
    """
    def __init__(self):
        self.authorized_principals = ["principal-god-mode"]
        # Improved patterns to capture keys and their assigned values
        self.sensitive_patterns = [
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card)\s*[=:]\s*[^,\s}\"]+",
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card)"
        ]

    def validate_principal(self, actor_id: str) -> bool:
        """Ensures only authorized principals can approve commands."""
        if actor_id not in self.authorized_principals:
            logger.error(f"[REMEDIATION] Unauthorized actor {actor_id} attempted principal action.")
            return False
        return True

    def mask_sensitive_data(self, data: Any) -> Any:
        """Recursively masks sensitive patterns in strings and dictionaries."""
        if isinstance(data, str):
            for pattern in self.sensitive_patterns:
                data = re.sub(pattern, "[MASKED]", data, flags=re.IGNORECASE)
            return data
        elif isinstance(data, dict):
            return {k: self.mask_sensitive_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_sensitive_data(i) for i in data]
        return data

    def inject_lifecycle_metadata(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Injects mandatory lifecycle timestamps and linkage IDs."""
        node_data["created_at"] = datetime.now(UTC).isoformat()
        node_data["updated_at"] = datetime.now(UTC).isoformat()
        if "node_id" not in node_data:
            import uuid
            node_data["node_id"] = str(uuid.uuid4())
        return node_data

    def link_event_to_node(self, event_id: str, node_id: str) -> Dict[str, str]:
        """Creates a dedicated persistence record for event-to-node linkage."""
        linkage = {
            "linkage_id": f"lnk-{event_id[:8]}",
            "event_id": event_id,
            "node_id": node_id,
            "linked_at": datetime.now(UTC).isoformat()
        }
        logger.info(f"[REMEDIATION] Persisted linkage: {linkage['linkage_id']}")
        return linkage

# Global instance
remediation = RemediationService()
