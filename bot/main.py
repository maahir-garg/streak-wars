"""Entry point: wires handlers, scheduled jobs, and starts long-polling."""

from __future__ import annotations

import logging

from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from . import messages
from .config import Config, load_config
from .handlers import commands
from .services.challenge import random_challenge
from .services.tracker import Tracker
from .storage import Storage

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("competition-bot")


async def _post(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    config: Config = context.application.bot_data["config"]
    await context.bot.send_message(
        chat_id=config.group_chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
    )


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Morning post: side-by-side streaks + a fresh challenge."""
    tracker: Tracker = context.application.bot_data["tracker"]
    snapshots = await tracker.snapshot()
    await _post(context, messages.format_daily_summary(snapshots))

    try:
        challenge = await random_challenge()
        await _post(context, messages.format_challenge(challenge))
    except Exception:  # noqa: BLE001
        log.warning("Daily challenge fetch failed", exc_info=True)


async def break_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Poll for streak breaks and taunt the group when one happens."""
    tracker: Tracker = context.application.bot_data["tracker"]
    for event in await tracker.check_breaks():
        await _post(context, messages.format_break(event))


async def _post_init(app: Application) -> None:
    """Seed streak state once at startup so the first poll isn't a false break."""
    tracker: Tracker = app.bot_data["tracker"]
    await tracker.check_breaks()
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
    app.add_handler(CommandHandler("challenge", commands.challenge_command))

    app.job_queue.run_daily(daily_summary_job, time=config.daily_summary_time)
    app.job_queue.run_repeating(
        break_check_job,
        interval=config.streak_check_interval_minutes * 60,
        first=config.streak_check_interval_minutes * 60,
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
