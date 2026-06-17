"""Tracking logic: fetch live stats and detect streak breaks.

Platform-agnostic. It iterates each user's configured handles and dispatches to
whichever platform is registered for that handle.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from ..models import BreakEvent, User
from ..platforms import PlatformStats, get_platform
from ..storage import Storage


@dataclass
class Snapshot:
    """Live stats for one user. A platform maps to None if its fetch failed."""

    user: User
    stats: dict[str, PlatformStats | None]


class Tracker:
    def __init__(self, config: Config, storage: Storage):
        self.config = config
        self.storage = storage

    async def _fetch_user(self, user: User) -> dict[str, PlatformStats | None]:
        results: dict[str, PlatformStats | None] = {}
        for platform_name, handle in user.handles.items():
            try:
                results[platform_name] = await get_platform(
                    platform_name
                ).fetch_stats(handle)
            except Exception:
                results[platform_name] = None
        return results

    async def snapshot(self) -> list[Snapshot]:
        """Live stats for every configured user, in configured order."""
        return [
            Snapshot(user, await self._fetch_user(user)) for user in self.config.users
        ]

    async def check_breaks(self) -> list[BreakEvent]:
        """Persist fresh streaks and return any that just dropped to zero.

        A break is recorded when the stored streak was positive and the live
        streak is now zero. Failed fetches are skipped so known-good state is
        never overwritten.
        """
        breaks: list[BreakEvent] = []
        for snap in await self.snapshot():
            for platform_name, stats in snap.stats.items():
                if stats is None:
                    continue
                previous = self.storage.get_streak(snap.user.telegram_id, platform_name)
                if previous and stats.current_streak == 0:
                    breaks.append(
                        BreakEvent(snap.user, platform_name, previous)
                    )
                self.storage.set_streak(
                    snap.user.telegram_id, platform_name, stats.current_streak
                )
        return breaks
