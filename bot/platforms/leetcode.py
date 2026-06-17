"""LeetCode integration via the public GraphQL and problems APIs.

Streaks are computed locally from the submission calendar so the semantics are
explicit and break detection is reliable.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone

import httpx

from .base import Challenge, Platform, PlatformStats, register_platform

GRAPHQL_URL = "https://leetcode.com/graphql"
PROBLEMS_URL = "https://leetcode.com/api/problems/all/"
SITE_URL = "https://leetcode.com"

# LeetCode rejects requests without a browser-like User-Agent.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Referer": "https://leetcode.com",
    "Content-Type": "application/json",
}

# Two calendar years are fetched so a streak spanning Jan 1 is computed correctly.
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

_DAILY_QUERY = """
query daily {
  activeDailyCodingChallengeQuestion {
    link
    question { title difficulty }
  }
}
"""

_DIFFICULTY_BY_LEVEL = {1: "Easy", 2: "Medium", 3: "Hard"}


def _active_dates(*calendars: str | None) -> set[date]:
    """Merge submissionCalendar JSON strings into a set of UTC dates."""
    dates: set[date] = set()
    for calendar in calendars:
        if not calendar:
            continue
        for ts, count in json.loads(calendar).items():
            if int(count) > 0:
                dates.add(datetime.fromtimestamp(int(ts), tz=timezone.utc).date())
    return dates


def _current_streak(active: set[date], today: date) -> int:
    """Count consecutive active days ending today, or yesterday if today is unsolved.

    An unsolved today does not break the streak, since the day is not over. Only
    a full missed day (latest activity two or more days ago) counts as broken.
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
    supports_daily = True

    async def fetch_stats(self, username: str) -> PlatformStats:
        today = datetime.now(timezone.utc).date()
        variables = {"username": username, "cur": today.year, "prev": today.year - 1}

        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.post(
                GRAPHQL_URL, json={"query": _STATS_QUERY, "variables": variables}
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
        by_difficulty = {
            row["difficulty"]: row["count"]
            for row in user["submitStatsGlobal"]["acSubmissionNum"]
        }

        return PlatformStats(
            platform=self.name,
            username=username,
            current_streak=_current_streak(active, today),
            total_solved=by_difficulty.get("All", 0),
            solved_today=today in active,
            easy=by_difficulty.get("Easy", 0),
            medium=by_difficulty.get("Medium", 0),
            hard=by_difficulty.get("Hard", 0),
        )

    async def random_challenge(self, difficulties=("Medium", "Hard")) -> Challenge:
        wanted = {d.lower() for d in difficulties}
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.get(PROBLEMS_URL)
            resp.raise_for_status()
            data = resp.json()

        pool = [
            (pair["stat"], _DIFFICULTY_BY_LEVEL[pair["difficulty"]["level"]])
            for pair in data.get("stat_status_pairs", [])
            if not pair.get("paid_only")
            and _DIFFICULTY_BY_LEVEL.get(pair["difficulty"]["level"], "").lower()
            in wanted
        ]
        if not pool:
            raise ValueError("No matching LeetCode problems found")

        stat, difficulty = random.choice(pool)
        slug = stat["question__title_slug"]
        return Challenge(
            platform=self.name,
            title=stat["question__title"],
            url=f"{SITE_URL}/problems/{slug}/",
            difficulty=difficulty,
        )

    async def daily_challenge(self) -> Challenge:
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.post(GRAPHQL_URL, json={"query": _DAILY_QUERY})
            resp.raise_for_status()
            payload = resp.json()

        daily = (payload.get("data") or {}).get("activeDailyCodingChallengeQuestion")
        if not daily:
            raise ValueError("LeetCode daily challenge unavailable")

        return Challenge(
            platform=self.name,
            title=daily["question"]["title"],
            url=f"{SITE_URL}{daily['link']}",
            difficulty=daily["question"]["difficulty"],
        )
