from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from i18n.strings import t

# Label shown on the one-tap GPS button (all 6 UN languages)
_GPS_BUTTON_LABEL: dict[str, str] = {
    "en": "📍 Share my GPS location",
    "ar": "📍 مشاركة موقعي",
    "fr": "📍 Partager ma position GPS",
    "zh": "📍 分享我的 GPS 位置",
    "ru": "📍 Поделиться геолокацией",
    "es": "📍 Compartir mi ubicación GPS",
}


def _location_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """One-tap button that triggers Telegram's native location sharing."""
    label = _GPS_BUTTON_LABEL.get(lang, _GPS_BUTTON_LABEL["en"])
    return ReplyKeyboardMarkup(
        [[KeyboardButton(label, request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")

    # Store the highest-resolution file_id for later download
    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id

    await update.message.reply_text(t("photo_received", lang))
    await update.message.reply_text(
        t("send_location", lang),
        reply_markup=_location_keyboard(lang),
    )
