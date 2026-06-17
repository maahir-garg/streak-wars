"""SQLite-backed persistence.

We only persist what we can't recompute from the platform APIs: the last-known
streak state per (user, platform), which powers break detection. Everything
else is fetched live.

The public surface is small (``get_state`` / ``set_state``) so it could be
swapped for another backend without touching callers.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = Path("data/competition.db")


@dataclass
class StreakState:
    current_streak: int
    last_active: str | None  # ISO date string, or None
    last_checked: str | None  # ISO datetime string, or None


class Storage:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS streak_state (
                telegram_id   INTEGER NOT NULL,
                platform      TEXT    NOT NULL,
                current_streak INTEGER NOT NULL DEFAULT 0,
                last_active   TEXT,
                last_checked  TEXT,
                PRIMARY KEY (telegram_id, platform)
            )
            """
        )
        self._conn.commit()

    def get_state(self, telegram_id: int, platform: str) -> StreakState | None:
        row = self._conn.execute(
            "SELECT current_streak, last_active, last_checked "
            "FROM streak_state WHERE telegram_id = ? AND platform = ?",
            (telegram_id, platform),
        ).fetchone()
        if row is None:
            return None
        return StreakState(
            current_streak=row["current_streak"],
            last_active=row["last_active"],
            last_checked=row["last_checked"],
        )

    def set_state(
        self,
        telegram_id: int,
        platform: str,
        current_streak: int,
        last_active: str | None,
        last_checked: str | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO streak_state
                (telegram_id, platform, current_streak, last_active, last_checked)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id, platform) DO UPDATE SET
                current_streak = excluded.current_streak,
                last_active    = excluded.last_active,
                last_checked   = excluded.last_checked
            """,
            (telegram_id, platform, current_streak, last_active, last_checked),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
