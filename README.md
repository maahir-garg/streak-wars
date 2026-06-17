# Competition Tracker Bot 🔥

A private Telegram bot for a friendly coding competition between two friends. It
tracks **LeetCode streaks**, posts a morning scoreboard, taunts whoever lets
their streak die, and serves up random challenges.

It's built so adding other platforms later (Codeforces, HackerRank, GitHub…) is
a single small file — LeetCode is just the first one.

This README is also a gentle **"how do Telegram bots even work?"** guide, since
this might be your first one. Read top to bottom the first time.

---

## Table of contents

1. [How a Telegram bot actually works](#1-how-a-telegram-bot-actually-works)
2. [What this bot does](#2-what-this-bot-does)
3. [How the code is organized](#3-how-the-code-is-organized)
4. [First-time setup (from zero)](#4-first-time-setup-from-zero)
5. [Running it](#5-running-it)
6. [Changing the schedule / timezone](#6-changing-the-schedule--timezone)
7. [Keeping it running — free options](#7-keeping-it-running--free-options)
8. [Working on it with your friend (git)](#8-working-on-it-with-your-friend-git)
9. [Adding a new platform](#9-adding-a-new-platform)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. How a Telegram bot actually works

The single most important thing to understand:

> **A bot is just a program running on a computer. While that program is
> running, the bot is "online" and answers messages. When the program stops,
> the bot is deaf — there's nothing to receive your messages.**

You **cannot** text a stopped bot to wake it up. Something has to already be
running and listening.

Here's the full picture:

```
  You type /streak in Telegram
            │
            ▼
   Telegram's servers  ◀──────────────┐
            │                          │ our program keeps asking
            │  "any new messages?"     │ "anything for me?" (polling)
            ▼                          │
   Your running program  ──────────────┘
   (python -m bot.main)
            │
            │ figures out the answer (calls LeetCode's API)
            ▼
   Sends the reply back through Telegram → shows up in your chat
```

- **BotFather** is Telegram's "bot for making bots." You talk to it once to
  create your bot and get a **token** — a secret password that identifies your
  bot to Telegram.
- **Polling** (what we use) = our program repeatedly asks Telegram "got anything
  new?". Simple, needs no public website, works from your laptop. The downside:
  the program must be running to poll.
- **Webhooks** (the other approach) = Telegram pushes messages to a public URL
  you host. More setup, needs a server with a domain. We don't use this.

So "running the bot" = starting the Python program. "Stopping the bot" = killing
that program. That's the whole mental model.

---

## 2. What this bot does

- **Morning summary** — once a day at a time you choose, it posts both players'
  streaks side by side to your group, plus a fresh random medium/hard problem.
- **Streak-break taunts** — it periodically checks streaks; when someone's drops
  to zero, it roasts them in the group.
- **`/streak`** — current streaks for both players.
- **`/leaderboard`** — streaks, total solved, and who's ahead.
- **`/challenge`** — a random medium/hard LeetCode problem on demand.
- **`/id`** — prints your Telegram + chat id (a setup helper; the only command
  anyone can use).
- Everything except `/id` is **locked to the two registered players**.

> Reminder from section 1: the morning summary and break-taunts only happen
> *while the program is running*. On-demand commands work great when you run it
> locally; for the scheduled stuff to fire reliably, see
> [section 7](#7-keeping-it-running--free-options).

---

## 3. How the code is organized

```
bot/
  main.py            # START HERE. Wires everything up, starts the bot.
  config.py          # reads your .env into Python objects
  models.py          # plain data: User, BreakEvent
  storage.py         # SQLite — remembers last-known streaks (for break detection)
  messages.py        # every message the bot sends + the taunts
  getids.py          # one-off helper to discover your Telegram ids during setup
  platforms/
    base.py          # ⭐ the Platform "contract" + registry — the extensibility core
    leetcode.py      # the LeetCode implementation of that contract
  services/
    tracker.py       # fetches stats for everyone, detects streak breaks
    challenge.py     # picks a random challenge
  handlers/
    commands.py      # what each /command does, plus the "only 2 users" lock
```

**The one idea that makes it extensible:** everything works against the
`Platform` interface in `platforms/base.py`, never against LeetCode directly.
A platform is anything that can answer "what's this user's streak and total?"
LeetCode is just the first one registered. The tracker, scheduler, and commands
don't know or care which platforms exist — they loop over a registry. That's why
adding Codeforces later touches exactly one new file (see
[section 9](#9-adding-a-new-platform)).

How a `/streak` flows through the code:
```
commands.streak_command   (handlers/commands.py)
  → tracker.snapshot()     (services/tracker.py)   "get everyone's stats"
    → for each user, for each platform handle:
      → get_platform("leetcode").fetch_stats(username)   (platforms/leetcode.py)
        → calls LeetCode's API, computes the streak
  → messages.format_streaks(...)   (messages.py)   "make it pretty"
  → reply in the chat
```

---

## 4. First-time setup (from zero)

You need **Python 3.11+** installed. Check with `python3 --version`.

### Step 1 — Create the bot in Telegram
1. In Telegram, search **`@BotFather`** (blue checkmark), open it, tap **Start**.
2. Send **`/newbot`**.
3. Give it a **name** (display name, anything).
4. Give it a **username** — must be unique and end in `bot` (e.g. `streakwars_bot`).
5. BotFather sends a **token** like `8012345678:AAH9xY...`. **Copy it and keep it
   secret** — anyone with it controls your bot. (Lost it later? `@BotFather` →
   `/mybots` → your bot → *API Token*.)

### Step 2 — Make the group
6. Create a Telegram **group** and add your friend.
7. Add your bot to the group (group title → *Add members* → search its username).

### Step 3 — Install the code's dependencies
In a terminal, from the project folder:
```bash
python3 -m venv .venv          # create an isolated Python environment (once)
source .venv/bin/activate       # activate it — do this in every new terminal
pip install -r requirements.txt # install the bot's libraries
```

### Step 4 — Create your config file
```bash
cp .env.example .env
```
Open `.env` and paste your **token** into `TELEGRAM_BOT_TOKEN=`. Leave the rest
for a moment.

### Step 5 — Discover the ids (the bot needs to know who's who)
The bot identifies players and the group by numeric ids. Get them with the
helper (it only needs your token):
```bash
python -m bot.getids
```
Then in Telegram:
- Send **`/id` in the group** → copy the **chat id** (a negative number) into
  `GROUP_CHAT_ID`.
- Send **`/id` to the bot in a direct message** → that's your
  `USER1_TELEGRAM_ID`. Have your **friend DM the bot `/id`** too → their
  `USER2_TELEGRAM_ID`.

Press **Ctrl+C** to stop the helper.

> **Friend not around?** You don't need their Telegram id to *track* them — only
> their LeetCode username. Set `USER2_TELEGRAM_ID=0` for now (a placeholder that
> can't match anyone). Their streak still shows up; they just can't type
> commands until you put their real id in later and restart.

### Step 6 — Fill in `.env`
```
TELEGRAM_BOT_TOKEN=8012345678:AAH9xYourRealToken
GROUP_CHAT_ID=-1001234567890

TIMEZONE=Asia/Singapore
DAILY_SUMMARY_TIME=08:00
STREAK_CHECK_INTERVAL_MINUTES=60

USER1_NAME=Maahir
USER1_TELEGRAM_ID=111111111
USER1_LEETCODE=your_leetcode_username

USER2_NAME=Rohan
USER2_TELEGRAM_ID=222222222
USER2_LEETCODE=friends_leetcode_username
```
Your LeetCode username is the part in your profile URL:
`leetcode.com/u/**this_part**/`.

You're set up. ✅

---

## 5. Running it

```bash
source .venv/bin/activate    # if not already active
python -m bot.main
```
It connects and sits there running. Now in the group try `/streak`,
`/leaderboard`, `/challenge`.

**Stop it** with **Ctrl+C**. When it's stopped, the bot won't answer (see
[section 1](#1-how-a-telegram-bot-actually-works)). Your data is safe on disk;
just run it again to come back online.

> ⚠️ **Never run two copies with the same token at once** (e.g. laptop + a
> server). Telegram allows only one poller per token and you'll see a
> `Conflict: terminated by other getUpdates` error. For local tinkering while a
> copy is hosted, make a **second bot** with BotFather and use its token in a
> separate `.env` for testing.

---

## 6. Changing the schedule / timezone

All in `.env` — no code changes:

| Setting | Example | Meaning |
| --- | --- | --- |
| `TIMEZONE` | `Asia/Singapore` | Any [IANA tz name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). Controls what "8am" means. |
| `DAILY_SUMMARY_TIME` | `08:00` | When the morning post goes out, 24h `HH:MM`. `20:30` = 8:30pm. |
| `STREAK_CHECK_INTERVAL_MINUTES` | `60` | How often to check for broken streaks. |

After editing `.env`, restart the bot (Ctrl+C, then `python -m bot.main`) for
changes to take effect.

---

## 7. Keeping it running — free options

The bot needs a running program. Your laptop works, but it's only online when
the laptop is. Here are ways to keep it going **without paying**, easiest first.

### Option A — Just run it locally, on demand (free, simplest)
Start it when you want to use it, Ctrl+C when done. Perfect for the `/streak`,
`/leaderboard`, `/challenge` commands. The catch: the 8am summary only fires if
the program happens to be running at 8am. If you don't care about the automatic
morning post, **this is all you need.**

### Option B — A spare device at home (free if you own one)
An old laptop, a Raspberry Pi, a always-on desktop. Leave the program running on
it. Same commands as section 5. To keep it running after you close the terminal,
use `tmux` or `nohup`:
```bash
nohup python -m bot.main > bot.log 2>&1 &   # runs in background, logs to bot.log
```

### Option C — A free always-on cloud VM (free, more setup)
Some providers give a small Linux server **free forever**:
- **Oracle Cloud — Always Free** tier (a small ARM VM, genuinely free, best
  pick). 
- **Google Cloud free tier** (an `e2-micro` VM, free in some US regions).

Once you have one (Ubuntu), SSH in and:
```bash
sudo apt update && sudo apt install -y python3-venv git
git clone <your-repo-url> && cd tele-leetcode
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create .env on the server (paste your values; it's NOT in git on purpose)
nano .env
```
Then keep it running across logouts/reboots with a tiny **systemd** service.
Create `/etc/systemd/system/streakbot.service`:
```ini
[Unit]
Description=Competition Tracker Bot
After=network-online.target

[Service]
WorkingDirectory=/home/ubuntu/tele-leetcode
ExecStart=/home/ubuntu/tele-leetcode/.venv/bin/python -m bot.main
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now streakbot      # start now + on every boot
sudo systemctl status streakbot            # check it's running
journalctl -u streakbot -f                 # watch logs
```
`Restart=always` means it auto-recovers from crashes and reboots — truly
always-on, $0.

> Avoid "free web app" hosts like Render/Railway free tiers for this — they're
> built for websites and either sleep when idle or expire their credits, which
> breaks a polling bot. A plain free VM (Option C) is the reliable free path.

---

## 8. Working on it with your friend (git)

This project is a git repo, so you can both improve the bot. The flow on GitHub:

**One-time: give your friend access**
1. Push the repo to GitHub (make it **private**):
   ```bash
   gh repo create tele-leetcode --private --source=. --push
   # no gh CLI? create an empty repo on github.com, then:
   #   git remote add origin https://github.com/YOU/tele-leetcode.git
   #   git push -u origin main
   ```
2. On GitHub: repo → **Settings → Collaborators → Add people** → your friend's
   GitHub username. They accept the email invite.

**Your friend gets the code**
```bash
git clone https://github.com/YOU/tele-leetcode.git
cd tele-leetcode
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # they make their OWN .env (secrets are never in git)
```

**Everyday changes (both of you)**
```bash
git pull                       # get the latest before starting
# ...make edits...
git add -A
git commit -m "what I changed"
git push                       # share it
```
If you both edit and push, whoever pushes second runs `git pull` first to merge.
For bigger changes, use a **branch** + Pull Request:
```bash
git checkout -b my-feature
# ...edit, commit...
git push -u origin my-feature
# then open a Pull Request on GitHub for the other to review
```

> Your `.env` (token, ids) is **never** shared via git — `.gitignore` blocks it.
> Each person and each server keeps its own `.env`. The repo only carries
> `.env.example` as a template.

---

## 9. Adding a new platform

The payoff of the design. To add, say, Codeforces:

1. Create `bot/platforms/codeforces.py`.
2. Subclass `Platform`, set `name = "codeforces"` and `display_name`, implement
   `fetch_stats(username)` to return a `PlatformStats`. Optionally implement
   `random_challenge(...)` and set `supports_challenges = True`.
3. Decorate the class with `@register_platform`.
4. Import it in `bot/platforms/__init__.py` (one line).
5. Add handles to `.env`: `USER1_CODEFORCES=...`, `USER2_CODEFORCES=...`.

Done. The tracker, scheduler, leaderboard, break-detection, and storage all pick
it up automatically — they were written against the `Platform` interface, not
against LeetCode. Use `bot/platforms/leetcode.py` as your worked example.

---

## 10. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `InvalidToken: ... rejected by the server` | Your `.env` token is wrong or still the placeholder. Re-copy it from BotFather (`/mybots`). |
| Bot ignores `/streak` in the group | BotFather → `/setprivacy` → your bot → **Disable**, then remove & re-add the bot to the group. |
| `Conflict: terminated by other getUpdates` | Two copies are running with the same token. Stop one. Use a second bot/token for dev. |
| `"... not on the roster"` reply | Your Telegram id isn't in `.env`. DM the bot `/id`, put the number in `USER*_TELEGRAM_ID`, restart. |
| Streak shows 0 but you solved today | Today not-yet-solved keeps the streak alive but counts from yesterday; a *full* missed day breaks it. If still wrong, double-check the LeetCode username in `.env`. |
| Stats say "couldn't fetch" | LeetCode API hiccup or a typo'd username. It retries on the next check; verify the username. |

---

Happy grinding. May the best streak win. 🏆
