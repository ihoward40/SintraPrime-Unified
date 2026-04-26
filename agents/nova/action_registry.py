"""Action Registry — Plugin system for registering and managing actions.

Provides a central registry where action handlers can be registered,
discovered, and invoked by the Nova execution engine.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("action_registry")
logger.setLevel(logging.INFO)


class ApprovalLevel(str, Enum):
    """Approval level required for an action."""
    AUTO = "AUTO"
    HUMAN = "HUMAN"
    LEGAL_REVIEW = "LEGAL_REVIEW"


class ActionCategory(str, Enum):
    """Categories for organizing actions."""
    DISPUTE = "dispute"
    LEGAL = "legal"
    NOTIFICATION = "notification"
    SCHEDULING = "scheduling"
    FINANCIAL = "financial"
    DOCUMENT = "document"


@dataclass
class ActionSpec:
    """Full specification of a registered action."""
    action_type: str
    name: str
    description: str
    category: str
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    approval_level: ApprovalLevel = ApprovalLevel.HUMAN
    handler: Optional[Callable] = None
    rollback_handler: Optional[Callable] = None
    validator: Optional[Callable] = None
    version: str = "1.0.0"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (excluding callables)."""
        d = asdict(self)
        d.pop("handler", None)
        d.pop("rollback_handler", None)
        d.pop("validator", None)
        return d


class ActionNotFoundError(Exception):
    """Raised when an action type is not found in the registry."""
    pass


class ActionAlreadyRegisteredError(Exception):
    """Raised when trying to register a duplicate action type."""
    pass


class ActionValidationError(Exception):
    """Raised when action parameters fail validation."""
    pass


class ActionRegistry:
    """Central registry for all available real-world actions.

    Provides plugin-style registration, discovery, validation, and
    retrieval of action handlers.
    """

    def __init__(self):
        self._actions: Dict[str, ActionSpec] = {}
        self._categories: Dict[str, List[str]] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_register": [],
            "post_register": [],
            "pre_execute": [],
            "post_execute": [],
        }
        logger.info("ActionRegistry initialized.")

    def register_action(
        self,
        action_spec: ActionSpec,
        overwrite: bool = False,
    ) -> None:
        """Register a new action in the registry.

        Args:
            action_spec: The action specification to register.
            overwrite: If True, overwrite existing registration.

        Raises:
            ActionAlreadyRegisteredError: If action already exists and overwrite is False.
        """
        action_type = action_spec.action_type

        # Run pre-register hooks
        for hook in self._hooks.get("pre_register", []):
            hook(action_spec)

        if action_type in self._actions and not overwrite:
            raise ActionAlreadyRegisteredError(
                f"Action '{action_type}' is already registered. Use overwrite=True to replace."
            )

        self._actions[action_type] = action_spec

        # Update category index
        cat = action_spec.category
        if cat not in self._categories:
            self._categories[cat] = []
        if action_type not in self._categories[cat]:
            self._categories[cat].append(action_type)

        # Run post-register hooks
        for hook in self._hooks.get("post_register", []):
            hook(action_spec)

        logger.info("Registered action: %s (%s)", action_type, action_spec.name)

    def unregister_action(self, action_type: str) -> bool:
        """Remove an action from the registry."""
        if action_type not in self._actions:
            return False

        spec = self._actions.pop(action_type)
        cat = spec.category
        if cat in self._categories and action_type in self._categories[cat]:
            self._categories[cat].remove(action_type)

        logger.info("Unregistered action: %s", action_type)
        return True

    def get_action(self, action_type: str) -> ActionSpec:
        """Retrieve an action specification by type.

        Raises:
            ActionNotFoundError: If the action type is not registered.
        """
        if action_type not in self._actions:
            raise ActionNotFoundError(f"Action '{action_type}' is not registered.")
        return self._actions[action_type]

    def has_action(self, action_type: str) -> bool:
        """Check if an action type is registered."""
        return action_type in self._actions

    def list_actions(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available actions, optionally filtered by category."""
        if category:
            action_types = self._categories.get(category, [])
            specs = [self._actions[at] for at in action_types if at in self._actions]
        else:
            specs = list(self._actions.values())

        return [
            {
                "action_type": s.action_type,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "approval_level": s.approval_level.value,
                "required_params": s.required_params,
                "optional_params": s.optional_params,
                "enabled": s.enabled,
                "version": s.version,
            }
            for s in specs
            if s.enabled
        ]

    def list_categories(self) -> List[str]:
        """Return list of all registered categories."""
        return list(self._categories.keys())

    def validate_params(self, action_type: str, params: Dict[str, Any]) -> List[str]:
        """Validate parameters for an action.

        Returns list of validation errors (empty if valid).
        """
        spec = self.get_action(action_type)
        errors: List[str] = []

        # Check required params
        for p in spec.required_params:
            if p not in params:
                errors.append(f"Missing required parameter: {p}")
            elif params[p] is None or params[p] == "":
                errors.append(f"Required parameter '{p}' cannot be empty")

        # Run custom validator if present
        if spec.validator:
            try:
                custom_errors = spec.validator(params)
                if custom_errors:
                    errors.extend(custom_errors)
            except Exception as exc:
                errors.append(f"Validator error: {exc}")

        return errors

    def enable_action(self, action_type: str) -> bool:
        """Enable a disabled action."""
        if action_type in self._actions:
            self._actions[action_type].enabled = True
            return True
        return False

    def disable_action(self, action_type: str) -> bool:
        """Disable an action (still registered but won't appear in listings)."""
        if action_type in self._actions:
            self._actions[action_type].enabled = False
            return True
        return False

    def add_hook(self, event: str, callback: Callable) -> None:
        """Add a lifecycle hook."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "total_actions": len(self._actions),
            "enabled_actions": sum(1 for a in self._actions.values() if a.enabled),
            "disabled_actions": sum(1 for a in self._actions.values() if not a.enabled),
            "categories": {cat: len(types) for cat, types in self._categories.items()},
            "approval_levels": {
                level.value: sum(1 for a in self._actions.values() if a.approval_level == level)
                for level in ApprovalLevel
            },
        }

    def export_schema(self) -> Dict[str, Any]:
        """Export the full registry schema for documentation."""
        return {
            "registry_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "actions": {at: spec.to_dict() for at, spec in self._actions.items()},
            "categories": dict(self._categories),
            "stats": self.get_stats(),
        }
