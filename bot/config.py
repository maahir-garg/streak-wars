"""Configuration loaded from environment / .env.

Users are defined with numbered env vars (USER1_*, USER2_*, ...). For each
registered platform we look for USER{n}_{PLATFORM} to find that user's handle,
so wiring up a new platform needs no changes here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Importing the platforms package registers all platforms (side effect).
from .platforms import all_platform_names
from .models import User

load_dotenv()

# PTB weekday numbering: 0 = Sunday ... 6 = Saturday.
_DAYS = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _parse_time(value: str | None, tz: ZoneInfo) -> time | None:
    """Parse 'HH:MM' into a tz-aware time. Blank or 'off' disables the feature."""
    if not value or value.strip().lower() == "off":
        return None
    hour, minute = (int(x) for x in value.split(":"))
    return time(hour=hour, minute=minute, tzinfo=tz)


def _load_users() -> list[User]:
    users: list[User] = []
    platforms = all_platform_names()
    n = 1
    while True:
        name = os.getenv(f"USER{n}_NAME")
        tg_id = os.getenv(f"USER{n}_TELEGRAM_ID")
        if not name or not tg_id:
            break
        handles = {}
        for platform in platforms:
            handle = os.getenv(f"USER{n}_{platform.upper()}")
            if handle:
                handles[platform] = handle
        users.append(User(telegram_id=int(tg_id), name=name, handles=handles))
        n += 1
    return users


@dataclass
class Config:
    bot_token: str
    group_chat_id: int
    timezone: ZoneInfo
    daily_summary_time: time
    streak_check_interval_minutes: int
    reminder_time: time | None
    weekly_recap_time: time | None
    weekly_recap_day: int
    users: list[User] = field(default_factory=list)

    @property
    def allowed_ids(self) -> set[int]:
        return {u.telegram_id for u in self.users}

    def user_by_id(self, telegram_id: int) -> User | None:
        return next((u for u in self.users if u.telegram_id == telegram_id), None)


def load_config() -> Config:
    tz = ZoneInfo(os.getenv("TIMEZONE", "UTC"))

    users = _load_users()
    if len(users) < 1:
        raise RuntimeError(
            "No users configured. Set USER1_NAME / USER1_TELEGRAM_ID etc. in .env"
        )

    daily_summary_time = _parse_time(os.getenv("DAILY_SUMMARY_TIME", "08:00"), tz)
    assert daily_summary_time is not None  # default is always set

    return Config(
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        group_chat_id=int(_require("GROUP_CHAT_ID")),
        timezone=tz,
        daily_summary_time=daily_summary_time,
        streak_check_interval_minutes=int(
            os.getenv("STREAK_CHECK_INTERVAL_MINUTES", "60")
        ),
        reminder_time=_parse_time(os.getenv("REMINDER_TIME", "21:00"), tz),
        weekly_recap_time=_parse_time(os.getenv("WEEKLY_RECAP_TIME", "20:00"), tz),
        weekly_recap_day=_DAYS.get(os.getenv("WEEKLY_RECAP_DAY", "sun").lower(), 0),
        users=users,
    )
