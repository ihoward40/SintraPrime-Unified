"""Scan ORM model columns vs SQL migration schema for the canonical bootstrap tables."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./probe.db")
import portal.models
from portal.database import Base

# Build SQL schema column map from migration files
MIGRATIONS = [
    "portal/migrations/portal_schema.sql",
    "portal/migrations/add_evidence_snapshots.sql",
    "portal/migrations/add_audit_records.sql",
    "portal/migrations/add_mission_control_command_ledger.sql",
    "portal/migrations/add_mission_control_run_control_projection.sql",
]

sql_cols: dict[str, dict[str, str]] = {}  # table -> {col: type}

for mig in MIGRATIONS:
    text = Path(mig).read_text(encoding="utf-8")
    # find CREATE TABLE blocks
    for m in re.finditer(r"CREATE TABLE (?:IF NOT EXISTS )?([\w.]+)\s*\((.*?)\)\s*;", text, re.S):
        table = m.group(1).strip('"').split(".")[-1]
        body = m.group(2)
        if table not in sql_cols:
            sql_cols[table] = {}
        for line in body.splitlines():
            line = line.strip()
            if (
                not line
                or line.startswith("--")
                or line.startswith(("CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "INDEX"))
            ):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            col = parts[0].strip('"')
            typ = parts[1].upper()
            sql_cols[table][col] = typ

# Compare ORM
missing: list[str] = []
extra: list[str] = []
type_mismatch: list[str] = []
for table_name, table in Base.metadata.tables.items():
    if table_name not in sql_cols:
        missing.append(f"TABLE {table_name}: exists in ORM but NOT in SQL migrations")
        continue
    orm_cols = {c.name: str(c.type).upper() for c in table.columns}
    sql_tbl = sql_cols[table_name]
    for col in orm_cols:
        if col not in sql_tbl:
            missing.append(f"  {table_name}.{col} (ORM {orm_cols[col]}) MISSING in SQL")
    for col in sql_tbl:
        if col not in orm_cols:
            extra.append(f"  {table_name}.{col} (SQL {sql_tbl[col]}) not in ORM")

print("=== MISSING in SQL (ORM has, schema lacks) ===")
for m in missing:
    print(m)
print("\n=== In SQL but not ORM ===")
for e in extra:
    print(e)

if os.path.exists("probe.db"):
    os.remove("probe.db")
