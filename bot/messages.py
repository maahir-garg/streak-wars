"""All user-facing message formatting + taunts, kept in one place.

Uses Telegram HTML parse mode. Designed to render multiple platforms per user,
even though only LeetCode is wired up today.
"""

from __future__ import annotations

import random
from html import escape

from .models import BreakEvent
from .platforms import Challenge, PlatformStats, get_platform
from .services.tracker import Snapshot

FIRE = "\U0001f525"  # 🔥
TROPHY = "\U0001f3c6"  # 🏆
SKULL = "\U0001f480"  # 💀
DART = "\U0001f3af"  # 🎯


_TAUNTS = [
    "{name} let their {platform} streak of {n} days die. {skull} Embarrassing.",
    "RIP {name}'s {n}-day {platform} streak. Was it worth the Netflix binge? {skull}",
    "{name} just fumbled a {n}-day streak on {platform}. The grind waits for no one.",
    "Breaking news: {name} forgot how to open {platform}. {n} days, gone. {skull}",
    "{name}'s {n}-day {platform} streak has left the chat. Press F to pay respects.",
]


def _platform_label(name: str) -> str:
    try:
        return get_platform(name).display_name
    except KeyError:
        return name.title()


def _streak_line(stats: PlatformStats | None) -> str:
    if stats is None:
        return "couldn't fetch stats right now ⚠️"
    flame = FIRE if stats.current_streak > 0 else SKULL
    return f"{flame} {stats.current_streak}-day streak  ·  {stats.total_solved} solved"


def format_streaks(snapshots: list[Snapshot]) -> str:
    lines = [f"<b>{FIRE} Current Streaks</b>", ""]
    for snap in snapshots:
        lines.append(f"<b>{escape(snap.user.name)}</b>")
        if not snap.stats:
            lines.append("  no platforms configured")
        for platform_name, stats in snap.stats.items():
            lines.append(
                f"  {escape(_platform_label(platform_name))}: {_streak_line(stats)}"
            )
        lines.append("")
    return "\n".join(lines).strip()


def _total_streak(snap: Snapshot) -> int:
    return sum(s.current_streak for s in snap.stats.values() if s)


def _total_solved(snap: Snapshot) -> int:
    return sum(s.total_solved for s in snap.stats.values() if s)


def format_leaderboard(snapshots: list[Snapshot]) -> str:
    ranked = sorted(snapshots, key=_total_streak, reverse=True)
    lines = [f"<b>{TROPHY} Leaderboard</b>", ""]
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇🥈🥉
    for i, snap in enumerate(ranked):
        medal = medals[i] if i < len(medals) else f"{i + 1}."
        lines.append(
            f"{medal} <b>{escape(snap.user.name)}</b> — "
            f"{FIRE} {_total_streak(snap)}  ·  {_total_solved(snap)} solved"
        )

    lines.append("")
    if len(ranked) >= 2 and _total_streak(ranked[0]) > _total_streak(ranked[1]):
        lead = _total_streak(ranked[0]) - _total_streak(ranked[1])
        lines.append(
            f"{escape(ranked[0].user.name)} is winning by {lead} streak-day"
            f"{'s' if lead != 1 else ''}! {DART}"
        )
    elif len(ranked) >= 2:
        lines.append("It's a dead heat. May the best grinder win. " + DART)
    return "\n".join(lines).strip()


def format_challenge(challenge: Challenge) -> str:
    return (
        f"<b>{DART} Challenge of the moment</b>\n\n"
        f"<a href=\"{escape(challenge.url, quote=True)}\">{escape(challenge.title)}</a>\n"
        f"Difficulty: <b>{escape(challenge.difficulty)}</b> · "
        f"{escape(_platform_label(challenge.platform))}\n\n"
        "First to solve it gets bragging rights. Go."
    )


def format_break(event: BreakEvent) -> str:
    return random.choice(_TAUNTS).format(
        name=escape(event.user.name),
        platform=escape(_platform_label(event.platform)),
        n=event.previous_streak,
        skull=SKULL,
    )


def format_daily_summary(snapshots: list[Snapshot]) -> str:
    header = f"<b>☀️ Good morning! Daily standings</b>\n"
    return header + "\n" + format_streaks(snapshots)
