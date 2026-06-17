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


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


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
    users: list[User] = field(default_factory=list)

    @property
    def allowed_ids(self) -> set[int]:
        return {u.telegram_id for u in self.users}

    def user_by_id(self, telegram_id: int) -> User | None:
        return next((u for u in self.users if u.telegram_id == telegram_id), None)


def load_config() -> Config:
    tz = ZoneInfo(os.getenv("TIMEZONE", "UTC"))

    raw_time = os.getenv("DAILY_SUMMARY_TIME", "08:00")
    hour, minute = (int(x) for x in raw_time.split(":"))

    users = _load_users()
    if len(users) < 1:
        raise RuntimeError(
            "No users configured. Set USER1_NAME / USER1_TELEGRAM_ID etc. in .env"
        )

    return Config(
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        group_chat_id=int(_require("GROUP_CHAT_ID")),
        timezone=tz,
        daily_summary_time=time(hour=hour, minute=minute, tzinfo=tz),
        streak_check_interval_minutes=int(
            os.getenv("STREAK_CHECK_INTERVAL_MINUTES", "60")
        ),
        users=users,
    )
