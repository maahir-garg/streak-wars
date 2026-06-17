"""Platform package.

Importing this package registers every available platform as a side effect, so
the registry is populated simply by importing `bot.platforms`. To add a new
platform: drop a module here, subclass `Platform`, decorate with
`@register_platform`, and import it below.
"""

from .base import (  # noqa: F401
    Challenge,
    Platform,
    PlatformStats,
    all_platform_names,
    challenge_platforms,
    get_platform,
    register_platform,
)

# Side-effect imports: each registers itself on import.
from . import leetcode  # noqa: F401,E402
