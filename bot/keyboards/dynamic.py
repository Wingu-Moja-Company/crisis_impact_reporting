"""
Schema-driven InlineKeyboard builders.

Builds Telegram InlineKeyboardMarkup from the dynamic schema definition
fetched from the pipeline API.  All functions are pure — they do not touch
user_data or Telegram context.

Callback data formats (64-byte Telegram limit respected):
  dmg:{value}          — damage level selected
  infra:{value}        — infrastructure type toggle
  infra:done           — infrastructure type selection complete
  f:{idx}:{value}      — custom field (select / boolean) at position idx
  fm:{idx}:{value}     — custom field multiselect toggle
  fd:{idx}             — custom field multiselect done
  fs:{idx}             — skip optional custom field
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def _label(obj: dict, lang: str) -> str:
    """Return the label for lang, falling back to English."""
    if isinstance(obj, dict):
        return obj.get(lang) or obj.get("en", "")
    return str(obj)


_DONE: dict[str, str] = {
    "en": "Done ✓", "fr": "Terminé ✓", "ar": "تم ✓",
    "sw": "Imekamilika ✓", "es": "Listo ✓", "zh": "完成 ✓",
}
_SKIP: dict[str, str] = {
    "en": "Skip →", "fr": "Passer →", "ar": "تخطى →",
    "sw": "Ruka →", "es": "Omitir →", "zh": "跳过 →",
}
_YES: dict[str, str] = {
    "en": "Yes ✅", "fr": "Oui ✅", "ar": "نعم ✅",
    "sw": "Ndiyo ✅", "es": "Sí ✅", "zh": "是 ✅",
}
_NO: dict[str, str] = {
    "en": "No ❌", "fr": "Non ❌", "ar": "لا ❌",
    "sw": "Hapana ❌", "es": "No ❌", "zh": "否 ❌",
}


# ---------------------------------------------------------------------------
# System fields
# ---------------------------------------------------------------------------

def build_damage_level(schema: dict, lang: str) -> InlineKeyboardMarkup:
    """Keyboard for the mandatory damage_level system field."""
    field = schema.get("system_fields", {}).get("damage_level", {})
    options = field.get("options", {})
    rows = []
    for value, labels in options.items():
        label = _label(labels, lang)
        rows.append([InlineKeyboardButton(label, callback_data=f"dmg:{value}")])
    if not rows:
        # Absolute fallback
        rows = [
            [InlineKeyboardButton("Minimal", callback_data="dmg:minimal")],
            [InlineKeyboardButton("Partial", callback_data="dmg:partial")],
            [InlineKeyboardButton("Complete", callback_data="dmg:complete")],
        ]
    return InlineKeyboardMarkup(rows)


def build_infra_type(
    schema: dict, lang: str, selected: set[str]
) -> InlineKeyboardMarkup:
    """Keyboard for the mandatory infrastructure_type system field (multiselect)."""
    field = schema.get("system_fields", {}).get("infrastructure_type", {})
    options = field.get("options", [])
    rows = []
    for opt in options:
        value = opt.get("value", "")
        label = _label(opt.get("labels", {}), lang)
        tick = "✅ " if value in selected else ""
        rows.append([InlineKeyboardButton(tick + label, callback_data=f"infra:{value}")])
    done = _DONE.get(lang, "Done ✓")
    rows.append([InlineKeyboardButton(done, callback_data="infra:done")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Custom field keyboards
# ---------------------------------------------------------------------------

def build_select_field(
    field: dict, lang: str, idx: int
) -> InlineKeyboardMarkup:
    """
    Keyboard for a custom field of type 'select'.
    Callback: f:{idx}:{value}
    """
    options = field.get("options", [])
    rows = []
    for opt in options:
        value = opt.get("value", "")
        label = _label(opt.get("labels", {}), lang)
        rows.append([InlineKeyboardButton(label, callback_data=f"f:{idx}:{value}")])
    if not field.get("required", True):
        skip = _SKIP.get(lang, "Skip →")
        rows.append([InlineKeyboardButton(skip, callback_data=f"fs:{idx}")])
    return InlineKeyboardMarkup(rows)


def build_multiselect_field(
    field: dict, lang: str, idx: int, selected: set[str]
) -> InlineKeyboardMarkup:
    """
    Keyboard for a custom field of type 'multiselect'.
    Callback: fm:{idx}:{value} (toggle) / fd:{idx} (done)
    """
    options = field.get("options", [])
    rows = []
    for opt in options:
        value = opt.get("value", "")
        label = _label(opt.get("labels", {}), lang)
        tick = "✅ " if value in selected else ""
        rows.append([InlineKeyboardButton(tick + label, callback_data=f"fm:{idx}:{value}")])

    done = _DONE.get(lang, "Done ✓")
    done_row = [InlineKeyboardButton(done, callback_data=f"fd:{idx}")]
    if not field.get("required", True):
        skip = _SKIP.get(lang, "Skip →")
        done_row.append(InlineKeyboardButton(skip, callback_data=f"fs:{idx}"))
    rows.append(done_row)
    return InlineKeyboardMarkup(rows)


def build_boolean_field(
    field: dict, lang: str, idx: int
) -> InlineKeyboardMarkup:
    """
    Keyboard for a custom field of type 'boolean'.
    Callback: f:{idx}:true / f:{idx}:false
    """
    yes = _YES.get(lang, "Yes")
    no = _NO.get(lang, "No")
    rows = [
        [
            InlineKeyboardButton(yes, callback_data=f"f:{idx}:true"),
            InlineKeyboardButton(no, callback_data=f"f:{idx}:false"),
        ]
    ]
    if not field.get("required", True):
        skip = _SKIP.get(lang, "Skip →")
        rows.append([InlineKeyboardButton(skip, callback_data=f"fs:{idx}")])
    return InlineKeyboardMarkup(rows)


def field_question(field: dict, lang: str, idx: int, total: int) -> str:
    """
    Return the question text for a custom field, with progress indicator.
    e.g. "(3/7) What is the estimated water level?"
    """
    labels = field.get("labels", {})
    question = _label(labels, lang)
    optional_hint = ""
    if not field.get("required", True):
        optional_hints = {
            "en": " (optional)", "fr": " (optionnel)", "ar": " (اختياري)",
            "sw": " (si lazima)", "es": " (opcional)", "zh": " （可选）",
        }
        optional_hint = optional_hints.get(lang, " (optional)")
    return f"({idx + 1}/{total}) {question}{optional_hint}"


def system_field_question(field_key: str, schema: dict, lang: str) -> str:
    """Return the question label for a system field."""
    field = schema.get("system_fields", {}).get(field_key, {})
    labels = field.get("labels", {})
    return _label(labels, lang) or f"Select {field_key}"
