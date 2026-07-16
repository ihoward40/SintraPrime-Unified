"""Role isolation test for sintraprime_test_runner.

Verifies the test runner role cannot access production databases,
escalate privileges, or bypass RLS.

Run with: GATE4_TEST_PASSWORD=<secret> python portal/tests/test_role_isolation.py
"""
import asyncio
import os

import asyncpg


def _get_password() -> str:
    pw = os.environ.get("GATE4_TEST_PASSWORD")
    if not pw:
        raise RuntimeError(
            "GATE4_TEST_PASSWORD is required. "
            "Set it in .env.test or export it before running this script."
        )
    return pw


async def main():
    password = _get_password()
    connect_kwargs = {
        "host": "localhost",
        "port": 5433,
        "user": "sintraprime_test_runner",
        "password": password,
    }

    # 1. Connect to gate4_test
    conn = await asyncpg.connect(database="gate4_test", **connect_kwargs)
    usr = await conn.fetchval("SELECT current_user")
    print(f"1. gate4_test connect: OK (user={usr})")
    await conn.close()

    # 2. Cannot connect to production DB
    try:
        prod = await asyncpg.connect(database="sintraprime_unified", **connect_kwargs)
        print("2. PRODUCTION DB: CONNECTED - NEEDS FIX")
        await prod.close()
    except Exception as e:
        print(f"2. Production DB: BLOCKED ({type(e).__name__})")

    # 3. Can create disposable databases
    admin = await asyncpg.connect(database="postgres", **connect_kwargs)
    try:
        await admin.execute("CREATE DATABASE gate4_test_temp")
        print("3. Can create DB: YES")
        await admin.execute("DROP DATABASE gate4_test_temp")
        print("   Can drop DB: YES")
    except Exception as e:
        print(f"3. DB create: {type(e).__name__}: {str(e)[:100]}")
    await admin.close()

    # 4. Cannot escalate privileges
    conn2 = await asyncpg.connect(database="gate4_test", **connect_kwargs)
    try:
        await conn2.execute("ALTER ROLE sintraprime_test_runner WITH SUPERUSER")
        print("4. CRITICAL: Can escalate!")
    except Exception as e:
        print(f"4. Privilege escalation: BLOCKED ({type(e).__name__})")

    # 5. Cannot alter production role
    try:
        await conn2.execute("ALTER ROLE sintraprime WITH SUPERUSER")
        print("5. CRITICAL: Can alter production role!")
    except Exception as e:
        print(f"5. Alter production role: BLOCKED ({type(e).__name__})")

    # 6. Cannot bypass RLS (if any)
    try:
        await conn2.execute("ALTER ROLE sintraprime_test_runner WITH BYPASSRLS")
        print("6. CRITICAL: Can bypass RLS!")
    except Exception as e:
        print(f"6. Bypass RLS: BLOCKED ({type(e).__name__})")

    await conn2.close()
    print("\nAll role isolation checks complete.")


if __name__ == "__main__":
    asyncio.run(main())