"""Telegram command handlers.

Shared objects (config, tracker) live in ``application.bot_data`` and are read
back here, so handlers remain plain functions.
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

_HELP_TEXT = (
    "Available commands:\n"
    "/streak - current streaks for all participants\n"
    "/leaderboard - standings and who is leading\n"
    "/challenge - a random medium or hard problem"
)


def _config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["config"]


def _tracker(context: ContextTypes.DEFAULT_TYPE) -> Tracker:
    return context.application.bot_data["tracker"]


def restricted(func):
    """Allow only registered participants to use a command."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None or user.id not in _config(context).allowed_ids:
            if update.message:
                await update.message.reply_text(
                    "You are not authorized to use this bot."
                )
            return
        return await func(update, context)

    return wrapper


async def _reply(update: Update, text: str) -> None:
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, _HELP_TEXT)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, _HELP_TEXT)


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
async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        challenge = await random_challenge()
    except Exception:
        await update.message.reply_text("Could not fetch a challenge right now.")
        return
    await _reply(update, messages.format_challenge(challenge))
