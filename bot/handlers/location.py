import json
import logging
import os
import re
import urllib.parse
import urllib.request

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from i18n.strings import t
from keyboards import dynamic
from schema import fallback_schema

logger = logging.getLogger(__name__)

# Matches what3words patterns with or without the /// prefix:
#   filled.count.soap  or  ///filled.count.soap
_W3W_RE = re.compile(r"^/{0,3}\s*([a-z]+\.[a-z]+\.[a-z]+)\s*$", re.IGNORECASE)

# Strip proximity words that confuse geocoders ("Near Westlands" → "Westlands")
_PROXIMITY_RE = re.compile(
    r"^\s*(near|by|next to|opposite|behind|in front of|outside|beside|around|along|at)\s+",
    re.IGNORECASE,
)

# Country code bias derived from crisis event ID prefix (e.g. "ke-flood-dev" → "ke")
def _country_code() -> str:
    event_id = os.environ.get("CRISIS_EVENT_ID", "")
    prefix = event_id.split("-")[0].lower()
    return prefix if len(prefix) == 2 else "ke"


def _geocode_nominatim(query: str) -> tuple[float | None, float | None, str | None]:
    """
    Geocode a plain-text location using OpenStreetMap Nominatim.
    Returns (lat, lon, display_name) or (None, None, None) on failure.
    No API key required; rate-limited to ~1 req/s by Nominatim ToS.
    """
    country = _country_code()
    # Strip proximity words so "Near Westlands Market" → "Westlands Market"
    clean_query = _PROXIMITY_RE.sub("", query).strip()
    params = urllib.parse.urlencode({
        "q": clean_query,
        "format": "json",
        "limit": 1,
        "countrycodes": country,
        "addressdetails": 0,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CrisisImpactReporter/1.0 (humanitarian)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            results = json.loads(resp.read())
        if results:
            r = results[0]
            # Shorten the display name to the first two comma-separated parts
            name_parts = r.get("display_name", query).split(",")
            short_name = ", ".join(p.strip() for p in name_parts[:2])
            return float(r["lat"]), float(r["lon"]), short_name
    except Exception as exc:
        logger.warning("Nominatim geocoding failed for %r: %s", query, exc)
    return None, None, None


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    geocode_msg = None  # feedback to show before damage question

    if update.message.location:
        # Native GPS share — most accurate, no lookup needed
        context.user_data["gps_lat"] = update.message.location.latitude
        context.user_data["gps_lon"] = update.message.location.longitude

    elif update.message.text:
        text = update.message.text.strip()
        w3w_match = _W3W_RE.match(text)

        if w3w_match:
            # what3words — resolve via W3W API if key is available
            words = w3w_match.group(1).lower()
            context.user_data["what3words"] = words
            lat, lon = _resolve_w3w(words)
            if lat and lon:
                context.user_data["gps_lat"] = lat
                context.user_data["gps_lon"] = lon

        else:
            # Plain text — try Nominatim geocoding
            context.user_data["location_description"] = text
            lat, lon, place = _geocode_nominatim(text)
            if lat is not None:
                context.user_data["gps_lat"] = lat
                context.user_data["gps_lon"] = lon
                geocode_msg = t("location_found", lang, place=place)
            else:
                geocode_msg = t("location_not_found", lang, query=text[:40])

    # Dismiss the GPS reply keyboard
    await update.message.reply_text(
        geocode_msg or t("select_damage_level", lang),
        reply_markup=ReplyKeyboardRemove(),
    )

    # Show damage level selector (schema-driven; falls back to cached schema or hardcoded)
    schema = context.user_data.get("schema") or fallback_schema()
    damage_question = dynamic.system_field_question("damage_level", schema, lang)
    await update.message.reply_text(
        damage_question,
        reply_markup=dynamic.build_damage_level(schema, lang),
    )


def _resolve_w3w(words: str) -> tuple[float | None, float | None]:
    key = os.environ.get("W3W_API_KEY", "")
    if not key or key == "placeholder":
        return None, None
    url = f"https://api.what3words.com/v3/convert-to-coordinates?words={words}&key={key}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        coords = data.get("coordinates", {})
        return coords.get("lat"), coords.get("lng")
    except Exception:
        return None, None
