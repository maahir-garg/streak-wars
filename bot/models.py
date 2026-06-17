"""Core data models shared across the app."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    """A registered competitor.

    ``handles`` maps a platform name (e.g. "leetcode") to that user's username
    on the platform. A user can have handles on many platforms.
    """

    telegram_id: int
    name: str
    handles: dict[str, str] = field(default_factory=dict)


@dataclass
class BreakEvent:
    """A user's streak on a platform dropped to zero."""

    user: User
    platform: str
    previous_streak: int


@dataclass
class MilestoneEvent:
    """A user's streak reached a celebrated threshold (7, 30, 100, ...)."""

    user: User
    platform: str
    streak: int
    milestone: int
