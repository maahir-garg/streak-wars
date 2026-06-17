"""Tracking logic: fetch live stats, detect events, and compute recaps.

Platform-agnostic. It iterates each user's configured handles and dispatches to
whichever platform is registered for that handle.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from ..models import BreakEvent, MilestoneEvent, User
from ..platforms import PlatformStats, get_platform
from ..storage import Storage

# Streak lengths worth celebrating.
MILESTONES = (7, 14, 30, 50, 100, 150, 200, 250, 365, 500, 730, 1000)

Event = BreakEvent | MilestoneEvent


@dataclass
class Snapshot:
    """Live stats for one user. A platform maps to None if its fetch failed."""

    user: User
    stats: dict[str, PlatformStats | None]


@dataclass
class RiskItem:
    """A streak that will break tonight unless the user solves something today."""

    user: User
    platform: str
    stats: PlatformStats


@dataclass
class WeeklyResult:
    user: User
    solved_this_week: int
    total_streak: int


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

    async def seed(self) -> None:
        """Record current streaks at startup without emitting any events.

        Ensures the first poll after launch does not announce a stale break and
        initialises the weekly baseline for any user/platform not yet stored.
        """
        for snap in await self.snapshot():
            for platform_name, stats in snap.stats.items():
                if stats is None:
                    continue
                state = self.storage.get_state(snap.user.telegram_id, platform_name)
                baseline = (
                    state.week_baseline_solved
                    if state and state.week_baseline_solved is not None
                    else stats.total_solved
                )
                self.storage.save_state(
                    snap.user.telegram_id,
                    platform_name,
                    stats.current_streak,
                    baseline,
                )

    async def poll(self) -> list[Event]:
        """Fetch fresh stats, persist them, and return events worth announcing.

        Detects streak breaks and milestone crossings. Failed fetches are skipped
        so known-good state is never overwritten.
        """
        events: list[Event] = []
        for snap in await self.snapshot():
            for platform_name, stats in snap.stats.items():
                if stats is None:
                    continue
                uid = snap.user.telegram_id
                state = self.storage.get_state(uid, platform_name)
                if state is None:
                    # Not seeded yet: store silently, no events.
                    self.storage.save_state(
                        uid, platform_name, stats.current_streak, stats.total_solved
                    )
                    continue

                prev = state.current_streak
                current = stats.current_streak

                crossed = [m for m in MILESTONES if prev < m <= current]
                if crossed:
                    events.append(
                        MilestoneEvent(snap.user, platform_name, current, max(crossed))
                    )
                if prev > 0 and current == 0:
                    events.append(BreakEvent(snap.user, platform_name, prev))

                baseline = (
                    state.week_baseline_solved
                    if state.week_baseline_solved is not None
                    else stats.total_solved
                )
                self.storage.save_state(uid, platform_name, current, baseline)
        return events

    async def at_risk(self) -> list[RiskItem]:
        """Users with a live streak who have not solved anything yet today."""
        items: list[RiskItem] = []
        for snap in await self.snapshot():
            for platform_name, stats in snap.stats.items():
                if stats and stats.current_streak >= 1 and not stats.solved_today:
                    items.append(RiskItem(snap.user, platform_name, stats))
        return items

    async def weekly_recap(self) -> list[WeeklyResult]:
        """Problems solved per user since the last recap, then reset the baseline."""
        results: list[WeeklyResult] = []
        for snap in await self.snapshot():
            solved = 0
            streak = 0
            for platform_name, stats in snap.stats.items():
                if stats is None:
                    continue
                uid = snap.user.telegram_id
                state = self.storage.get_state(uid, platform_name)
                baseline = (
                    state.week_baseline_solved
                    if state and state.week_baseline_solved is not None
                    else stats.total_solved
                )
                solved += max(0, stats.total_solved - baseline)
                streak += stats.current_streak
                self.storage.save_state(
                    uid,
                    platform_name,
                    state.current_streak if state else stats.current_streak,
                    stats.total_solved,  # reset baseline for the new week
                )
            results.append(WeeklyResult(snap.user, solved, streak))
        results.sort(key=lambda r: r.solved_this_week, reverse=True)
        return results
