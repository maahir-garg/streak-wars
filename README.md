# Streak Wars

A private Telegram bot for tracking a friendly coding competition between a
group of participants. It tracks LeetCode streaks, posts a daily summary, and
announces when a streak breaks.

The platform layer is pluggable: LeetCode is one module implementing a shared
interface, so support for other sites (Codeforces, HackerRank, and so on) can be
added without changing the rest of the application.

## Status

A personal project, written in June 2026 for a small friend group. It is run by
hand on one machine, has no automated tests, and has no hosted instance.

## What it does

- Daily summary posted to a group chat showing every participant's streak and
  total solved, alongside LeetCode's official daily challenge.
- Streak-break announcements when a participant's streak drops to zero.
- Milestone announcements when a streak reaches 7, 14, 30, 50, 100, 150, 200,
  250, 365, 500, 730 or 1000 days.
- Evening reminders for anyone whose streak has no activity yet that day.
- Weekly recap of problems solved, naming a winner.
- `/streak` shows current streaks, total solved and the easy, medium and hard
  breakdown for all participants.
- `/leaderboard` ranks participants by current streak, shows total solved, and
  states who leads and by how many days.
- `/challenge` posts a random free medium or hard LeetCode problem.
- `/start` and `/help` list the commands.
- Commands are restricted to registered participants.

## Requirements

- Python 3.11 or newer.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).

## Setup

1. Create a bot with @BotFather (`/newbot`) and copy the token.

2. Install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create the configuration file and fill it in:

   ```bash
   cp .env.example .env
   ```

   See [Configuration](#configuration) for each value. To find Telegram ids,
   have each participant message [@userinfobot](https://t.me/userinfobot) for
   their user id, and add @RawDataBot to the group to read the group chat id.

4. Run the bot:

   ```bash
   python -m bot.main
   ```

## Configuration

All configuration is read from `.env`. No code changes are required.

| Variable | Description |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather. |
| `GROUP_CHAT_ID` | Chat that receives the daily summary and announcements. |
| `TIMEZONE` | IANA timezone name, for example `Asia/Singapore`. |
| `DAILY_SUMMARY_TIME` | Time of the daily summary, 24h `HH:MM`, in `TIMEZONE`. |
| `STREAK_CHECK_INTERVAL_MINUTES` | How often to check for breaks and milestones. |
| `REMINDER_TIME` | Evening reminder time, 24h `HH:MM`. Set to `off` to disable. |
| `WEEKLY_RECAP_DAY` | Day of the weekly recap, `sun` through `sat`. |
| `WEEKLY_RECAP_TIME` | Time of the weekly recap, 24h `HH:MM`. Set to `off` to disable. |
| `USER{n}_NAME` | Display name of participant `n`. |
| `USER{n}_TELEGRAM_ID` | Telegram user id of participant `n` (controls command access). |
| `USER{n}_LEETCODE` | LeetCode username of participant `n`. |

Participants are numbered `USER1`, `USER2`, `USER3`, and so on. Any number is
supported; the bot loads every consecutive `USER{n}` block that defines a name
and Telegram id. A participant's streak is tracked from their platform handle
alone, so their Telegram id is only required for issuing commands.

## Usage

Send these commands to the bot from a registered participant's account:

| Command | Result |
| --- | --- |
| `/start`, `/help` | Lists the commands. |
| `/streak` | Current streak, total solved and difficulty counts per participant. |
| `/leaderboard` | Participants ranked by current streak. |
| `/challenge` | A random medium or hard LeetCode problem. |

The daily summary, streak-break and milestone announcements, reminders and
weekly recap are posted to `GROUP_CHAT_ID` on the schedule set in `.env`. They
do not need a command.

## Running

While `python -m bot.main` is running the bot is online and responds to
commands, and the scheduled daily summary and streak checks run. Stopping the
process (Ctrl+C) takes the bot offline; stored data is preserved and resumes on
the next start. Do not run two instances with the same token simultaneously, as
Telegram permits only one poller per token.

For continuous operation, run the process on an always-on machine (a home
server or a small cloud VM) under a process manager such as `systemd` so it
restarts on failure and on reboot.

## Adding a platform

The application depends only on the `Platform` interface in
`bot/platforms/base.py`. To add a platform:

1. Create a module in `bot/platforms/`.
2. Subclass `Platform`, set `name` and `display_name`, and implement
   `fetch_stats`. Optionally implement `random_challenge` (set
   `supports_challenges = True`) and `daily_challenge` (set
   `supports_daily = True`).
3. Decorate the class with `@register_platform`.
4. Import the module in `bot/platforms/__init__.py`.
5. Add `USER{n}_{PLATFORM}` handles to `.env`.

The tracker, scheduler, leaderboard, break detection, and storage require no
changes. `bot/platforms/leetcode.py` is a complete example.

## How it works

On startup the bot records each participant's current streak without
announcing anything, so a stale break is not reported on the first poll. After
that a repeating job fetches fresh stats, compares the streak with the stored
value, and announces a break (streak fell from above zero to zero) or a
milestone crossing. The reminder job posts for anyone with a live streak and no
activity in the submission calendar yet today. The weekly recap compares total solved with the
count stored at the previous recap, then resets that count.

LeetCode streaks are computed in `bot/platforms/leetcode.py` from the public
submission calendar for the current and previous calendar year. A streak counts
consecutive days with at least one entry in that calendar, ending today or, if today has
none yet, yesterday. SQLite (`data/competition.db`, created on first run) holds
only the last seen streak and the weekly baseline for each participant.

## Project structure

```
bot/
  main.py            Entry point: builds the app, registers handlers and jobs.
  config.py          Loads .env into typed configuration objects.
  models.py          Data classes: User, BreakEvent, MilestoneEvent.
  storage.py         SQLite persistence of current streak and weekly baseline.
  messages.py        Message formatting and taunts.
  platforms/
    base.py          Platform interface and registry.
    leetcode.py      LeetCode implementation.
  services/
    tracker.py       Fetches stats; detects breaks and milestones; weekly recap.
    challenge.py     Selects random and daily challenges.
  handlers/
    commands.py      Command handlers and access control.
```

## Limitations

- Stats come from LeetCode's public, undocumented GraphQL and problems
  endpoints, with a browser-like User-Agent. They are not an official API and
  can change or rate-limit without notice. A failed fetch shows as "stats
  unavailable" and is skipped when checking for breaks.
- Streak days are calendar days in UTC, not in `TIMEZONE`. `TIMEZONE` only sets
  when the scheduled posts fire, so a day can roll over at a different local
  hour than the schedule suggests.
- Only LeetCode is implemented. The weekly recap and break detection assume one
  process running continuously; no catch-up happens for time the bot was off.
- Only the streak and weekly baseline are stored. Past streaks and personal
  bests are not tracked.
- There are no automated tests.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `InvalidToken` on startup | The token in `.env` is missing or incorrect. Recopy it from @BotFather. |
| Commands ignored in a group | In @BotFather, run `/setprivacy`, select the bot, and disable privacy mode, then re-add the bot to the group. |
| `Conflict: terminated by other getUpdates` | Two instances are running with the same token. Stop one. |
| "You are not authorized to use this bot." | The caller's Telegram id is not configured. Add it as a `USER{n}_TELEGRAM_ID` and restart. |
| Stats show as unavailable | A transient API error or an incorrect username. Verify the handle in `.env`. |
