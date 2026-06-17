"""SQLite persistence.

Only the last-known streak per (user, platform) is stored, since that is the
single piece of state needed to detect a break. Everything else is fetched live.
The interface is intentionally small so the backend can be swapped without
touching callers.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/competition.db")


class Storage:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS streak_state (
                telegram_id    INTEGER NOT NULL,
                platform       TEXT    NOT NULL,
                current_streak INTEGER NOT NULL,
                PRIMARY KEY (telegram_id, platform)
            )
            """
        )
        self._conn.commit()

    def get_streak(self, telegram_id: int, platform: str) -> int | None:
        """Last stored streak, or None if this user/platform has never been seen."""
        row = self._conn.execute(
            "SELECT current_streak FROM streak_state "
            "WHERE telegram_id = ? AND platform = ?",
            (telegram_id, platform),
        ).fetchone()
        return row[0] if row else None

    def set_streak(self, telegram_id: int, platform: str, streak: int) -> None:
        self._conn.execute(
            """
            INSERT INTO streak_state (telegram_id, platform, current_streak)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id, platform)
            DO UPDATE SET current_streak = excluded.current_streak
            """,
            (telegram_id, platform, streak),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
