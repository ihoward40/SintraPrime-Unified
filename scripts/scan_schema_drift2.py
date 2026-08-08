"""Compare ORM column types vs SQL schema for canonical tables (type-level)."""
import re, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./probe.db")
from portal.database import Base
import portal.models  # noqa

MIGRATIONS = [
    "portal/migrations/portal_schema.sql",
    "portal/migrations/add_evidence_snapshots.sql",
    "portal/migrations/add_audit_records.sql",
    "portal/migrations/add_mission_control_command_ledger.sql",
    "portal/migrations/add_mission_control_run_control_projection.sql",
]
sql_cols = {}
for mig in MIGRATIONS:
    text = Path(mig).read_text(encoding="utf-8")
    for m in re.finditer(r"CREATE TABLE (?:IF NOT EXISTS )?([\w.]+)\s*\((.*?)\)\s*;", text, re.S):
        table = m.group(1).strip('"').split(".")[-1]
        body = m.group(2)
        sql_cols.setdefault(table, {})
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("--") or line.startswith(("CONSTRAINT","PRIMARY","UNIQUE","FOREIGN","CHECK","INDEX")):
                continue
            parts = line.split()
            if len(parts) < 2: continue
            sql_cols[table][parts[0].strip('"')] = parts[1].upper()

def norm(t):
    t = t.upper()
    for a, b in [("VARCHAR","VARCHAR"),("CHARACTER VARYING","VARCHAR"),("TIMESTAMPTZ","DATETIME"),("TIMESTAMP","DATETIME"),("JSONB","JSON"),("DOUBLE PRECISION","FLOAT"),("NUMERIC","FLOAT"),("DECIMAL","FLOAT"),("INTEGER","INTEGER"),("BIGINT","INTEGER"),("SMALLINT","INTEGER"),("BOOLEAN","BOOLEAN"),("UUID","VARCHAR"),("TEXT","TEXT"),("INET","VARCHAR"),("DATE","DATE"),("BYTEA","BLOB")]:
        t = t.replace(a, b)
    return t

issues = []
for table_name, table in Base.metadata.tables.items():
    if table_name not in sql_cols: continue
    for col in table.columns:
        if col.name not in sql_cols[table_name]: continue
        orm_t = norm(str(col.type))
        sql_t = norm(sql_cols[table_name][col.name])
        if orm_t.split("(")[0] != sql_t.split("(")[0]:
            issues.append(f"{table_name}.{col.name}: ORM {str(col.type)} vs SQL {sql_cols[table_name][col.name]}")
print(f"type mismatches: {len(issues)}")
for i in issues:
    print(" ", i)
if os.path.exists("probe.db"): os.remove("probe.db")
