import pytest

from src.memory.schema import SCHEMA_SQL, create_tables


@pytest.mark.asyncio
async def test_schema_creates_tables(tmp_path):
    db_file = tmp_path / "test.db"

    class FakeDB:
        async def executescript(self, sql):
            assert SCHEMA_SQL in sql

    await create_tables(FakeDB())


@pytest.mark.asyncio
async def test_schema_sql_contains_all_tables():
    assert "CREATE TABLE IF NOT EXISTS episodes" in SCHEMA_SQL
    assert "CREATE TABLE IF NOT EXISTS actions" in SCHEMA_SQL
    assert "CREATE TABLE IF NOT EXISTS state_diffs" in SCHEMA_SQL


@pytest.mark.asyncio
async def test_schema_sql_contains_indexes():
    assert "CREATE INDEX IF NOT EXISTS idx_episodes_timestamp" in SCHEMA_SQL
    assert "CREATE INDEX IF NOT EXISTS idx_actions_episode" in SCHEMA_SQL
    assert "CREATE INDEX IF NOT EXISTS idx_diffs_action" in SCHEMA_SQL


@pytest.mark.asyncio
async def test_schema_sql_has_foreign_keys():
    assert "FOREIGN KEY" in SCHEMA_SQL
    assert "REFERENCES episodes" in SCHEMA_SQL
