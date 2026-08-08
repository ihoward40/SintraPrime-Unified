"""Sweep portal/models/*.py: replace String(36) with PortableUUIDString
for UUID-semantic columns (PK with uuid default or ForeignKey)."""

import re
from pathlib import Path

MODEL_DIR = Path("portal/models")


def sweep_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    orig = text

    # ensure PortableUUIDString is imported
    if "PortableUUIDString" not in text:
        if "from portal.models.types import" in text:
            text = text.replace(
                "from portal.models.types import",
                "from portal.models.types import PortableUUIDString,",
            )
        elif "from .types import" in text:
            text = text.replace(
                "from .types import",
                "from .types import PortableUUIDString,",
            )
        elif "from ..database import Base" in text:
            text = text.replace(
                "from ..database import Base",
                "from ..database import Base\nfrom ..models.types import PortableUUIDString",
            )
        else:
            import_idx = text.find("\nfrom ")
            if import_idx > 0:
                text = (
                    text[:import_idx]
                    + "\nfrom portal.models.types import PortableUUIDString"
                    + text[import_idx:]
                )
            import_idx = text.find("\nimport ")
            if import_idx > 0 and "PortableUUIDString" not in text:
                text = (
                    text[:import_idx]
                    + "\nfrom portal.models.types import PortableUUIDString"
                    + text[import_idx:]
                )

    # PK pattern: mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text = re.sub(
        r"mapped_column\(\s*String\(36\),\s*primary_key=True,\s*default=lambda:\s*str\(uuid\.uuid4\(\)\)\)",
        "mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)",
        text,
    )
    # PK pattern: mapped_column(String(36), primary_key=True, default=uuid.uuid4)
    text = re.sub(
        r"mapped_column\(\s*String\(36\),\s*primary_key=True,\s*default=uuid\.uuid4\)",
        "mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)",
        text,
    )

    # Single-line FK: mapped_column(String(36), ForeignKey(...), ...)
    def replace_single_fk(m):
        return m.group(0).replace("String(36)", "PortableUUIDString", 1)

    text = re.sub(
        r"mapped_column\(\s*String\(36\),\s*(ForeignKey\([^)]+\)[^,]*(?:,\s*\w+[^,]*)*)",
        replace_single_fk,
        text,
    )

    # Multi-line FK: mapped_column(\n        String(36),\n        ForeignKey(...),
    def replace_multi_fk(m):
        return m.group(0).replace("String(36)", "PortableUUIDString", 1)

    text = re.sub(
        r"mapped_column\(\s*\n\s*String\(36\),\s*\n\s*(ForeignKey)",
        replace_multi_fk,
        text,
    )

    # Simple: mapped_column(String(36), index=True, ...) — tenant_id without explicit FK
    text = re.sub(
        r"mapped_column\(\s*String\(36\),\s*index=True,\s*nullable=False\)",
        "mapped_column(PortableUUIDString, index=True, nullable=False)",
        text,
    )

    count = 0
    if text != orig:
        count = orig.count("String(36)") - text.count("String(36)")
        path.write_text(text, encoding="utf-8")
    return count


total = 0
files_touched = 0
for py in sorted(MODEL_DIR.glob("*.py")):
    if py.name.startswith("__") or py.name == "types.py":
        continue
    n = sweep_file(py)
    if n:
        print(f"  {py.name}: {n} replaced")
        total += n
        files_touched += 1
print(f"\nTotal: {total} String(36) -> PortableUUIDString across {files_touched} model files")
