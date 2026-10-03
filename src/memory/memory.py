import time
from typing import Any, Optional

from loguru import logger

from src.memory.db_manager import DatabaseManager
from src.memory.episode_repository import EpisodeRepository
from src.memory.models import ActionRecord, Episode, StateDiff


class MemorySystem:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self.episodes = EpisodeRepository(self.db)
        self.current_episode_id: Optional[str] = None
        self.action_counter: int = 0
        self._episode_start_time: float = 0.0

    async def start_episode(self, goal: str, model_used: Optional[str] = None) -> str:
        import uuid

        episode_id = uuid.uuid4().hex
        self.current_episode_id = episode_id
        self.action_counter = 0
        self._episode_start_time = time.time()

        ep = Episode(
            episode_id=episode_id,
            timestamp=self._episode_start_time,
            goal=goal,
            outcome="running",
            model_used=model_used,
        )
        await self.episodes.create(ep)
        logger.info(f"Episode {episode_id} started: '{goal}'")
        return episode_id

    async def end_episode(self, outcome: str, duration_ms: int, feedback: Optional[str] = None) -> None:
        if self.current_episode_id is None:
            logger.warning("No active episode to end")
            return
        await self.episodes.update_outcome(self.current_episode_id, outcome, duration_ms)
        if feedback:
            await self.db.execute_insert(
                "UPDATE episodes SET user_feedback = ? WHERE episode_id = ?",
                (feedback, self.current_episode_id),
            )
        logger.info(f"Episode {self.current_episode_id} ended: {outcome} ({duration_ms}ms)")
        self.current_episode_id = None

    async def record_action(
        self,
        action_type: str,
        parameters: dict[str, Any],
        outcome: str,
        execution_time_ms: int,
        error_msg: Optional[str] = None,
    ) -> str:
        import uuid

        action_id = uuid.uuid4().hex
        self.action_counter += 1

        if self.current_episode_id is None:
            raise RuntimeError("No active episode. Call start_episode first.")

        action = ActionRecord(
            action_id=action_id,
            episode_id=self.current_episode_id,
            sequence=self.action_counter,
            action_type=action_type,
            parameters=parameters,
            outcome=outcome,
            execution_time_ms=execution_time_ms,
            error_message=error_msg,
        )
        await self.episodes.add_action(action)
        logger.debug(f"Action {action_id}: {action_type} -> {outcome}")
        return action_id

    async def record_diff(self, action_id: str, diff: StateDiff) -> None:
        await self.episodes.add_diff(diff)

    async def get_recent_successes(self, limit: int = 10, action_type: Optional[str] = None) -> list[ActionRecord]:
        if action_type:
            rows = await self.db.execute(
                """SELECT a.* FROM actions a
                   JOIN episodes e ON a.episode_id = e.episode_id
                   WHERE a.outcome = 'success' AND a.action_type = ?
                   ORDER BY e.timestamp DESC LIMIT ?""",
                (action_type, limit),
            )
        else:
            rows = await self.db.execute(
                """SELECT a.* FROM actions a
                   JOIN episodes e ON a.episode_id = e.episode_id
                   WHERE a.outcome = 'success'
                   ORDER BY e.timestamp DESC LIMIT ?""",
                (limit,),
            )
        return [
            ActionRecord(
                action_id=row["action_id"],
                episode_id=row["episode_id"],
                sequence=row["sequence"],
                action_type=row["action_type"],
                parameters=row["parameters"],
                outcome=row["outcome"],
                execution_time_ms=row["execution_time_ms"],
                error_message=row.get("error_message"),
            )
            for row in rows
        ]

    async def get_failure_patterns(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = await self.db.execute(
            """SELECT action_type, error_message, COUNT(*) as count
               FROM actions
               WHERE outcome = 'failed' AND error_message IS NOT NULL
               GROUP BY action_type, error_message
               ORDER BY count DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in rows]
