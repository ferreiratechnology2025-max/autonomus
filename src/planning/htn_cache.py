import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class HTNPlanCache:
    """Cache persistente de planos HTN com TTL para evitar chamadas repetitivas ao LLM."""

    def __init__(self, db_path: str = "data/htn_cache.db", ttl_hours: int = 24) -> None:
        self.db_path = Path(db_path)
        self.ttl = timedelta(hours=ttl_hours)
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS htn_cache (
                    objective_hash TEXT PRIMARY KEY,
                    objective_text TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON htn_cache(expires_at)"
            )

    @staticmethod
    def _hash_objective(objective: str) -> str:
        normalized = " ".join(objective.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, objective: str) -> Optional[List[Dict[str, Any]]]:
        obj_hash = self._hash_objective(objective)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM htn_cache WHERE objective_hash = ?", (obj_hash,)
            ).fetchone()
            if not row:
                return None
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now():
                conn.execute(
                    "DELETE FROM htn_cache WHERE objective_hash = ?", (obj_hash,)
                )
                return None
            conn.execute(
                "UPDATE htn_cache SET hit_count = hit_count + 1 WHERE objective_hash = ?",
                (obj_hash,),
            )
            logger.info(f"Cache HIT: {obj_hash}")
            return json.loads(row["actions"])

    def set(self, objective: str, actions: List[Dict[str, Any]]) -> None:
        obj_hash = self._hash_objective(objective)
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO htn_cache
                   (objective_hash, objective_text, actions, created_at, expires_at, hit_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    obj_hash,
                    objective,
                    json.dumps(actions),
                    now.isoformat(),
                    (now + self.ttl).isoformat(),
                    0,
                ),
            )
        logger.info(f"Cache SET: {obj_hash}")

    def clear_expired(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM htn_cache WHERE expires_at < ?",
                (datetime.now().isoformat(),),
            )
            removed = cursor.rowcount
            if removed:
                logger.info(f"Cache: {removed} expirados removidos")
            return removed

    def invalidate(self, objective: str) -> bool:
        obj_hash = self._hash_objective(objective)
        return self.invalidate_by_hash(obj_hash)

    def invalidate_by_hash(self, obj_hash: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM htn_cache WHERE objective_hash = ?",
                (obj_hash,),
            )
            if cursor.rowcount > 0:
                logger.warning(f"Cache INVALIDATED for hash: {obj_hash}")
                return True
            return False

    def get_hash(self, objective: str) -> str:
        return self._hash_objective(objective)

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as total, COALESCE(SUM(hit_count), 0) as hits FROM htn_cache"
            ).fetchone()
            return {
                "entries": row[0],
                "total_hits": row[1],
                "ttl_hours": self.ttl.total_seconds() / 3600,
            }
