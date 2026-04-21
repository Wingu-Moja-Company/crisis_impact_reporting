from telegram import Update
from telegram.ext import ContextTypes

from i18n.strings import t
from utils import detect_un_language


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = detect_un_language(update.effective_user.language_code)
    context.user_data.clear()
    context.user_data["lang"] = lang

    await update.message.reply_text(t("welcome", lang))
    await update.message.reply_text(t("send_photo", lang))
