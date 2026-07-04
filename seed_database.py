"""
Seed initial data for SintraPrime-Unified portal database.
"""

import asyncio
import uuid
from datetime import datetime
from portal.database import engine, AsyncSessionLocal, Base
from portal.models.user import Tenant, Role, User
from portal.models.client import Client
from portal.models.case import Case


async def seed():
    async with AsyncSessionLocal() as session:
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name="IKE Solutions",
            slug="ike-solutions",
            domain="ikesolutions.org",
            plan="enterprise",
            is_active=True,
            email="isiahh@ikesolutions.org",
            phone="908-365-4234",
            address="991 Frelinghuysen Avenue, Apt 1K, Newark, NJ 07114",
            primary_color="#D4AF37",
            secondary_color="#1a1a1a",
        )
        session.add(tenant)
        await session.flush()
        print(f"Tenant: {tenant.name}")

        roles_data = [
            ("SUPER_ADMIN", "Full system access", ["*"]),
            ("FIRM_ADMIN", "Manage firm", ["user:*", "client:*", "case:*", "doc:*", "billing:*"]),
            ("ATTORNEY", "Case and document access", ["client:*", "case:*", "doc:*", "billing:read"]),
            ("PARALEGAL", "Case access, limited", ["client:read", "case:read,update", "doc:read,upload"]),
            ("CLIENT", "Own data only", ["client:own", "case:own", "doc:own"]),
            ("ACCOUNTANT", "Financial and billing", ["billing:*", "doc:financial"]),
            ("VIEWER", "Read-only documents", ["doc:read"]),
        ]

        role_ids = {}
        for name, desc, _ in roles_data:
            role_id = str(uuid.uuid4())
            session.add(Role(id=role_id, name=name, display_name=name.replace("_", " ").title(), description=desc, is_system=True))
            role_ids[name] = role_id
        await session.flush()
        print(f"Roles: {len(roles_data)}")

        admin_id = str(uuid.uuid4())
        admin = User(
            id=admin_id,
            tenant_id=tenant_id,
            role_id=role_ids["SUPER_ADMIN"],
            email="isiahh@ikesolutions.org",
            email_verified=True,
            hashed_password="$2b$12$placeholder",
            first_name="Isiah",
            last_name="Howard",
            phone="908-365-4234",
            title="Founder & Trustee",
            is_active=True,
        )
        session.add(admin)
        await session.flush()
        print(f"Admin: {admin.email}")

        client_id = str(uuid.uuid4())
        client = Client(
            id=client_id,
            tenant_id=tenant_id,
            client_type="individual",
            first_name="Isiah",
            last_name="Howard",
            email="howardisiah@gmail.com",
            phone="908-365-4234",
            address_line1="991 Frelinghuysen Avenue",
            address_line2="Apt 1K",
            city="Newark",
            state="NJ",
            postal_code="07114",
            country="US",
            status="active",
            intake_date=datetime(2026, 7, 3),
            notes="Founder and primary client. Trust: ISIAH TARIK HOWARD TRUST EIN 92-6080121. Business: IKE Solutions EIN 87-1798434.",
        )
        session.add(client)
        await session.flush()
        print(f"Client: {client.first_name} {client.last_name}")

        cases_data = [
            ("IRS CP23 / Letter 3176C / 2024 Tax Dispute", "high", "IRS assessed $74,280. Letter 3176C frivolous warning. CNC/hardship filing needed."),
            ("Halsted / LVNV / Resurgent", "high", "Celtic Bank/Reflex 9370. Deficiency notice drafted. Portal submission pending approval."),
            ("PayPal Negative Balance", "high", "Account blocked, balance -$1,015.00."),
            ("UACC / Vroom", "high", "Auto-finance lawsuit preparation."),
            ("AFF / FinWise", "high", "FCRA rent-a-bank dispute."),
            ("Self Financial / Lead Bank", "high", "Derogatory reporting dispute."),
        ]

        for name, priority, notes in cases_data:
            session.add(Case(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                client_id=client_id,
                case_number=f"CASE-{uuid.uuid4().hex[:10].upper()}",
                title=name,
                case_type="recovery",
                practice_area="consumer_law",
                description=notes,
                stage="evidence_intake",
                is_urgent=(priority == "high"),
            ))
        await session.flush()
        print(f"Cases: {len(cases_data)}")

        await session.commit()
        print("\n=== SEED COMPLETE ===")
        print(f"Tenant: IKE Solutions")
        print(f"Admin: isiahh@ikesolutions.org")
        print(f"Client: Isiah Howard")
        print(f"Cases: {len(cases_data)} active")
        print(f"Tables: 27 in SQLite")


if __name__ == "__main__":
    asyncio.run(seed())