"""Entry point: wires handlers, scheduled jobs, and starts long-polling."""

from __future__ import annotations

import logging

from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from . import messages
from .config import Config, load_config
from .handlers import commands
from .services.challenge import daily_challenge, random_challenge
from .services.tracker import Tracker
from .storage import Storage

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("streak-wars")


async def _post(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    config: Config = context.application.bot_data["config"]
    await context.bot.send_message(
        chat_id=config.group_chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
    )


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Morning post: standings plus the official daily challenge."""
    tracker: Tracker = context.application.bot_data["tracker"]
    snapshots = await tracker.snapshot()
    await _post(context, messages.format_daily_summary(snapshots))

    try:
        challenge = await daily_challenge()
        await _post(context, messages.format_challenge(challenge, "Daily challenge"))
    except Exception:
        log.warning("Daily challenge fetch failed; falling back to random", exc_info=True)
        try:
            await _post(context, messages.format_challenge(await random_challenge()))
        except Exception:
            log.warning("Random challenge fetch also failed", exc_info=True)


async def poll_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Poll for breaks, milestones, and records, and announce them."""
    tracker: Tracker = context.application.bot_data["tracker"]
    for event in await tracker.poll():
        await _post(context, messages.format_event(event))


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nudge anyone whose live streak has no activity yet today."""
    tracker: Tracker = context.application.bot_data["tracker"]
    for item in await tracker.at_risk():
        await _post(context, messages.format_reminder(item))


async def weekly_recap_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post the week's solved counts and crown a winner."""
    tracker: Tracker = context.application.bot_data["tracker"]
    await _post(context, messages.format_weekly_recap(await tracker.weekly_recap()))


async def _post_init(app: Application) -> None:
    """Seed streak state once at startup so the first poll isn't a false break."""
    tracker: Tracker = app.bot_data["tracker"]
    await tracker.seed()
    log.info("Initial streak state seeded.")


def build_application(config: Config) -> Application:
    storage = Storage()
    tracker = Tracker(config, storage)

    app = Application.builder().token(config.bot_token).post_init(_post_init).build()
    app.bot_data["config"] = config
    app.bot_data["tracker"] = tracker
    app.bot_data["storage"] = storage

    app.add_handler(CommandHandler("start", commands.start_command))
    app.add_handler(CommandHandler("help", commands.help_command))
    app.add_handler(CommandHandler("streak", commands.streak_command))
    app.add_handler(CommandHandler("leaderboard", commands.leaderboard_command))
    app.add_handler(CommandHandler("records", commands.records_command))
    app.add_handler(CommandHandler("challenge", commands.challenge_command))

    jobs = app.job_queue
    jobs.run_daily(daily_summary_job, time=config.daily_summary_time)
    jobs.run_repeating(
        poll_job,
        interval=config.streak_check_interval_minutes * 60,
        first=config.streak_check_interval_minutes * 60,
    )
    if config.reminder_time:
        jobs.run_daily(reminder_job, time=config.reminder_time)
        log.info("Streak reminders enabled at %s", config.reminder_time)
    if config.weekly_recap_time:
        jobs.run_daily(
            weekly_recap_job,
            time=config.weekly_recap_time,
            days=(config.weekly_recap_day,),
        )
        log.info(
            "Weekly recap enabled on day %d at %s",
            config.weekly_recap_day,
            config.weekly_recap_time,
        )
    return app


def main() -> None:
    config = load_config()
    log.info(
        "Starting with %d user(s); daily summary at %s",
        len(config.users),
        config.daily_summary_time,
    )
    app = build_application(config)
    app.run_polling()


if __name__ == "__main__":
    main()
