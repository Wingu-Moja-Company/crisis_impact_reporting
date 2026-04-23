"""
Handles all InlineKeyboard callback queries through the damage form flow.

State machine via context.user_data["step"]:
  dmg → infra → crisis → debris → electricity → health → pressing_needs → confirm
"""

from telegram import Update
from telegram.ext import ContextTypes

from i18n.strings import t
from keyboards import infra_type, crisis_type, electricity_status, health_services, pressing_needs


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang = context.user_data.get("lang", "en")
    data: str = query.data

    if data.startswith("dmg:"):
        context.user_data["damage_level"] = data.split(":")[1]
        context.user_data["infra_selected"] = set()
        await query.edit_message_text(
            t("select_infra_type", lang),
            reply_markup=infra_type.build(lang),
        )

    elif data.startswith("infra:"):
        value = data.split(":")[1]
        selected: set[str] = context.user_data.setdefault("infra_selected", set())

        if value == "done":
            if not selected:
                await query.answer("Select at least one type.", show_alert=True)
                return
            await query.edit_message_text(
                t("select_crisis_nature", lang),
                reply_markup=crisis_type.build(lang),
            )
        else:
            if value in selected:
                selected.discard(value)
            else:
                selected.add(value)
            await query.edit_message_reply_markup(
                reply_markup=infra_type.build(lang, selected),
            )

    elif data.startswith("crisis:"):
        context.user_data["crisis_nature"] = data.split(":")[1]
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(t("yes", lang), callback_data="debris:yes"),
            InlineKeyboardButton(t("no",  lang), callback_data="debris:no"),
        ]])
        await query.edit_message_text(t("debris_question", lang), reply_markup=kb)

    elif data.startswith("debris:"):
        context.user_data["requires_debris_clearing"] = data.split(":")[1] == "yes"
        await query.edit_message_text(
            t("electricity_question", lang),
            reply_markup=electricity_status.build(lang),
        )

    elif data.startswith("elec:"):
        context.user_data["electricity_status"] = data.split(":")[1]
        await query.edit_message_text(
            t("health_question", lang),
            reply_markup=health_services.build(lang),
        )

    elif data.startswith("health:"):
        context.user_data["health_services"] = data.split(":")[1]
        context.user_data["needs_selected"] = set()
        await query.edit_message_text(
            t("pressing_needs_question", lang),
            reply_markup=pressing_needs.build(lang),
        )

    elif data.startswith("needs:"):
        value = data.split(":")[1]
        selected: set[str] = context.user_data.setdefault("needs_selected", set())

        if value == "done":
            if not selected:
                await query.answer("Select at least one need.", show_alert=True)
                return
            from handlers import confirm
            await confirm.submit(query, context)
        else:
            if value in selected:
                selected.discard(value)
            else:
                selected.add(value)
            await query.edit_message_reply_markup(
                reply_markup=pressing_needs.build(lang, selected),
            )
