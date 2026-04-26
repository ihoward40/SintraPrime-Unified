"""
DatabaseBuilder — Auto-generates Database Schemas for SintraPrime App Builder
=============================================================================
Generates SQLite databases, SQL migrations, and FastAPI routes from
natural language descriptions or predefined legal/financial schemas.
"""

from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .app_types import Column, DatabaseSchema, Relationship, Table


class DatabaseBuilder:
    """
    Auto-generates database schemas optimized for legal and financial applications.

    Capabilities:
    - Parse natural language to schema
    - Generate SQLite databases
    - Write SQL migration files
    - Seed realistic sample data
    - Generate FastAPI REST endpoints
    """

    # ------------------------------------------------------------------
    # Pre-built Legal & Financial Schema Libraries
    # ------------------------------------------------------------------

    @staticmethod
    def _legal_clients_table() -> Table:
        return Table(
            name="clients",
            description="Law firm client records",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("first_name", "TEXT", nullable=False),
                Column("last_name", "TEXT", nullable=False),
                Column("email", "TEXT", unique=True),
                Column("phone", "TEXT"),
                Column("address", "TEXT"),
                Column("city", "TEXT"),
                Column("state", "TEXT"),
                Column("zip_code", "TEXT"),
                Column("date_of_birth", "TEXT"),
                Column("ssn_last4", "TEXT"),
                Column("client_type", "TEXT", default="'individual'"),  # individual, entity
                Column("status", "TEXT", default="'active'"),
                Column("source", "TEXT"),  # referral, website, etc.
                Column("notes", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
                Column("updated_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["email", "last_name", "status"],
        )

    @staticmethod
    def _legal_matters_table() -> Table:
        return Table(
            name="matters",
            description="Legal matters/cases",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("client_id", "TEXT", nullable=False, foreign_key="clients.id"),
                Column("matter_number", "TEXT", unique=True),
                Column("title", "TEXT", nullable=False),
                Column("matter_type", "TEXT"),  # estate, trust, probate, litigation
                Column("status", "TEXT", default="'open'"),  # open, closed, on_hold
                Column("jurisdiction", "TEXT"),
                Column("court", "TEXT"),
                Column("case_number", "TEXT"),
                Column("attorney_assigned", "TEXT"),
                Column("paralegal_assigned", "TEXT"),
                Column("open_date", "TEXT"),
                Column("close_date", "TEXT"),
                Column("description", "TEXT"),
                Column("billable_hours", "REAL", default="0.0"),
                Column("flat_fee", "REAL", default="0.0"),
                Column("total_billed", "REAL", default="0.0"),
                Column("total_collected", "REAL", default="0.0"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
                Column("updated_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["client_id", "status", "matter_type", "attorney_assigned"],
        )

    @staticmethod
    def _legal_documents_table() -> Table:
        return Table(
            name="documents",
            description="Legal documents and files",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("matter_id", "TEXT", nullable=False, foreign_key="matters.id"),
                Column("client_id", "TEXT", foreign_key="clients.id"),
                Column("name", "TEXT", nullable=False),
                Column("document_type", "TEXT"),  # will, trust, contract, pleading, etc.
                Column("file_path", "TEXT"),
                Column("file_size_bytes", "INTEGER"),
                Column("mime_type", "TEXT"),
                Column("status", "TEXT", default="'draft'"),  # draft, signed, filed, archived
                Column("signed_by", "TEXT"),
                Column("signed_date", "TEXT"),
                Column("notarized", "BOOLEAN", default="0"),
                Column("notarized_date", "TEXT"),
                Column("tags", "TEXT"),  # JSON array
                Column("notes", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
                Column("updated_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["matter_id", "client_id", "document_type", "status"],
        )

    @staticmethod
    def _legal_deadlines_table() -> Table:
        return Table(
            name="deadlines",
            description="Court deadlines and task due dates",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("matter_id", "TEXT", nullable=False, foreign_key="matters.id"),
                Column("title", "TEXT", nullable=False),
                Column("deadline_type", "TEXT"),  # court, filing, internal, client
                Column("due_date", "TEXT", nullable=False, index=True),
                Column("completed", "BOOLEAN", default="0"),
                Column("completed_date", "TEXT"),
                Column("priority", "TEXT", default="'normal'"),  # low, normal, high, critical
                Column("assigned_to", "TEXT"),
                Column("reminder_days", "INTEGER", default="3"),
                Column("notes", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["matter_id", "due_date", "completed"],
        )

    @staticmethod
    def _legal_billing_table() -> Table:
        return Table(
            name="billing_entries",
            description="Time entries and billing records",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("matter_id", "TEXT", nullable=False, foreign_key="matters.id"),
                Column("client_id", "TEXT", nullable=False, foreign_key="clients.id"),
                Column("attorney", "TEXT"),
                Column("entry_date", "TEXT", nullable=False),
                Column("hours", "REAL", nullable=False),
                Column("hourly_rate", "REAL"),
                Column("amount", "REAL"),
                Column("description", "TEXT"),
                Column("billing_code", "TEXT"),
                Column("status", "TEXT", default="'unbilled'"),  # unbilled, billed, paid, written_off
                Column("invoice_id", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["matter_id", "client_id", "status", "entry_date"],
        )

    @staticmethod
    def _trusts_table() -> Table:
        return Table(
            name="trusts",
            description="Trust entities and details",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("trust_name", "TEXT", nullable=False),
                Column("trust_type", "TEXT"),  # revocable, irrevocable, testamentary, special_needs
                Column("grantor_client_id", "TEXT", foreign_key="clients.id"),
                Column("trustee_name", "TEXT"),
                Column("successor_trustee", "TEXT"),
                Column("date_established", "TEXT"),
                Column("state_of_formation", "TEXT"),
                Column("tax_id", "TEXT"),
                Column("total_assets", "REAL", default="0.0"),
                Column("status", "TEXT", default="'active'"),
                Column("distribution_rules", "TEXT"),  # JSON
                Column("notes", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["grantor_client_id", "trust_type", "status"],
        )

    @staticmethod
    def _beneficiaries_table() -> Table:
        return Table(
            name="beneficiaries",
            description="Trust beneficiaries",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("trust_id", "TEXT", nullable=False, foreign_key="trusts.id"),
                Column("name", "TEXT", nullable=False),
                Column("relationship", "TEXT"),
                Column("share_percentage", "REAL"),
                Column("distribution_type", "TEXT"),  # percentage, fixed_amount, discretionary
                Column("contact_info", "TEXT"),  # JSON
                Column("notes", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["trust_id"],
        )

    @staticmethod
    def _financial_accounts_table() -> Table:
        return Table(
            name="accounts",
            description="Financial accounts",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("user_id", "TEXT", nullable=False),
                Column("institution_name", "TEXT"),
                Column("account_name", "TEXT", nullable=False),
                Column("account_type", "TEXT"),  # checking, savings, investment, credit, loan
                Column("account_number_last4", "TEXT"),
                Column("balance", "REAL", default="0.0"),
                Column("credit_limit", "REAL"),
                Column("interest_rate", "REAL"),
                Column("currency", "TEXT", default="'USD'"),
                Column("is_asset", "BOOLEAN", default="1"),
                Column("plaid_account_id", "TEXT"),
                Column("last_synced", "DATETIME"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["user_id", "account_type"],
        )

    @staticmethod
    def _financial_transactions_table() -> Table:
        return Table(
            name="transactions",
            description="Financial transactions",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("account_id", "TEXT", nullable=False, foreign_key="accounts.id"),
                Column("user_id", "TEXT", nullable=False),
                Column("amount", "REAL", nullable=False),
                Column("transaction_type", "TEXT"),  # income, expense, transfer
                Column("category", "TEXT"),
                Column("subcategory", "TEXT"),
                Column("description", "TEXT"),
                Column("merchant", "TEXT"),
                Column("transaction_date", "TEXT", nullable=False),
                Column("posted_date", "TEXT"),
                Column("pending", "BOOLEAN", default="0"),
                Column("tags", "TEXT"),  # JSON array
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
            indexes=["account_id", "user_id", "transaction_date", "category"],
        )

    # ------------------------------------------------------------------
    # Schema Factory
    # ------------------------------------------------------------------

    def from_description(self, description: str) -> DatabaseSchema:
        """
        Generate a database schema from a natural language description.
        Detects the domain (legal/financial/trust) and returns appropriate schema.
        """
        desc_lower = description.lower()

        tables = []
        relationships = []

        # Always include a users/settings table
        tables.append(Table(
            name="users",
            description="System users",
            columns=[
                Column("id", "TEXT", primary_key=True, nullable=False),
                Column("email", "TEXT", unique=True, nullable=False),
                Column("name", "TEXT"),
                Column("role", "TEXT", default="'user'"),
                Column("password_hash", "TEXT"),
                Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
            ],
        ))

        # Legal domain
        if any(k in desc_lower for k in ["law", "legal", "attorney", "matter", "case", "client portal"]):
            tables += [
                self._legal_clients_table(),
                self._legal_matters_table(),
                self._legal_documents_table(),
                self._legal_deadlines_table(),
                self._legal_billing_table(),
            ]
            relationships += [
                Relationship("matters", "clients", "many_to_one", "client_id", "id"),
                Relationship("documents", "matters", "many_to_one", "matter_id", "id"),
                Relationship("deadlines", "matters", "many_to_one", "matter_id", "id"),
                Relationship("billing_entries", "matters", "many_to_one", "matter_id", "id"),
            ]

        # Trust domain
        if any(k in desc_lower for k in ["trust", "estate", "probate", "beneficiar", "trustee"]):
            tables += [self._trusts_table(), self._beneficiaries_table()]
            relationships.append(
                Relationship("beneficiaries", "trusts", "many_to_one", "trust_id", "id")
            )
            if not any(t.name == "clients" for t in tables):
                tables.append(self._legal_clients_table())

        # Financial domain
        if any(k in desc_lower for k in ["finance", "financial", "account", "budget", "investment", "transaction"]):
            tables += [
                self._financial_accounts_table(),
                self._financial_transactions_table(),
            ]
            relationships.append(
                Relationship("transactions", "accounts", "many_to_one", "account_id", "id")
            )

        # If nothing detected, use a generic schema
        if len(tables) == 1:
            tables.append(Table(
                name="records",
                description="Generic records",
                columns=[
                    Column("id", "TEXT", primary_key=True, nullable=False),
                    Column("title", "TEXT", nullable=False),
                    Column("description", "TEXT"),
                    Column("status", "TEXT", default="'active'"),
                    Column("created_at", "DATETIME", default="CURRENT_TIMESTAMP"),
                ],
            ))

        schema_name = "sintra_app"
        for keyword, name in [("legal", "legal_portal"), ("trust", "trust_manager"),
                               ("financial", "financial_dashboard"), ("crm", "client_crm")]:
            if keyword in desc_lower:
                schema_name = name
                break

        return DatabaseSchema(
            name=schema_name,
            tables=tables,
            relationships=relationships,
            description=f"Auto-generated schema for: {description[:100]}",
        )

    # ------------------------------------------------------------------
    # SQLite Generator
    # ------------------------------------------------------------------

    def generate_sqlite(self, schema: DatabaseSchema, db_path: str) -> None:
        """Create a SQLite database from a schema definition."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.executescript("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")

        for table in schema.tables:
            ddl = self._table_to_ddl(table)
            cursor.execute(ddl)

            # Create indexes
            for idx_col in table.indexes:
                idx_name = f"idx_{table.name}_{idx_col}"
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table.name} ({idx_col})"
                )

        conn.commit()
        conn.close()

    def _table_to_ddl(self, table: Table) -> str:
        """Convert a Table to SQLite DDL."""
        col_defs = []
        for col in table.columns:
            parts = [col.name, col.type]
            if col.primary_key:
                parts.append("PRIMARY KEY")
            if not col.nullable and not col.primary_key:
                parts.append("NOT NULL")
            if col.unique and not col.primary_key:
                parts.append("UNIQUE")
            if col.default is not None:
                parts.append(f"DEFAULT {col.default}")
            if col.foreign_key:
                ref_table, ref_col = col.foreign_key.split(".")
                parts.append(f"REFERENCES {ref_table}({ref_col})")
            col_defs.append("  " + " ".join(parts))

        return f"CREATE TABLE IF NOT EXISTS {table.name} (\n{(chr(44) + chr(10)).join(col_defs)}\n);"

    # ------------------------------------------------------------------
    # SQL Migration Generator
    # ------------------------------------------------------------------

    def generate_migration(self, schema: DatabaseSchema) -> str:
        """Generate a SQL migration file."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        lines = [
            f"-- SintraPrime Migration: {schema.name}",
            f"-- Generated: {datetime.now().isoformat()}",
            f"-- Schema version: {ts}",
            "",
            "PRAGMA journal_mode=WAL;",
            "PRAGMA foreign_keys=ON;",
            "",
        ]
        for table in schema.tables:
            lines.append(f"-- Table: {table.name}")
            if table.description:
                lines.append(f"-- {table.description}")
            lines.append(self._table_to_ddl(table))
            for idx_col in table.indexes:
                lines.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{table.name}_{idx_col} "
                    f"ON {table.name} ({idx_col});"
                )
            lines.append("")

        # Relationships as comments
        if schema.relationships:
            lines.append("-- Relationships:")
            for r in schema.relationships:
                lines.append(
                    f"--   {r.from_table}.{r.from_column} -> {r.to_table}.{r.to_column} ({r.relationship_type})"
                )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Sample Data Seeder
    # ------------------------------------------------------------------

    def seed_sample_data(self, db_path: str, schema: DatabaseSchema) -> None:
        """Seed the database with realistic sample data."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        table_names = [t.name for t in schema.tables]

        if "clients" in table_names:
            self._seed_clients(cursor)
        if "matters" in table_names:
            self._seed_matters(cursor)
        if "documents" in table_names:
            self._seed_documents(cursor)
        if "deadlines" in table_names:
            self._seed_deadlines(cursor)
        if "trusts" in table_names:
            self._seed_trusts(cursor)
        if "accounts" in table_names:
            self._seed_accounts(cursor)
        if "transactions" in table_names:
            self._seed_transactions(cursor)

        conn.commit()
        conn.close()

    def _seed_clients(self, cursor: sqlite3.Cursor) -> None:
        clients = [
            (str(uuid.uuid4()), "James", "Morrison", "james.morrison@email.com", "201-555-0100", "Newark", "NJ", "individual", "active"),
            (str(uuid.uuid4()), "Sophia", "Chen", "sophia.chen@email.com", "973-555-0200", "Newark", "NJ", "individual", "active"),
            (str(uuid.uuid4()), "Marcus", "Williams", "marcus.williams@email.com", "862-555-0300", "Orange", "NJ", "individual", "active"),
            (str(uuid.uuid4()), "Elena", "Ramirez", "elena.ramirez@email.com", "908-555-0400", "Elizabeth", "NJ", "individual", "active"),
            (str(uuid.uuid4()), "Thompson Family", "Trust", "thompson.trust@email.com", "201-555-0500", "Montclair", "NJ", "entity", "active"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO clients (id, first_name, last_name, email, phone, city, state, client_type, status) VALUES (?,?,?,?,?,?,?,?,?)",
            clients,
        )

    def _seed_matters(self, cursor: sqlite3.Cursor) -> None:
        client_rows = cursor.execute("SELECT id FROM clients LIMIT 5").fetchall()
        matter_types = ["estate_planning", "trust_administration", "probate", "debt_settlement", "contract_review"]
        statuses = ["open", "open", "open", "closed", "on_hold"]
        for i, (cid,) in enumerate(client_rows):
            cursor.execute(
                "INSERT OR IGNORE INTO matters (id, client_id, matter_number, title, matter_type, status, jurisdiction, attorney_assigned, open_date) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), cid, f"M-2026-{i+1:04d}",
                    f"Matter {i+1} - {matter_types[i % len(matter_types)].replace('_', ' ').title()}",
                    matter_types[i % len(matter_types)],
                    statuses[i % len(statuses)],
                    "New Jersey",
                    "Jane Doe, Esq.",
                    (date.today() - timedelta(days=random.randint(10, 365))).isoformat(),
                ),
            )

    def _seed_documents(self, cursor: sqlite3.Cursor) -> None:
        matter_rows = cursor.execute("SELECT id, client_id FROM matters LIMIT 5").fetchall()
        doc_types = ["will", "trust_agreement", "power_of_attorney", "healthcare_directive", "deed"]
        for i, (mid, cid) in enumerate(matter_rows):
            cursor.execute(
                "INSERT OR IGNORE INTO documents (id, matter_id, client_id, name, document_type, status) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), mid, cid, f"{doc_types[i % len(doc_types)].replace('_', ' ').title()} - Draft", doc_types[i % len(doc_types)], "draft"),
            )

    def _seed_deadlines(self, cursor: sqlite3.Cursor) -> None:
        matter_rows = cursor.execute("SELECT id FROM matters LIMIT 5").fetchall()
        for i, (mid,) in enumerate(matter_rows):
            cursor.execute(
                "INSERT OR IGNORE INTO deadlines (id, matter_id, title, deadline_type, due_date, priority) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), mid, f"Filing Deadline #{i+1}", "court",
                 (date.today() + timedelta(days=random.randint(7, 90))).isoformat(),
                 random.choice(["normal", "high", "critical"])),
            )

    def _seed_trusts(self, cursor: sqlite3.Cursor) -> None:
        client_rows = cursor.execute("SELECT id FROM clients LIMIT 3").fetchall()
        trust_types = ["revocable", "irrevocable", "testamentary"]
        for i, (cid,) in enumerate(client_rows):
            cursor.execute(
                "INSERT OR IGNORE INTO trusts (id, trust_name, trust_type, grantor_client_id, trustee_name, date_established, state_of_formation, total_assets, status) VALUES (?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), f"Family Trust #{i+1}", trust_types[i % len(trust_types)], cid,
                 "Jane Doe, Esq.", date(2020 + i, 1, 15).isoformat(), "NJ",
                 random.uniform(100000, 5000000), "active"),
            )

    def _seed_accounts(self, cursor: sqlite3.Cursor) -> None:
        user_id = str(uuid.uuid4())
        accounts = [
            (str(uuid.uuid4()), user_id, "Chase Bank", "Primary Checking", "checking", 15420.50, True),
            (str(uuid.uuid4()), user_id, "Chase Bank", "High-Yield Savings", "savings", 82300.00, True),
            (str(uuid.uuid4()), user_id, "Fidelity", "Investment Portfolio", "investment", 245000.00, True),
            (str(uuid.uuid4()), user_id, "Capital One", "Venture Card", "credit", -4200.00, False),
        ]
        for acc in accounts:
            cursor.execute(
                "INSERT OR IGNORE INTO accounts (id, user_id, institution_name, account_name, account_type, balance, is_asset) VALUES (?,?,?,?,?,?,?)",
                acc,
            )

    def _seed_transactions(self, cursor: sqlite3.Cursor) -> None:
        acc_rows = cursor.execute("SELECT id, user_id FROM accounts LIMIT 1").fetchall()
        if not acc_rows:
            return
        acc_id, user_id = acc_rows[0]
        categories = ["housing", "food", "transportation", "healthcare", "entertainment", "income"]
        for i in range(20):
            amount = random.uniform(-500, 5000) if i % 5 == 0 else random.uniform(-200, -10)
            cursor.execute(
                "INSERT OR IGNORE INTO transactions (id, account_id, user_id, amount, transaction_type, category, description, transaction_date) VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), acc_id, user_id, round(amount, 2),
                 "income" if amount > 0 else "expense",
                 random.choice(categories),
                 f"Transaction {i+1}",
                 (date.today() - timedelta(days=i*2)).isoformat()),
            )

    # ------------------------------------------------------------------
    # FastAPI Route Generator
    # ------------------------------------------------------------------

    def generate_api_endpoints(self, schema: DatabaseSchema) -> str:
        """Generate FastAPI router code for all schema tables."""
        routes = []
        for table in schema.tables:
            routes.append(self._generate_table_routes(table))

        imports = """\"\"\"
Auto-generated FastAPI routes for {schema_name}
Generated by SintraPrime DatabaseBuilder
\"\"\"
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import sqlite3
import uuid
from datetime import datetime

router = APIRouter()

def get_db():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

""".format(schema_name=schema.name)

        return imports + "\n\n".join(routes)

    def _generate_table_routes(self, table: Table) -> str:
        t = table.name
        pk_col = next((c.name for c in table.columns if c.primary_key), "id")
        non_pk_cols = [c.name for c in table.columns if not c.primary_key and c.name not in ("created_at", "updated_at")]
        col_list = ", ".join(non_pk_cols)

        return f"""# --- {t.upper()} Routes ---

@router.get("/{t}", tags=["{t}"])
async def list_{t}(limit: int = 50, offset: int = 0, db = Depends(get_db)):
    rows = db.execute("SELECT * FROM {t} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return {{"data": [dict(r) for r in rows], "total": db.execute("SELECT COUNT(*) FROM {t}").fetchone()[0]}}

@router.get("/{t}/{{item_id}}", tags=["{t}"])
async def get_{t[:-1]}(item_id: str, db = Depends(get_db)):
    row = db.execute("SELECT * FROM {t} WHERE {pk_col} = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="{t[:-1]} not found")
    return dict(row)

@router.post("/{t}", tags=["{t}"], status_code=201)
async def create_{t[:-1]}(data: Dict[str, Any], db = Depends(get_db)):
    item_id = str(uuid.uuid4())
    data["{pk_col}"] = item_id
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    db.execute(f"INSERT INTO {t} ({{cols}}) VALUES ({{placeholders}})", list(data.values()))
    db.commit()
    return {{"id": item_id, "message": "Created successfully"}}

@router.put("/{t}/{{item_id}}", tags=["{t}"])
async def update_{t[:-1]}(item_id: str, data: Dict[str, Any], db = Depends(get_db)):
    data.pop("{pk_col}", None)
    if not data:
        raise HTTPException(status_code=400, detail="No data provided")
    set_clause = ", ".join(f"{{k}} = ?" for k in data)
    db.execute(f"UPDATE {t} SET {{set_clause}} WHERE {pk_col} = ?", [*data.values(), item_id])
    db.commit()
    return {{"message": "Updated successfully"}}

@router.delete("/{t}/{{item_id}}", tags=["{t}"])
async def delete_{t[:-1]}(item_id: str, db = Depends(get_db)):
    db.execute("DELETE FROM {t} WHERE {pk_col} = ?", (item_id,))
    db.commit()
    return {{"message": "Deleted successfully"}}
"""
