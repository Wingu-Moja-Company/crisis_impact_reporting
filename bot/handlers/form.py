"""
Schema-driven form state machine for the Telegram bot.

Callback data routing:
  dmg:{value}       → damage level chosen (system field)
  infra:{value}     → infrastructure type toggle (system field, multiselect)
  infra:done        → infrastructure selection complete
  f:{idx}:{value}   → custom field answer (select / boolean)
  fm:{idx}:{value}  → custom field multiselect toggle
  fd:{idx}          → custom field multiselect done
  fs:{idx}          → skip optional custom field

After all custom fields are answered, calls confirm.submit().
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from i18n.strings import t
from keyboards import dynamic
from schema import fallback_schema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _schema(context) -> dict:
    return context.user_data.get("schema") or fallback_schema()


def _custom_fields(context) -> list:
    return _schema(context).get("custom_fields", [])


async def _advance_custom_fields(
    query, context, lang: str, start_idx: int
) -> None:
    """
    Move to the next custom field starting from start_idx.
    If all fields are done, call confirm.submit().
    """
    fields = _custom_fields(context)
    idx = start_idx

    # Skip any hidden/skipped fields (future extension)
    while idx < len(fields):
        field = fields[idx]
        field_type = field.get("type", "select")
        question = dynamic.field_question(field, lang, idx, len(fields))

        if field_type == "select":
            await query.edit_message_text(
                question,
                reply_markup=dynamic.build_select_field(field, lang, idx),
            )
            return

        elif field_type == "boolean":
            await query.edit_message_text(
                question,
                reply_markup=dynamic.build_boolean_field(field, lang, idx),
            )
            return

        elif field_type in ("multiselect",):
            selected: set = context.user_data.get(f"_ms_{idx}", set())
            await query.edit_message_text(
                question,
                reply_markup=dynamic.build_multiselect_field(field, lang, idx, selected),
            )
            return

        elif field_type in ("text", "number"):
            # Text / number fields: send a plain message and wait for MessageHandler
            # Store pending field so the text handler can pick it up
            context.user_data["_pending_text_field_idx"] = idx
            required_hint = "" if field.get("required", True) else f"\n{t('field_skip', lang)}"
            await query.edit_message_text(question + required_hint)
            return

        else:
            # Unknown type — skip
            logger.warning("Unknown field type %r at idx %d — skipping", field_type, idx)
            idx += 1

    # All custom fields done → submit
    from handlers import confirm
    await confirm.submit(query, context)


# ---------------------------------------------------------------------------
# Main callback handler
# ---------------------------------------------------------------------------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang: str = context.user_data.get("lang", "en")
    data: str = query.data
    schema = _schema(context)

    # ── Damage level (system field) ─────────────────────────────────────────
    if data.startswith("dmg:"):
        value = data.split(":", 1)[1]
        context.user_data["damage_level"] = value
        context.user_data["infra_selected"] = set()

        infra_question = dynamic.system_field_question("infrastructure_type", schema, lang)
        await query.edit_message_text(
            infra_question,
            reply_markup=dynamic.build_infra_type(schema, lang, set()),
        )

    # ── Infrastructure type (system field, multiselect) ──────────────────────
    elif data.startswith("infra:"):
        value = data.split(":", 1)[1]
        selected: set = context.user_data.setdefault("infra_selected", set())

        if value == "done":
            if not selected:
                await query.answer(t("field_select_min_one", lang), show_alert=True)
                return
            # Move to first custom field (or confirm if none)
            context.user_data["custom_idx"] = 0
            context.user_data["responses"] = {}
            await _advance_custom_fields(query, context, lang, start_idx=0)

        else:
            if value in selected:
                selected.discard(value)
            else:
                selected.add(value)
            infra_question = dynamic.system_field_question("infrastructure_type", schema, lang)
            await query.edit_message_reply_markup(
                reply_markup=dynamic.build_infra_type(schema, lang, selected),
            )

    # ── Custom field — select / boolean ─────────────────────────────────────
    elif data.startswith("f:"):
        # Format: f:{idx}:{value}
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        idx = int(parts[1])
        value = parts[2]
        field = _custom_fields(context)[idx] if idx < len(_custom_fields(context)) else None
        if not field:
            return

        # Convert boolean string to Python bool
        if field.get("type") == "boolean":
            stored = value == "true"
        else:
            stored = value

        context.user_data.setdefault("responses", {})[field["id"]] = stored
        await _advance_custom_fields(query, context, lang, start_idx=idx + 1)

    # ── Custom field — multiselect toggle ───────────────────────────────────
    elif data.startswith("fm:"):
        # Format: fm:{idx}:{value}
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        idx = int(parts[1])
        value = parts[2]
        field = _custom_fields(context)[idx] if idx < len(_custom_fields(context)) else None
        if not field:
            return

        ms_key = f"_ms_{idx}"
        selected: set = context.user_data.setdefault(ms_key, set())
        if value in selected:
            selected.discard(value)
        else:
            selected.add(value)

        question = dynamic.field_question(field, lang, idx, len(_custom_fields(context)))
        await query.edit_message_reply_markup(
            reply_markup=dynamic.build_multiselect_field(field, lang, idx, selected),
        )

    # ── Custom field — multiselect done ─────────────────────────────────────
    elif data.startswith("fd:"):
        # Format: fd:{idx}
        idx = int(data.split(":", 1)[1])
        field = _custom_fields(context)[idx] if idx < len(_custom_fields(context)) else None
        if not field:
            return

        ms_key = f"_ms_{idx}"
        selected: set = context.user_data.get(ms_key, set())
        if not selected and field.get("required", True):
            await query.answer(t("field_select_min_one", lang), show_alert=True)
            return

        context.user_data.setdefault("responses", {})[field["id"]] = list(selected)
        # Clean up temporary multiselect state
        context.user_data.pop(ms_key, None)
        await _advance_custom_fields(query, context, lang, start_idx=idx + 1)

    # ── Custom field — skip optional ─────────────────────────────────────────
    elif data.startswith("fs:"):
        # Format: fs:{idx}
        idx = int(data.split(":", 1)[1])
        field = _custom_fields(context)[idx] if idx < len(_custom_fields(context)) else None
        if field and not field.get("required", True):
            # Clean up any multiselect state
            context.user_data.pop(f"_ms_{idx}", None)
            await _advance_custom_fields(query, context, lang, start_idx=idx + 1)
        else:
            # Can't skip required field
            await query.answer(t("field_required", lang), show_alert=True)

    else:
        logger.warning("Unhandled callback_data: %r", data)
