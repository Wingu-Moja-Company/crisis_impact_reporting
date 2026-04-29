import os
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from i18n.strings import t
from schema import fetch_events, fetch_schema
from utils import detect_un_language

# Default event when no deep-link payload is provided
_DEFAULT_EVENT_ID = os.environ.get("CRISIS_EVENT_ID", "ke-flood-dev")

# Telegram deep-link payloads may only contain A-Z a-z 0-9 _ -  (max 64 chars)
_EVENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$", re.IGNORECASE)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = detect_un_language(update.effective_user.language_code)

    # ── Parse deep-link payload ───────────────────────────────────────────────
    # Telegram sends "/start <payload>" when user arrives via t.me/Bot?start=<payload>
    text = (update.message.text or "").strip()
    parts = text.split(None, 1)                    # ["/start", "payload"] or ["/start"]
    raw_payload = parts[1].strip() if len(parts) > 1 else ""

    if raw_payload and _EVENT_ID_RE.match(raw_payload):
        crisis_event_id = raw_payload
        via_deeplink = True
    else:
        # No deep-link payload — reuse a previously bound event ID if present
        # (set by confirm.py after a successful submission so repeat /start
        #  stays in the same crisis without another deep link).
        crisis_event_id = (
            context.user_data.get("crisis_event_id")
            or _DEFAULT_EVENT_ID
        )
        via_deeplink = False

    # Clear form state but keep session-level bindings until we update them
    _prev_schema = context.user_data.get("schema")
    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["crisis_event_id"] = crisis_event_id

    # ── Fetch schema ─────────────────────────────────────────────────────────
    # Re-use the cached schema if the event hasn't changed (avoids an API
    # round-trip when the user hits /start again after submitting).
    if _prev_schema and not via_deeplink and not _prev_schema.get("_fallback"):
        schema = _prev_schema
    else:
        schema = fetch_schema(crisis_event_id)
    context.user_data["schema"] = schema

    # If a deep-link payload was given but the schema fell back, the event
    # ID is probably wrong — show available events and stop.
    if via_deeplink and schema.get("_fallback"):
        events = fetch_events()
        if events:
            lines = "\n".join(
                f"  • <code>{e['id']}</code> — {e.get('name', e['id'])}"
                for e in events[:12]
            )
            await update.message.reply_text(
                f"⚠️ Crisis event <code>{crisis_event_id}</code> was not found.\n\n"
                f"<b>Available events:</b>\n{lines}\n\n"
                f"Share a link like:\n"
                f"<code>t.me/{context.bot.username}?start=event-id</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            # API unreachable — fall back silently and continue
            await update.message.reply_text(t("schema_unavailable", lang))
        return

    # Warn if schema fell back for a non-deeplink start (API offline)
    if schema.get("_fallback"):
        await update.message.reply_text(t("schema_unavailable", lang))

    # ── Welcome ───────────────────────────────────────────────────────────────
    # Show the event ID as a small subtitle when arrived via deep link,
    # so the reporter knows exactly which crisis they are filing for.
    welcome = t("welcome", lang)
    if via_deeplink:
        event_name = schema.get("crisis_event_id") or crisis_event_id
        welcome += f"\n\n<i>Reporting for: <code>{event_name}</code></i>"

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
