"""One-off helper to discover Telegram IDs during setup.

Unlike the full bot, this needs ONLY your TELEGRAM_BOT_TOKEN in .env — not the
chat id or user ids yet (that's what this is for). Run it, send /id in your
group and in a direct message to the bot, copy the numbers it prints into your
.env, then stop it with Ctrl+C and run the real bot.

    python -m bot.getids
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

from .handlers.commands import id_command

load_dotenv()


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your .env first.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("id", id_command))

    print(
        "\nBot is listening. Now in Telegram:\n"
        "  1. Send /id in your GROUP   -> note the 'This chat id' value (GROUP_CHAT_ID)\n"
        "  2. Send /id to the bot in a DM, and have your friend do the same\n"
        "     -> each 'Your Telegram user id' is a USER*_TELEGRAM_ID\n"
        "When you have the numbers, press Ctrl+C and put them in .env.\n"
    )
    app.run_polling()


if __name__ == "__main__":
    main()
