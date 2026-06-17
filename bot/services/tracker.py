"""Tracking logic: fetch live stats and detect streak breaks.

Platform-agnostic — it iterates each user's handles and dispatches to whatever
platform module is registered for that handle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import Config
from ..models import BreakEvent, User
from ..platforms import PlatformStats, get_platform
from ..storage import Storage

# Per-user, per-platform result. ``stats`` is None if the live fetch failed.
UserStats = dict[str, PlatformStats | None]


@dataclass
class Snapshot:
    user: User
    stats: UserStats


class Tracker:
    def __init__(self, config: Config, storage: Storage):
        self.config = config
        self.storage = storage

    async def _fetch_user(self, user: User) -> UserStats:
        result: UserStats = {}
        for platform_name, handle in user.handles.items():
            try:
                result[platform_name] = await get_platform(platform_name).fetch_stats(
                    handle
                )
            except Exception:  # noqa: BLE001 - degrade gracefully per user
                result[platform_name] = None
        return result

    async def snapshot(self) -> list[Snapshot]:
        """Live stats for every user, in configured order."""
        return [
            Snapshot(user=u, stats=await self._fetch_user(u))
            for u in self.config.users
        ]

    async def check_breaks(self) -> list[BreakEvent]:
        """Fetch fresh stats, persist them, and return any new streak breaks.

        A break = the stored streak was > 0 and the live streak is now 0.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        breaks: list[BreakEvent] = []

        for snap in await self.snapshot():
            for platform_name, stats in snap.stats.items():
                if stats is None:
                    continue  # fetch failed; don't overwrite known-good state

                prev = self.storage.get_state(snap.user.telegram_id, platform_name)
                if prev and prev.current_streak > 0 and stats.current_streak == 0:
                    breaks.append(
                        BreakEvent(
                            user=snap.user,
                            platform=platform_name,
                            previous_streak=prev.current_streak,
                        )
                    )

                self.storage.set_state(
                    telegram_id=snap.user.telegram_id,
                    platform=platform_name,
                    current_streak=stats.current_streak,
                    last_active=stats.extra.get("last_active"),
                    last_checked=now_iso,
                )

        return breaks
