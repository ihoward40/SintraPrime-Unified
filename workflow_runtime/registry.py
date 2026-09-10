"""Workflow definition registry.

Loads YAML definitions from a directory tree, validates them,
stores them in-memory keyed by (name, version, source_hash).
Re-registering the same (name, hash) is idempotent.
"""

from __future__ import annotations

from pathlib import Path

from .models import WorkflowDefinition
from .parser import parse_workflow
from .validator import ValidationError, validate_workflow


class WorkflowRegistry:
    """In-memory registry of validated workflow definitions."""

    def __init__(self) -> None:
        self._defs: dict[str, WorkflowDefinition] = {}  # key = name

    def register(self, defn: WorkflowDefinition) -> None:
        result = validate_workflow(defn)
        if not result.valid:
            raise ValidationError(f"Cannot register {defn.name!r}: {'; '.join(result.errors)}")
        existing = self._defs.get(defn.name)
        if existing:
            if existing.source_hash == defn.source_hash:
                return  # idempotent
            if existing.version >= defn.version:
                raise ValidationError(
                    f"Cannot register {defn.name!r} v{defn.version}: "
                    f"v{existing.version} is already registered with a different hash"
                )
        self._defs[defn.name] = defn

    def get(self, name: str) -> WorkflowDefinition | None:
        return self._defs.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._defs.keys())

    def __len__(self) -> int:
        return len(self._defs)


def load_defaults(
    defaults_dir: Path | str,
    registry: WorkflowRegistry | None = None,
) -> WorkflowRegistry:
    """Load all YAML files from a defaults directory into a registry."""
    defaults_dir = Path(defaults_dir)
    reg = registry or WorkflowRegistry()
    if not defaults_dir.is_dir():
        return reg
    for yaml_file in sorted(defaults_dir.glob("*.yaml")):
        defn = parse_workflow(yaml_file)
        reg.register(defn)
    for yml_file in sorted(defaults_dir.glob("*.yml")):
        defn = parse_workflow(yml_file)
        reg.register(defn)
    return reg
