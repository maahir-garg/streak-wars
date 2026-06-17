"""Challenge selection across challenge-capable platforms."""

from __future__ import annotations

import random
from typing import Sequence

from ..platforms import Challenge, challenge_platforms


async def random_challenge(
    difficulties: Sequence[str] = ("Medium", "Hard"),
) -> Challenge:
    """Pick a random platform that supports challenges and pull one problem."""
    platforms = challenge_platforms()
    if not platforms:
        raise RuntimeError("No challenge-capable platforms are registered")
    platform = random.choice(platforms)
    return await platform.random_challenge(difficulties)
