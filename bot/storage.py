"""SQLite persistence.

Stores the small amount of state that cannot be recomputed from the platform
APIs, per (user, platform):

- ``current_streak``: last seen streak, used to detect breaks and milestones.
- ``best_streak``: longest completed streak, used to detect personal records.
- ``week_baseline_solved``: total-solved count at the start of the week, used to
  compute how many problems were solved during the week.

The interface is intentionally small so the backend can be swapped without
touching callers.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = Path("data/competition.db")


@dataclass
class StreakState:
    current_streak: int
    best_streak: int
    week_baseline_solved: int | None


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
                telegram_id    INTEGER NOT NULL,
                platform       TEXT    NOT NULL,
                current_streak INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (telegram_id, platform)
            )
            """
        )
        # Migrate older databases that predate these columns.
        existing = {row["name"] for row in self._conn.execute(
            "PRAGMA table_info(streak_state)"
        )}
        if "best_streak" not in existing:
            self._conn.execute(
                "ALTER TABLE streak_state ADD COLUMN best_streak INTEGER NOT NULL "
                "DEFAULT 0"
            )
        if "week_baseline_solved" not in existing:
            self._conn.execute(
                "ALTER TABLE streak_state ADD COLUMN week_baseline_solved INTEGER"
            )
        self._conn.commit()

    def get_state(self, telegram_id: int, platform: str) -> StreakState | None:
        row = self._conn.execute(
            "SELECT current_streak, best_streak, week_baseline_solved "
            "FROM streak_state WHERE telegram_id = ? AND platform = ?",
            (telegram_id, platform),
        ).fetchone()
        if row is None:
            return None
        return StreakState(
            current_streak=row["current_streak"],
            best_streak=row["best_streak"],
            week_baseline_solved=row["week_baseline_solved"],
        )

    def save_state(
        self,
        telegram_id: int,
        platform: str,
        current_streak: int,
        best_streak: int,
        week_baseline_solved: int | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO streak_state
                (telegram_id, platform, current_streak, best_streak,
                 week_baseline_solved)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id, platform) DO UPDATE SET
                current_streak       = excluded.current_streak,
                best_streak          = excluded.best_streak,
                week_baseline_solved = excluded.week_baseline_solved
            """,
            (telegram_id, platform, current_streak, best_streak, week_baseline_solved),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
