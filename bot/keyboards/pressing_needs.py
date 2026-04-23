from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from i18n.strings import t

_OPTIONS = [
    ("needs_food_water",        "food_water"),
    ("needs_cash_financial",    "cash_financial"),
    ("needs_healthcare",        "healthcare"),
    ("needs_shelter",           "shelter"),
    ("needs_livelihoods",       "livelihoods"),
    ("needs_wash",              "wash"),
    ("needs_basic_services",    "basic_services"),
    ("needs_protection",        "protection"),
    ("needs_community_support", "community_support"),
    ("needs_other",             "other"),
]


def build(lang: str, selected: set[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    rows = []
    for string_key, value in _OPTIONS:
        label = t(string_key, lang)
        if value in selected:
            label = f"✔ {label}"
        rows.append([InlineKeyboardButton(label, callback_data=f"needs:{value}")])
    rows.append([InlineKeyboardButton("✅ Done", callback_data="needs:done")])
    return InlineKeyboardMarkup(rows)
