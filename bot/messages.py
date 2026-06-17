"""All user-facing message formatting and taunts.

Uses Telegram HTML parse mode. Renders any number of participants and any number
of platforms per participant.
"""

from __future__ import annotations

import random
from html import escape

from .models import BreakEvent
from .platforms import Challenge, PlatformStats, get_platform
from .services.tracker import Snapshot

_TAUNTS = [
    "{name} let a {n}-day {platform} streak die. Back to zero.",
    "{name}'s {n}-day {platform} streak is over. The grind continues without them.",
    "Streak broken: {name} dropped a {n}-day run on {platform}.",
    "{name} missed a day. {n} days of {platform} progress, gone.",
]


def _platform_label(name: str) -> str:
    try:
        return get_platform(name).display_name
    except KeyError:
        return name.title()


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _stats_line(stats: PlatformStats | None) -> str:
    if stats is None:
        return "stats unavailable"
    return f"{stats.current_streak}-day streak, {stats.total_solved} solved"


def _total_streak(snapshot: Snapshot) -> int:
    return sum(s.current_streak for s in snapshot.stats.values() if s)


def _total_solved(snapshot: Snapshot) -> int:
    return sum(s.total_solved for s in snapshot.stats.values() if s)


def format_streaks(snapshots: list[Snapshot]) -> str:
    lines = ["<b>Current streaks</b>", ""]
    for snap in snapshots:
        lines.append(f"<b>{escape(snap.user.name)}</b>")
        if not snap.stats:
            lines.append("  no platforms configured")
        for platform_name, stats in snap.stats.items():
            label = escape(_platform_label(platform_name))
            lines.append(f"  {label}: {_stats_line(stats)}")
        lines.append("")
    return "\n".join(lines).strip()


def format_leaderboard(snapshots: list[Snapshot]) -> str:
    ranked = sorted(snapshots, key=_total_streak, reverse=True)
    lines = ["<b>Leaderboard</b>", ""]
    for i, snap in enumerate(ranked, start=1):
        lines.append(
            f"{i}. <b>{escape(snap.user.name)}</b> - "
            f"{_total_streak(snap)} streak, {_total_solved(snap)} solved"
        )

    lines.append("")
    if len(ranked) >= 2 and _total_streak(ranked[0]) > _total_streak(ranked[1]):
        lead = _total_streak(ranked[0]) - _total_streak(ranked[1])
        lines.append(
            f"{escape(ranked[0].user.name)} leads by {_plural(lead, 'streak day')}."
        )
    elif len(ranked) >= 2:
        lines.append("It is currently a tie.")
    return "\n".join(lines).strip()


def format_challenge(challenge: Challenge) -> str:
    title = escape(challenge.title)
    url = escape(challenge.url, quote=True)
    return (
        "<b>Challenge</b>\n\n"
        f'<a href="{url}">{title}</a>\n'
        f"Difficulty: {escape(challenge.difficulty)} "
        f"({escape(_platform_label(challenge.platform))})"
    )


def format_break(event: BreakEvent) -> str:
    return random.choice(_TAUNTS).format(
        name=escape(event.user.name),
        platform=escape(_platform_label(event.platform)),
        n=event.previous_streak,
    )


def format_daily_summary(snapshots: list[Snapshot]) -> str:
    return "<b>Daily standings</b>\n\n" + format_streaks(snapshots)
