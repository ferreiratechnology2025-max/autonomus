import hashlib
import json
import time
from pathlib import Path

import aiosqlite
from loguru import logger

from src.integration.models import LLMResponse


class LLMCache:
    def __init__(self, db_path: Path, ttl_seconds: int = 3600) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                prompt_hash TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _hash_prompt(self, prompt: str, system_prompt: str | None, model: str | None) -> str:
        key = f"{prompt}|{system_prompt}|{model}"
        return hashlib.sha256(key.encode()).hexdigest()

    async def get(self, prompt_hash: str) -> LLMResponse | None:
        if not self._conn:
            return None
        cursor = await self._conn.execute(
            "SELECT response_json, created_at FROM llm_cache WHERE prompt_hash = ?",
            (prompt_hash,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        elapsed = time.time() - row["created_at"]
        if elapsed > self.ttl_seconds:
            await self._conn.execute("DELETE FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,))
            await self._conn.commit()
            return None
        data = json.loads(row["response_json"])
        return LLMResponse(**data)

    async def set(self, prompt_hash: str, response: LLMResponse) -> None:
        if not self._conn:
            return
        data = {
            "content": response.content,
            "model_used": response.model_used,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "latency_ms": response.latency_ms,
        }
        await self._conn.execute(
            "INSERT OR REPLACE INTO llm_cache (prompt_hash, response_json, created_at) VALUES (?, ?, ?)",
            (prompt_hash, json.dumps(data), time.time()),
        )
        await self._conn.commit()

    async def clear_expired(self) -> None:
        if not self._conn:
            return
        cutoff = time.time() - self.ttl_seconds
        await self._conn.execute("DELETE FROM llm_cache WHERE created_at < ?", (cutoff,))
        await self._conn.commit()
        logger.debug("LLM cache expired entries cleared")
