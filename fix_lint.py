import re

print("=" * 60)
print("FIXING LINT VIOLATIONS")
print("=" * 60)

# FIX 1 & 2: evidence_snapshot_service.py (F821 + RUF012)
print("\n[1/3] evidence_snapshot_service.py (F821 + RUF012)")
with open('portal/services/evidence_snapshot_service.py', 'r') as f:
    content = f.read()

# Add ClassVar import after other imports
lines = content.split('\n')
insert_at = 0
for i, line in enumerate(lines):
    if line.startswith('from'):
        insert_at = i + 1

# Check if ClassVar already imported
if 'ClassVar' not in content:
    lines.insert(insert_at, 'from typing import ClassVar')
    content = '\n'.join(lines)
    print("  ✓ Added 'from typing import ClassVar'")

with open('portal/services/evidence_snapshot_service.py', 'w') as f:
    f.write(content)

# FIX 3: test_hash_boundary.py (RUF005)
print("\n[2/3] test_hash_boundary.py (RUF005)")
with open('portal/tests/test_hash_boundary.py', 'r') as f:
    content = f.read()

content = content.replace(
    'extended_items = sample_items + (',
    'extended_items = (*sample_items, '
)

with open('portal/tests/test_hash_boundary.py', 'w') as f:
    f.write(content)

print("  ✓ Replaced tuple concatenation with iterable unpacking")

# FIX 4: test_hash_boundary.py (B007)
print("\n[3/3] test_hash_boundary.py (B007)")
with open('portal/tests/test_hash_boundary.py', 'r') as f:
    content = f.read()

content = content.replace(
    'for version in range(1, 6):',
    'for _version in range(1, 6):'
)

with open('portal/tests/test_hash_boundary.py', 'w') as f:
    f.write(content)

print("  ✓ Renamed loop variable to '_version'")

print("\n" + "=" * 60)
print("ALL FIXES APPLIED")
print("=" * 60)
