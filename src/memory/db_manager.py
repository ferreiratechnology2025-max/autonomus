from pathlib import Path

import aiosqlite
from loguru import logger

from src.memory.schema import create_tables


class DatabaseManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await create_tables(self._conn)
        logger.info(f"Database initialized at {self.db_path}")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: tuple = ()) -> list[dict]:
        if not self._conn:
            raise RuntimeError("Database not initialized")
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def execute_many(self, query: str, params_list: list[tuple]) -> None:
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.executemany(query, params_list)

    async def execute_insert(self, query: str, params: tuple = ()) -> None:
        if not self._conn:
            raise RuntimeError("Database not initialized")
        await self._conn.execute(query, params)
        await self._conn.commit()
