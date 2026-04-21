from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from i18n.strings import t

_TYPES = [
    ("crisis_earthquake",   "earthquake"),
    ("crisis_flood",        "flood"),
    ("crisis_tsunami",      "tsunami"),
    ("crisis_hurricane",    "hurricane"),
    ("crisis_wildfire",     "wildfire"),
    ("crisis_explosion",    "explosion"),
    ("crisis_chemical",     "chemical"),
    ("crisis_conflict",     "conflict"),
    ("crisis_civil_unrest", "civil_unrest"),
]


def build(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(t(key, lang), callback_data=f"crisis:{value}")]
        for key, value in _TYPES
    ]
    return InlineKeyboardMarkup(rows)
