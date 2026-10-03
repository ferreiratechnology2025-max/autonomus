import json
from typing import Optional

from loguru import logger

from src.memory.db_manager import DatabaseManager
from src.memory.models import ActionRecord, Episode, StateDiff


class EpisodeRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    async def create(self, episode: Episode) -> str:
        query = """
            INSERT INTO episodes (episode_id, timestamp, goal, outcome, duration_ms, user_feedback, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute_insert(query, (
            episode.episode_id,
            episode.timestamp,
            episode.goal,
            episode.outcome,
            episode.duration_ms,
            episode.user_feedback,
            episode.model_used,
        ))
        logger.debug(f"Episode {episode.episode_id} created")
        return episode.episode_id

    async def get(self, episode_id: str) -> Optional[Episode]:
        rows = await self.db.execute("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,))
        if not rows:
            return None
        row = rows[0]
        return Episode(
            episode_id=row["episode_id"],
            timestamp=row["timestamp"],
            goal=row["goal"],
            outcome=row["outcome"],
            duration_ms=row["duration_ms"],
            user_feedback=row.get("user_feedback"),
            model_used=row.get("model_used"),
        )

    async def list_recent(self, limit: int = 100, outcome: Optional[str] = None) -> list[Episode]:
        if outcome:
            rows = await self.db.execute(
                "SELECT * FROM episodes WHERE outcome = ? ORDER BY timestamp DESC LIMIT ?",
                (outcome, limit),
            )
        else:
            rows = await self.db.execute(
                "SELECT * FROM episodes ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        return [
            Episode(
                episode_id=row["episode_id"],
                timestamp=row["timestamp"],
                goal=row["goal"],
                outcome=row["outcome"],
                duration_ms=row["duration_ms"],
                user_feedback=row.get("user_feedback"),
                model_used=row.get("model_used"),
            )
            for row in rows
        ]

    async def update_outcome(self, episode_id: str, outcome: str, duration_ms: int) -> None:
        await self.db.execute_insert(
            "UPDATE episodes SET outcome = ?, duration_ms = ? WHERE episode_id = ?",
            (outcome, duration_ms, episode_id),
        )
        logger.debug(f"Episode {episode_id} outcome updated to {outcome}")

    async def add_action(self, action: ActionRecord) -> None:
        query = """
            INSERT INTO actions (action_id, episode_id, sequence, action_type, parameters, outcome, execution_time_ms, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute_insert(query, (
            action.action_id,
            action.episode_id,
            action.sequence,
            action.action_type,
            json.dumps(action.parameters),
            action.outcome,
            action.execution_time_ms,
            action.error_message,
        ))

    async def add_diff(self, diff: StateDiff) -> None:
        query = """
            INSERT INTO state_diffs (diff_id, action_id, pre_screenshot_hash, post_screenshot_hash, visual_divergence, text_added, text_removed, window_changed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute_insert(query, (
            diff.diff_id,
            diff.action_id,
            diff.pre_screenshot_hash,
            diff.post_screenshot_hash,
            diff.visual_divergence,
            diff.text_added,
            diff.text_removed,
            int(diff.window_changed),
        ))

    async def get_actions_by_episode(self, episode_id: str) -> list[ActionRecord]:
        rows = await self.db.execute(
            "SELECT * FROM actions WHERE episode_id = ? ORDER BY sequence ASC",
            (episode_id,),
        )
        return [
            ActionRecord(
                action_id=row["action_id"],
                episode_id=row["episode_id"],
                sequence=row["sequence"],
                action_type=row["action_type"],
                parameters=json.loads(row["parameters"]),
                outcome=row["outcome"],
                execution_time_ms=row["execution_time_ms"],
                error_message=row.get("error_message"),
            )
            for row in rows
        ]
