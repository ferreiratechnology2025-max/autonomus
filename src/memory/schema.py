from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    goal TEXT NOT NULL,
    outcome TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    user_feedback TEXT,
    model_used TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    parameters TEXT NOT NULL,
    outcome TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    error_message TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS state_diffs (
    diff_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    pre_screenshot_hash TEXT,
    post_screenshot_hash TEXT,
    visual_divergence REAL,
    text_added TEXT,
    text_removed TEXT,
    window_changed INTEGER,
    FOREIGN KEY (action_id) REFERENCES actions(action_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp);
CREATE INDEX IF NOT EXISTS idx_episodes_outcome ON episodes(outcome);
CREATE INDEX IF NOT EXISTS idx_actions_episode ON actions(episode_id);
CREATE INDEX IF NOT EXISTS idx_diffs_action ON state_diffs(action_id);
"""


async def create_tables(db: Any) -> None:
    await db.executescript(SCHEMA_SQL)
