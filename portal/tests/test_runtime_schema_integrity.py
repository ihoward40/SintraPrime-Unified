import asyncpg
import pytest
import pytest_asyncio

from portal.scripts.verify_runtime_schema_integrity import apply_baseline, apply_migration, verify


@pytest_asyncio.fixture
async def runtime_test_db():
    """Connect to the runtime test database and apply the integrity migration."""
    # Uses the disposable container started for Phase Two.
    url = "postgresql+asyncpg://sintraprime:***@127.0.0.1:5434/sintraprime_runtime_test"
    parsed = __import__("urllib.parse").parse.urlparse(url)
    scheme = parsed.scheme
    if scheme.startswith("postgresql+"):
        scheme = "postgresql"
    dsn = f"{scheme}://{parsed.netloc}{parsed.path}"

    conn = await asyncpg.connect(dsn=dsn)
    await apply_baseline(conn, ".")
    await apply_migration(conn, ".")
    yield conn
    await conn.close()


@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_runtime_schema_integrity_migration(runtime_test_db):
    results = await verify(runtime_test_db)
    assert results["failed"] == 0, results["checks"]


@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_agents_status_check(runtime_test_db):
    with pytest.raises(asyncpg.CheckViolationError):
        await runtime_test_db.execute(
            "INSERT INTO agents (name, type, status) VALUES ($1, $2, $3)",
            "test-agent", "worker", "invalid_status",
        )


@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_messages_priority_check(runtime_test_db):
    with pytest.raises(asyncpg.CheckViolationError):
        await runtime_test_db.execute(
            "INSERT INTO messages (type, priority, content) VALUES ($1, $2, $3)",
            "test", "invalid_priority", "{}",
        )


@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_knowledge_entries_confidence_check(runtime_test_db):
    with pytest.raises(asyncpg.CheckViolationError):
        await runtime_test_db.execute(
            "INSERT INTO knowledge_entries (key, value, confidence) VALUES ($1, $2, $3)",
            "test-key", "{}", 1.5,
        )


@pytest.mark.asyncio
@pytest.mark.postgresql
async def test_agents_status_not_null(runtime_test_db):
    with pytest.raises(asyncpg.NotNullViolationError):
        await runtime_test_db.execute(
            "INSERT INTO agents (name, type, status) VALUES ($1, $2, NULL)",
            "test-agent", "worker",
        )
