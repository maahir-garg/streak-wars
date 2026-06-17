"""LeetCode integration via the public GraphQL + problems API.

Streaks are computed locally from the submission calendar so we control the
exact semantics (and can detect breaks) rather than trusting an opaque field.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone, date

import httpx

from .base import Challenge, Platform, PlatformStats, register_platform

GRAPHQL_URL = "https://leetcode.com/graphql"
PROBLEMS_URL = "https://leetcode.com/api/problems/all/"

# Sent on every request — LeetCode rejects calls without a browser-ish UA.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Referer": "https://leetcode.com",
    "Content-Type": "application/json",
}

_STATS_QUERY = """
query combined($username: String!, $cur: Int!, $prev: Int!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum { difficulty count }
    }
    cur: userCalendar(year: $cur) { submissionCalendar }
    prev: userCalendar(year: $prev) { submissionCalendar }
  }
}
"""

_DIFFICULTY_BY_LEVEL = {1: "Easy", 2: "Medium", 3: "Hard"}


def _active_dates(*calendars: str | None) -> set[date]:
    """Merge LeetCode submissionCalendar JSON strings into a set of UTC dates."""
    dates: set[date] = set()
    for cal in calendars:
        if not cal:
            continue
        for ts, count in json.loads(cal).items():
            if int(count) > 0:
                d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
                dates.add(d)
    return dates


def _current_streak(active: set[date], today: date) -> int:
    """Consecutive active days ending today (or yesterday if today is unsolved).

    Today being unsolved does not break the streak — the day isn't over. Only a
    full missed day (so the latest activity is >= 2 days ago) counts as broken.
    """
    if today in active:
        anchor = today
    elif (today - timedelta(days=1)) in active:
        anchor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    day = anchor
    while day in active:
        streak += 1
        day -= timedelta(days=1)
    return streak


@register_platform
class LeetCode(Platform):
    name = "leetcode"
    display_name = "LeetCode"
    supports_challenges = True

    async def fetch_stats(self, username: str) -> PlatformStats:
        today = datetime.now(timezone.utc).date()
        variables = {"username": username, "cur": today.year, "prev": today.year - 1}

        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.post(
                GRAPHQL_URL,
                json={"query": _STATS_QUERY, "variables": variables},
            )
            resp.raise_for_status()
            payload = resp.json()

        user = (payload.get("data") or {}).get("matchedUser")
        if not user:
            raise ValueError(f"LeetCode user '{username}' not found")

        active = _active_dates(
            (user.get("cur") or {}).get("submissionCalendar"),
            (user.get("prev") or {}).get("submissionCalendar"),
        )
        streak = _current_streak(active, today)

        by_difficulty = {
            row["difficulty"]: row["count"]
            for row in user["submitStatsGlobal"]["acSubmissionNum"]
        }
        total = by_difficulty.get("All", 0)

        return PlatformStats(
            platform=self.name,
            username=username,
            current_streak=streak,
            total_solved=total,
            extra={
                "easy": by_difficulty.get("Easy", 0),
                "medium": by_difficulty.get("Medium", 0),
                "hard": by_difficulty.get("Hard", 0),
                "last_active": max(active).isoformat() if active else None,
            },
        )

    async def random_challenge(self, difficulties=("Medium", "Hard")) -> Challenge:
        wanted = {d.lower() for d in difficulties}
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.get(PROBLEMS_URL)
            resp.raise_for_status()
            data = resp.json()

        pool = []
        for pair in data.get("stat_status_pairs", []):
            if pair.get("paid_only"):
                continue
            level = pair.get("difficulty", {}).get("level")
            diff = _DIFFICULTY_BY_LEVEL.get(level)
            if diff and diff.lower() in wanted:
                pool.append((pair["stat"], diff))

        if not pool:
            raise ValueError("No matching LeetCode problems found")

        stat, diff = random.choice(pool)
        slug = stat["question__title_slug"]
        return Challenge(
            platform=self.name,
            title=stat["question__title"],
            url=f"https://leetcode.com/problems/{slug}/",
            difficulty=diff,
        )
