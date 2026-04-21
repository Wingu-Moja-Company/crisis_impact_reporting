import json
import os
import urllib.request

from telegram import CallbackQuery
from telegram.ext import ContextTypes

from i18n.strings import t


def _api_base() -> str:
    """Read at call time so env var changes after import are picked up."""
    return os.environ.get("API_BASE_URL", "http://localhost:7071/api")


async def submit(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    ud = context.user_data

    await query.edit_message_text("Submitting report…")

    # Download photo bytes from Telegram
    photo_bytes = None
    if file_id := ud.get("photo_file_id"):
        file = await context.bot.get_file(file_id)
        photo_bytes = await file.download_as_bytearray()

    crisis_event_id = os.environ.get("CRISIS_EVENT_ID", "unknown")

    payload = {
        "damage_level":            ud["damage_level"],
        "infrastructure_types":    json.dumps(list(ud.get("infra_selected", []))),
        "crisis_nature":           ud["crisis_nature"],
        "requires_debris_clearing": str(ud.get("requires_debris_clearing", False)).lower(),
        "crisis_event_id":         crisis_event_id,
        "channel":                 "telegram",
    }
    if lat := ud.get("gps_lat"):
        payload["gps_lat"] = str(lat)
        payload["gps_lon"] = str(ud["gps_lon"])
    if w3w := ud.get("what3words"):
        payload["what3words_address"] = w3w
    if desc := ud.get("location_description"):
        payload["location_description"] = desc

    try:
        result = _post_report(payload, photo_bytes, str(query.from_user.id))
    except Exception as exc:
        await query.edit_message_text(t("error_generic", lang))
        return  # don't re-raise — keeps the function returning 200 to Telegram

    report_id = result.get("report_id", "unknown")
    map_url = result.get("map_url", "")
    msg = t("confirm", lang, report_id=report_id, map_url=map_url) if map_url else t("confirm_no_url", lang, report_id=report_id)
    await query.edit_message_text(msg)

    # Notify of any badges earned (returned separately by the API in prod)
    for badge in result.get("badges_awarded", []):
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=t("badge_awarded", lang, badge_name=badge),
        )

    context.user_data.clear()


def _post_report(fields: dict, photo_bytes: bytes | None, submitter_id: str) -> dict:
    import io
    import email.mime.multipart

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

    req = urllib.request.Request(
        f"{_api_base()}/v1/reports",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Submitter-Id": submitter_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
