import os

from telegram import Update
from telegram.ext import ContextTypes

from i18n.strings import t
from schema import fetch_schema
from utils import detect_un_language


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = detect_un_language(update.effective_user.language_code)
    context.user_data.clear()
    context.user_data["lang"] = lang

    # Fetch the current form schema from the pipeline API and cache it for the
    # duration of this conversation.  Falls back to a minimal hardcoded schema
    # if the API is unreachable — the bot never fails to start a report.
    crisis_event_id = os.environ.get("CRISIS_EVENT_ID", "ke-flood-dev")
    schema = fetch_schema(crisis_event_id)
    context.user_data["schema"] = schema

    if schema.get("_fallback"):
        await update.message.reply_text(t("schema_unavailable", lang))

    await update.message.reply_text(t("welcome", lang))
    await update.message.reply_text(t("send_photo", lang))
