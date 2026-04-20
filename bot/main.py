"""
Entry point for two run modes:
  - Azure Functions webhook (production)
  - Polling mode for local development: python bot/main.py --poll
"""

import argparse
import asyncio

import azure.functions as func
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.handlers import confirm, form, location, photo, start
from bot.utils import get_secret

_app: Application | None = None


async def _get_app() -> Application:
    global _app
    if _app is None:
        token = get_secret("TELEGRAM_BOT_TOKEN")
        _app = Application.builder().token(token).build()
        _app.add_handler(CommandHandler("start", start.handle))
        _app.add_handler(MessageHandler(filters.PHOTO, photo.handle))
        _app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, location.handle))
        _app.add_handler(CallbackQueryHandler(form.handle))
        await _app.initialize()
    return _app


# ---------------------------------------------------------------------------
# Azure Functions webhook handler
# ---------------------------------------------------------------------------

async def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    app = await _get_app()
    update = Update.de_json(req.get_json(), app.bot)
    await app.process_update(update)
    return func.HttpResponse("OK", status_code=200)


# ---------------------------------------------------------------------------
# Local polling mode
# ---------------------------------------------------------------------------

def _run_polling() -> None:
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or get_secret("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start.handle))
    app.add_handler(MessageHandler(filters.PHOTO, photo.handle))
    app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, location.handle))
    app.add_handler(CallbackQueryHandler(form.handle))
    print("Bot polling started — press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll", action="store_true", help="Run in polling mode (local dev)")
    args = parser.parse_args()
    if args.poll:
        _run_polling()
