from telegram import Update
from telegram.ext import ContextTypes

from bot.i18n.strings import t
from bot.keyboards import damage_level


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")

    if update.message.location:
        context.user_data["gps_lat"] = update.message.location.latitude
        context.user_data["gps_lon"] = update.message.location.longitude
    elif update.message.text and update.message.text.startswith("///"):
        context.user_data["what3words"] = update.message.text.strip().lstrip("/")
    else:
        context.user_data["location_description"] = update.message.text

    await update.message.reply_text(
        t("select_damage_level", lang),
        reply_markup=damage_level.build(lang),
    )
