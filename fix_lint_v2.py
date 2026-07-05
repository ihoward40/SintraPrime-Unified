import re

print("=" * 60)
print("FIXING LINT VIOLATIONS (v2)")
print("=" * 60)

# FIX 1 & 2: evidence_snapshot_service.py (F821 + RUF012)
print("\n[1/3] evidence_snapshot_service.py (F821 + RUF012)")
with open('portal/services/evidence_snapshot_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if ClassVar already imported
if 'from typing import ClassVar' not in content:
    # Find the last "from" import line
    lines = content.split('\n')
    last_from_import_idx = -1
    
    for i, line in enumerate(lines):
        if line.startswith('from ') and ' import ' in line:
            last_from_import_idx = i
    
    if last_from_import_idx >= 0:
        # Insert after the last from import
        lines.insert(last_from_import_idx + 1, 'from typing import ClassVar')
        content = '\n'.join(lines)
        with open('portal/services/evidence_snapshot_service.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✓ Added 'from typing import ClassVar'")
    else:
        print("  ⚠ Could not find import location")
else:
    print("  ℹ ClassVar already imported")

# FIX 3: test_hash_boundary.py (RUF005)
print("\n[2/3] test_hash_boundary.py (RUF005)")
with open('portal/tests/test_hash_boundary.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace tuple concatenation with iterable unpacking
# Pattern: "sample_items + (" → "(*sample_items, "
content = re.sub(
    r'sample_items\s*\+\s*\(',
    '(*sample_items, ',
    content
)

with open('portal/tests/test_hash_boundary.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("  ✓ Replaced tuple concatenation with iterable unpacking")

# FIX 4: test_hash_boundary.py (B007)
print("\n[3/3] test_hash_boundary.py (B007)")
with open('portal/tests/test_hash_boundary.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'for version in range(1, 6):',
    'for _version in range(1, 6):'
)

with open('portal/tests/test_hash_boundary.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("  ✓ Renamed loop variable to '_version'")

print("\n" + "=" * 60)
print("ALL FIXES APPLIED")
print("=" * 60)
