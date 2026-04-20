from telegram import Update
from telegram.ext import ContextTypes

from bot.i18n.strings import t


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")

    # Store the highest-resolution file_id for later download
    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id

    await update.message.reply_text(t("photo_received", lang))
    await update.message.reply_text(t("send_location", lang))
