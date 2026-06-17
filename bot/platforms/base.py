"""Platform abstraction and registry.

Each supported site is a Platform. The rest of the application depends only on
this interface, never on a concrete site, so adding a new platform means adding
one module that subclasses Platform and registers itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class PlatformStats:
    """A normalized snapshot of one user's standing on one platform."""

    platform: str
    username: str
    current_streak: int
    total_solved: int
    # Whether the user was active today (used for streak-saving reminders).
    solved_today: bool = False
    # Solved counts by difficulty, where the platform exposes them.
    easy: int = 0
    medium: int = 0
    hard: int = 0
    # Optional platform-specific fields, kept loose so platforms can expose
    # extra detail without changing this schema.
    extra: dict = field(default_factory=dict)


@dataclass
class Challenge:
    """A single problem to post to the group."""

    platform: str
    title: str
    url: str
    difficulty: str


class Platform(ABC):
    """Base class for all platform integrations.

    Subclasses set a unique ``name`` (used as the env-var suffix and storage
    key) and implement ``fetch_stats``. Two optional capabilities can be added
    by setting the matching flag and implementing the method:
    ``supports_challenges`` / ``random_challenge`` and ``supports_daily`` /
    ``daily_challenge``.
    """

    name: str = "base"
    display_name: str = "Base"
    supports_challenges: bool = False
    supports_daily: bool = False

    @abstractmethod
    async def fetch_stats(self, username: str) -> PlatformStats:
        """Return current streak and totals for ``username``.

        Should raise on lookup or network failure so callers can degrade
        gracefully per user rather than failing the whole run.
        """

    async def random_challenge(
        self, difficulties: Sequence[str] = ("Medium", "Hard")
    ) -> Challenge:
        raise NotImplementedError(f"{self.display_name} does not support challenges")

    async def daily_challenge(self) -> Challenge:
        raise NotImplementedError(
            f"{self.display_name} does not have a daily challenge"
        )


_REGISTRY: dict[str, Platform] = {}


def register_platform(cls: type[Platform]) -> type[Platform]:
    """Class decorator that instantiates and registers a platform singleton."""
    instance = cls()
    _REGISTRY[instance.name] = instance
    return cls


def get_platform(name: str) -> Platform:
    return _REGISTRY[name]


def all_platform_names() -> list[str]:
    return list(_REGISTRY.keys())


def challenge_platforms() -> list[Platform]:
    return [p for p in _REGISTRY.values() if p.supports_challenges]


def daily_platforms() -> list[Platform]:
    return [p for p in _REGISTRY.values() if p.supports_daily]
