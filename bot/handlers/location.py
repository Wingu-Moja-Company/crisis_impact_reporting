import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from i18n.strings import t
from keyboards import damage_level

# Matches what3words patterns with or without the /// prefix:
#   filled.count.soap  or  ///filled.count.soap
_W3W_RE = re.compile(r"^/{0,3}\s*([a-z]+\.[a-z]+\.[a-z]+)\s*$", re.IGNORECASE)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")

    if update.message.location:
        context.user_data["gps_lat"] = update.message.location.latitude
        context.user_data["gps_lon"] = update.message.location.longitude
    elif update.message.text:
        text = update.message.text.strip()
        match = _W3W_RE.match(text)
        if match:
            context.user_data["what3words"] = match.group(1).lower()
        else:
            context.user_data["location_description"] = text

    # Dismiss the GPS reply keyboard before showing the inline damage keyboard
    await update.message.reply_text(
        t("select_damage_level", lang),
        reply_markup=ReplyKeyboardRemove(),
    )
    # Send the inline keyboard as a separate message
    await update.message.reply_text(
        "👇",
        reply_markup=damage_level.build(lang),
    )
