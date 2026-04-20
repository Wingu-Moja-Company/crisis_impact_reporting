from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.i18n.strings import t


def build(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("damage_minimal",  lang), callback_data="dmg:minimal")],
        [InlineKeyboardButton(t("damage_partial",  lang), callback_data="dmg:partial")],
        [InlineKeyboardButton(t("damage_complete", lang), callback_data="dmg:complete")],
    ])
