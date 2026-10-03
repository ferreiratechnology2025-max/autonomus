from pathlib import Path

import pytest

from src.memory.db_manager import DatabaseManager
from src.memory.memory import MemorySystem


@pytest.mark.slow
@pytest.mark.asyncio
async def test_memory_with_real_db(tmp_path):
    db_file = tmp_path / "memory.db"
    db = DatabaseManager(db_file)
    await db.initialize()
    assert db_file.exists()

    memory = MemorySystem(db)
    ep_id = await memory.start_episode("test integration")
    assert ep_id is not None

    await memory.record_action("click", {"x": 100, "y": 200}, "success", 50)
    await memory.end_episode("success", 100)

    recent = await memory.get_recent_successes(limit=10)
    assert len(recent) >= 1

    await db.close()
