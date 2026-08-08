"""Second sweep: convert remaining PK String(36) columns to PortableUUIDString."""
import re
from pathlib import Path

MODEL_DIR = Path("portal/models")

def sweep_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    orig = text

    if "PortableUUIDString" not in text:
        if "from portal.models.types import" in text:
            text = text.replace("from portal.models.types import",
                                "from portal.models.types import PortableUUIDString,")
        elif "from .types import" in text:
            text = text.replace("from .types import",
                                "from .types import PortableUUIDString,")
        elif "from ..database import Base" in text:
            text = text.replace("from ..database import Base",
                                "from ..database import Base\nfrom ..models.types import PortableUUIDString")

    # Any remaining String(36), primary_key=True (various default patterns)
    text = re.sub(
        r'mapped_column\(\s*String\(36\),\s*primary_key=True',
        'mapped_column(PortableUUIDString, primary_key=True',
        text,
    )

    count = 0
    if text != orig:
        count = orig.count("String(36)") - text.count("String(36)")
        path.write_text(text, encoding="utf-8")
    return count

total = 0
for py in sorted(MODEL_DIR.glob("*.py")):
    if py.name.startswith("__") or py.name == "types.py":
        continue
    n = sweep_file(py)
    if n:
        print(f"  {py.name}: {n} more replaced")
        total += 1
print(f"\nTotal: {total} additional PK columns converted")
