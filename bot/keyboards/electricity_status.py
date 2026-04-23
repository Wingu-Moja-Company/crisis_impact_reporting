from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from i18n.strings import t

_OPTIONS = [
    ("elec_no_damage",  "no_damage"),
    ("elec_minor",      "minor"),
    ("elec_moderate",   "moderate"),
    ("elec_severe",     "severe"),
    ("elec_destroyed",  "destroyed"),
    ("elec_unknown",    "unknown"),
]


def build(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(t(key, lang), callback_data=f"elec:{value}")]
        for key, value in _OPTIONS
    ]
    return InlineKeyboardMarkup(rows)
