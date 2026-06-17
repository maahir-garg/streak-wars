# Competition Tracker Bot

A private Telegram bot for a friendly coding competition between two friends.
Tracks **LeetCode streaks** today, but the platform layer is pluggable — adding
Codeforces, HackerRank, etc. is a single new module.

## Features

- **Daily morning summary** posted to your group chat: both users' streaks side
  by side, plus a fresh random medium/hard challenge.
- **Streak-break taunts** — when someone's streak dies, the bot announces it
  with a randomly-picked roast.
- `/streak` — current streaks for everyone.
- `/leaderboard` — streaks, total solved, and who's winning.
- `/challenge` — a random medium/hard LeetCode problem on demand.
- Locked to the registered Telegram users only.

## Setup

1. **Create the bot** with [@BotFather](https://t.me/BotFather) and copy the token.
2. **Install deps** (Python 3.11+):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configure**:
   ```bash
   cp .env.example .env
   ```
   Fill in `TELEGRAM_BOT_TOKEN`, the two users' names / Telegram ids /
   LeetCode usernames, and `GROUP_CHAT_ID`.

   To find the ids: add the bot to your group, run the bot (step 4), and send
   `/id` in the group — it replies with your user id and the chat id. Paste
   those into `.env`. (`/id` is the only command anyone can use; everything
   else is locked to the roster.)
4. **Run**:
   ```bash
   python -m bot.main
   ```
   Leave it running. It long-polls Telegram (no public URL/webhook needed) and
   uses an internal scheduler for the daily summary and break checks.

## Configuration reference

| Var | Meaning |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `GROUP_CHAT_ID` | Chat that gets daily summaries + taunts (usually negative) |
| `TIMEZONE` | IANA tz, e.g. `Asia/Kolkata` |
| `DAILY_SUMMARY_TIME` | 24h `HH:MM` in `TIMEZONE` |
| `STREAK_CHECK_INTERVAL_MINUTES` | How often to poll for breaks |
| `USER{n}_NAME` / `USER{n}_TELEGRAM_ID` | Per-user identity |
| `USER{n}_LEETCODE` | That user's LeetCode handle |

## Adding a new platform

The whole design hinges on `bot/platforms/base.py::Platform`. To add one:

1. Create `bot/platforms/<name>.py`.
2. Subclass `Platform`, set `name` / `display_name`, implement `fetch_stats`
   (and optionally `random_challenge` + `supports_challenges = True`).
3. Decorate the class with `@register_platform`.
4. Import it in `bot/platforms/__init__.py`.
5. Add `USER{n}_<NAME>` handles to `.env`.

No changes needed in the tracker, handlers, scheduler, or storage — they all
work off the registry and each user's `handles` dict.

## Project layout

```
bot/
  config.py          # .env loading; user + platform wiring
  models.py          # User, BreakEvent
  storage.py         # SQLite persistence of last-known streaks
  messages.py        # all formatting + taunts (HTML)
  main.py            # entry point: handlers + scheduled jobs + polling
  platforms/
    base.py          # Platform interface + registry  <-- extensibility core
    leetcode.py      # LeetCode implementation
  services/
    tracker.py       # fetch stats, detect breaks
    challenge.py     # pick a random challenge
  handlers/
    commands.py      # /streak /leaderboard /challenge /id + auth
```
