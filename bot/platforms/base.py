"""Platform abstraction + registry.

Every competitive-programming site we support is a `Platform`. The rest of the
codebase only ever talks to this interface, so adding a new site (Codeforces,
HackerRank, ...) means writing one module that subclasses `Platform` and calls
`@register_platform` — nothing else needs to change.
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
    # Anything platform-specific (e.g. per-difficulty breakdown). Kept loose
    # on purpose so platforms can expose extra detail without schema churn.
    extra: dict = field(default_factory=dict)


@dataclass
class Challenge:
    """A single problem to throw at the group."""

    platform: str
    title: str
    url: str
    difficulty: str
    extra: dict = field(default_factory=dict)


class Platform(ABC):
    """Base class for all platform integrations.

    Subclasses set a unique ``name`` (used as the env-var suffix and storage
    key) and implement ``fetch_stats``. Challenge support is optional: flip
    ``supports_challenges`` and implement ``random_challenge``.
    """

    name: str = "base"
    display_name: str = "Base"
    supports_challenges: bool = False

    @abstractmethod
    async def fetch_stats(self, username: str) -> PlatformStats:
        """Return the current streak + totals for ``username``.

        Should raise on network/lookup failure so callers can degrade
        gracefully per-user instead of crashing the whole run.
        """
        raise NotImplementedError

    async def random_challenge(
        self, difficulties: Sequence[str] = ("Medium", "Hard")
    ) -> Challenge:
        raise NotImplementedError(
            f"{self.display_name} does not support challenges"
        )


# --- registry -------------------------------------------------------------

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
