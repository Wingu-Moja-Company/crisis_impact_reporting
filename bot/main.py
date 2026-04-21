"""
Entry point for two run modes:
  - Azure Functions webhook (production)
  - Polling mode for local development: python bot/main.py --poll
"""

import argparse
import asyncio
import hmac
import os

import azure.functions as func
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers import confirm, form, location, photo, start
from utils import get_secret

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
    # ── Security: verify Telegram webhook secret token ──────────────────────
    # Set TELEGRAM_WEBHOOK_SECRET in App Settings and register the webhook
    # with the same value via setWebhook?secret_token=<value>.
    # If the env var is absent (local dev / first deploy) verification is skipped.
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if expected_secret:
        incoming_secret = req.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(incoming_secret, expected_secret):
            return func.HttpResponse("Forbidden", status_code=403)

    app = await _get_app()
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse("Bad Request", status_code=400)

    update = Update.de_json(body, app.bot)
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
