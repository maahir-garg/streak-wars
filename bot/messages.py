"""All user-facing message formatting and taunts.

Uses Telegram HTML parse mode. Renders any number of participants and any number
of platforms per participant.
"""

from __future__ import annotations

import random
from html import escape

from .models import BreakEvent, MilestoneEvent
from .platforms import Challenge, PlatformStats, get_platform
from .services.tracker import RiskItem, Snapshot, WeeklyResult

_TAUNTS = [
    "{name} let a {n}-day {platform} streak die. Back to zero.",
    "{name}'s {n}-day {platform} streak is over. The grind continues without them.",
    "Streak broken: {name} dropped a {n}-day run on {platform}.",
    "{name} missed a day. {n} days of {platform} progress, gone.",
]

_MILESTONES = [
    "{name} just hit a {m}-day {platform} streak. Keep it going.",
    "Milestone: {name} reached {m} days on {platform}.",
    "{m} days and counting. {name} is on a {platform} tear.",
]


def _platform_label(name: str) -> str:
    try:
        return get_platform(name).display_name
    except KeyError:
        return name.title()


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _mention(telegram_id: int, name: str) -> str:
    safe = escape(name)
    # A real user id produces a tap-to-ping mention; placeholder ids (e.g. 0)
    # simply render as bold text.
    if telegram_id > 0:
        return f'<a href="tg://user?id={telegram_id}">{safe}</a>'
    return f"<b>{safe}</b>"


def _stats_line(stats: PlatformStats | None) -> str:
    if stats is None:
        return "stats unavailable"
    return (
        f"{stats.current_streak}-day streak, {stats.total_solved} solved "
        f"({stats.easy}E / {stats.medium}M / {stats.hard}H)"
    )


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


def format_challenge(challenge: Challenge, heading: str = "Challenge") -> str:
    title = escape(challenge.title)
    url = escape(challenge.url, quote=True)
    return (
        f"<b>{escape(heading)}</b>\n\n"
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


def format_milestone(event: MilestoneEvent) -> str:
    return random.choice(_MILESTONES).format(
        name=escape(event.user.name),
        platform=escape(_platform_label(event.platform)),
        m=event.milestone,
    )


def format_event(event) -> str:
    if isinstance(event, BreakEvent):
        return format_break(event)
    if isinstance(event, MilestoneEvent):
        return format_milestone(event)
    raise TypeError(f"Unknown event type: {type(event)!r}")


def format_reminder(item: RiskItem) -> str:
    mention = _mention(item.user.telegram_id, item.user.name)
    platform = escape(_platform_label(item.platform))
    return (
        f"{mention}, your {item.stats.current_streak}-day {platform} streak is on "
        "the line. Solve something today to keep it alive."
    )


def format_weekly_recap(results: list[WeeklyResult]) -> str:
    lines = ["<b>Weekly recap</b>", "", "Problems solved this week:"]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"{i}. <b>{escape(r.user.name)}</b> - {r.solved_this_week} solved, "
            f"{r.total_streak}-day streak"
        )

    lines.append("")
    top = results[0] if results else None
    if not top or top.solved_this_week == 0:
        lines.append("Nobody solved anything this week. Step it up.")
    elif len(results) >= 2 and results[1].solved_this_week == top.solved_this_week:
        lines.append("It is a tie at the top this week.")
    else:
        lines.append(
            f"Winner: {escape(top.user.name)} with {top.solved_this_week} solved."
        )
    return "\n".join(lines).strip()


def format_daily_summary(snapshots: list[Snapshot]) -> str:
    return "<b>Daily standings</b>\n\n" + format_streaks(snapshots)
