from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from i18n.strings import t

_OPTIONS = [
    ("health_fully",     "fully_functional"),
    ("health_partially", "partially_functional"),
    ("health_disrupted", "largely_disrupted"),
    ("health_none",      "not_functioning"),
    ("health_unknown",   "unknown"),
]


def build(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(t(key, lang), callback_data=f"health:{value}")]
        for key, value in _OPTIONS
    ]
    return InlineKeyboardMarkup(rows)
