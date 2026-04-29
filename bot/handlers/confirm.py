import json
import logging
import os
import urllib.request
import urllib.error

from telegram import CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from i18n.strings import t

logger = logging.getLogger(__name__)


def _api_base() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:7071/api")


async def submit(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    ud = context.user_data

    await query.edit_message_text("Submitting report…")

    # ── Download photo bytes from Telegram ───────────────────────────────────
    photo_bytes = None
    if file_id := ud.get("photo_file_id"):
        try:
            file = await context.bot.get_file(file_id)
            photo_bytes = await file.download_as_bytearray()
        except Exception as exc:
            logger.warning("Photo download failed (non-fatal): %s", exc)

    # ── Validate mandatory system fields ─────────────────────────────────────
    damage_level = ud.get("damage_level")
    infra_selected = list(ud.get("infra_selected", set()))

    if not damage_level:
        logger.error("damage_level missing from user_data. ud keys: %s", list(ud.keys()))
        await query.edit_message_text("Session expired — please start again with /start.")
        return

    if not infra_selected:
        logger.error("infra_selected empty. ud keys: %s", list(ud.keys()))
        await query.edit_message_text("Session expired — please start again with /start.")
        return

    # ── Build payload ────────────────────────────────────────────────────────
    # Use the event ID pinned at /start (from deep link or env var fallback)
    crisis_event_id = ud.get("crisis_event_id") or os.environ.get("CRISIS_EVENT_ID", "ke-flood-dev")
    schema = ud.get("schema", {})
    schema_version = schema.get("version")

    # responses holds all custom field answers collected during the form flow
    responses = ud.get("responses", {})

    payload = {
        "damage_level":         damage_level,
        "infrastructure_types": json.dumps(infra_selected),
        "crisis_event_id":      crisis_event_id,
        "channel":              "telegram",
        # New dynamic schema fields
        "responses":            json.dumps(responses),
        **({"schema_version": str(schema_version)} if schema_version else {}),
    }

    # GPS location
    if lat := ud.get("gps_lat"):
        payload["gps_lat"] = str(lat)
        payload["gps_lon"] = str(ud.get("gps_lon", ""))
    if w3w := ud.get("what3words"):
        payload["what3words_address"] = w3w
    if desc := ud.get("location_description"):
        payload["location_description"] = desc

    logger.info(
        "Submitting to %s — damage=%s infra=%s schema_v=%s responses_keys=%s",
        _api_base(), damage_level, infra_selected, schema_version, list(responses.keys()),
    )

    # ── POST to pipeline API ─────────────────────────────────────────────────
    try:
        result = _post_report(payload, photo_bytes, str(query.from_user.id))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:200]
        logger.error("API HTTP %s: %s", exc.code, body)
        await query.edit_message_text(
            f"⚠️ Submission failed (HTTP {exc.code}). Please try /start again.\n\nDetail: {body}"
        )
        return
    except Exception as exc:
        logger.error("API call failed: %s", exc, exc_info=True)
        await query.edit_message_text(
            f"⚠️ Submission failed: {exc}\n\nPlease try /start again."
        )
        return

    # ── Send success messages ─────────────────────────────────────────────────
    report_id = result.get("report_id", "unknown")
    map_url = result.get("map_url", "")
    if map_url:
        msg = t("confirm", lang, report_id=report_id, map_url=map_url)
    else:
        msg = t("confirm_no_url", lang, report_id=report_id)
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    for badge in result.get("badges_awarded", []):
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=t("badge_awarded", lang, badge_name=badge),
        )

    # ── Preserve session-level data across submissions ────────────────────────
    # Clearing user_data resets the form, but we keep the event binding and
    # schema so a follow-up /start re-enters the same crisis event without
    # requiring another deep-link.
    _crisis_event_id = ud.get("crisis_event_id")
    _schema = ud.get("schema")
    _lang = lang

    context.user_data.clear()

    if _crisis_event_id:
        context.user_data["crisis_event_id"] = _crisis_event_id
    if _schema:
        context.user_data["schema"] = _schema
    context.user_data["lang"] = _lang

    # Invite the user to file another report for the same event
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "To submit another report for this event, send /start."
        ),
    )


def _post_report(fields: dict, photo_bytes: bytes | None, submitter_id: str) -> dict:
    boundary = "----CrisisBot"
    body_parts = []

    for key, value in fields.items():
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            f"{value}\r\n"
        )

    if photo_bytes:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        )

    body = "".join(body_parts).encode()
    if photo_bytes:
        body = body + bytes(photo_bytes) + f"\r\n--{boundary}--\r\n".encode()
    else:
        body += f"--{boundary}--\r\n".encode()

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Submitter-Id": submitter_id,
    }
    if api_key := os.environ.get("INGEST_API_KEY"):
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(
        f"{_api_base()}/v1/reports",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
