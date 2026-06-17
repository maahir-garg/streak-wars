"""Telegram command handlers.

Shared objects (config, tracker) live in ``application.bot_data`` and are read
back here, so handlers stay plain functions.
"""

from __future__ import annotations

from functools import wraps

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import messages
from ..config import Config
from ..services.challenge import random_challenge
from ..services.tracker import Tracker


def _config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["config"]


def _tracker(context: ContextTypes.DEFAULT_TYPE) -> Tracker:
    return context.application.bot_data["tracker"]


def restricted(func):
    """Only the two (N) registered Telegram users may use a command."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        allowed = _config(context).allowed_ids
        if user is None or user.id not in allowed:
            if update.message:
                await update.message.reply_text(
                    "🔒 This is a private competition bot. You're not on the roster."
                )
            return
        return await func(update, context)

    return wrapper


async def _reply(update: Update, text: str) -> None:
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=False
    )


# --- public-ish bootstrap helper -----------------------------------------

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unrestricted: prints the caller's user id + this chat id (setup aid)."""
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"Your Telegram user id: {user.id if user else '?'}\n"
        f"This chat id: {chat.id if chat else '?'}\n\n"
        "Put these in your .env (USER*_TELEGRAM_ID and GROUP_CHAT_ID)."
    )


# --- restricted commands ---------------------------------------------------

@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(
        update,
        "👋 <b>Competition tracker online.</b>\n\n"
        "/streak — current streaks\n"
        "/leaderboard — who's winning\n"
        "/challenge — random medium/hard problem\n"
        "/help — this message",
    )


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


@restricted
async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshots = await _tracker(context).snapshot()
    await _reply(update, messages.format_streaks(snapshots))


@restricted
async def leaderboard_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    snapshots = await _tracker(context).snapshot()
    await _reply(update, messages.format_leaderboard(snapshots))


@restricted
async def challenge_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        challenge = await random_challenge()
    except Exception:  # noqa: BLE001
        await update.message.reply_text("⚠️ Couldn't fetch a challenge right now.")
        return
    await _reply(update, messages.format_challenge(challenge))
