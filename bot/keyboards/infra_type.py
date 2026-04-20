from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.i18n.strings import t

_TYPES = [
    ("infra_residential",  "residential"),
    ("infra_commercial",   "commercial"),
    ("infra_government",   "government"),
    ("infra_utility",      "utility"),
    ("infra_transport",    "transport"),
    ("infra_community",    "community"),
    ("infra_public_space", "public_space"),
    ("infra_other",        "other"),
]


def build(lang: str, selected: set[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    rows = []
    for string_key, value in _TYPES:
        label = t(string_key, lang)
        if value in selected:
            label = f"✔ {label}"
        rows.append([InlineKeyboardButton(label, callback_data=f"infra:{value}")])
    rows.append([InlineKeyboardButton("✅ Done", callback_data="infra:done")])
    return InlineKeyboardMarkup(rows)
