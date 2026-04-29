"""
15-step ingestion pipeline executed for every incoming damage report.
Steps run sequentially; any unhandled exception propagates to the Azure
Functions HTTP trigger which returns a 500 to the caller.
"""

import base64
import hashlib
import hmac as _hmac
import io
import json
import logging
import os
import time
import urllib.request
import uuid
from datetime import datetime, timezone

from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, ContentSettings
from PIL import Image

from buildings.footprint_query import resolve_building_id
from ingest.dedup import is_duplicate
from ingest.schema import DamageReportSubmission
from ingest.translate import detect_and_translate


# ---------------------------------------------------------------------------
# Cosmos DB helpers
# ---------------------------------------------------------------------------

def _cosmos_container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])
    return db.get_container_client(name)


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

_MAX_PHOTO_BYTES  = 10 * 1024 * 1024   # 10 MB hard limit
_MAX_PHOTO_PIXELS = 4096                # max width or height in pixels


def _store_photo(photo_bytes: bytes, crisis_event_id: str, report_id: str) -> str:
    """Validate, strip EXIF, resize if needed, store in Blob Storage. Returns blob path."""
    # ── Size guard (before opening with PIL to avoid zip-bomb risk) ──────────
    if len(photo_bytes) > _MAX_PHOTO_BYTES:
        raise ValueError(
            f"Photo exceeds maximum allowed size "
            f"({len(photo_bytes) // 1024} KB > {_MAX_PHOTO_BYTES // 1024} KB)"
        )

    img = Image.open(io.BytesIO(photo_bytes))

    # ── Dimension guard ──────────────────────────────────────────────────────
    w, h = img.size
    if w > _MAX_PHOTO_PIXELS or h > _MAX_PHOTO_PIXELS:
        img.thumbnail((_MAX_PHOTO_PIXELS, _MAX_PHOTO_PIXELS), Image.LANCZOS)

    # PIL copy (or thumbnail) drops all EXIF metadata
    clean = img.copy()

    buf = io.BytesIO()
    clean.save(buf, format="JPEG")
    buf.seek(0)

    blob_path = f"{crisis_event_id}/{report_id}.jpg"
    conn_str = os.environ["STORAGE_CONNECTION_STRING"]
    blob_client = BlobServiceClient.from_connection_string(conn_str)
    blob_client.get_blob_client("report-photos", blob_path).upload_blob(
        buf, overwrite=True,
        content_settings=ContentSettings(content_type="image/jpeg"),
    )
    return blob_path


def _extract_exif_gps(photo_bytes: bytes) -> tuple[float | None, float | None]:
    """Return (lat, lon) from EXIF GPS tags, or (None, None)."""
    try:
        img = Image.open(io.BytesIO(photo_bytes))
        exif = img._getexif() or {}
        gps_info = exif.get(34853)  # GPSInfo tag
        if not gps_info:
            return None, None

        def dms_to_dd(dms, ref):
            d, m, s = [float(x.numerator) / float(x.denominator) for x in dms]
            dd = d + m / 60 + s / 3600
            return -dd if ref in ("S", "W") else dd

        lat = dms_to_dd(gps_info[2], gps_info[1])
        lon = dms_to_dd(gps_info[4], gps_info[3])
        return lat, lon
    except Exception:
        return None, None


_DAMAGE_PROMPT = """You are a humanitarian field damage assessor reviewing a photo submitted during a crisis response.

Assess the structural damage visible and respond with JSON only — no explanation outside the JSON:

{
  "damage_level": "minimal|partial|complete|unclear",
  "confidence": 0.0,
  "infrastructure_visible": true,
  "debris_visible": false,
  "rejection_reason": null,
  "summary": "One sentence max 20 words for field responders",
  "access_status": "clear|limited|blocked|unknown",
  "hazard_indicators": [],
  "intervention_priority": "low|medium|high|critical"
}

Damage level guide:
- minimal: Structurally sound, cosmetic damage only (cracks, water marks), building still functional
- partial: Repairable structural damage, some elements compromised, proceed with caution
- complete: Structurally unsafe or destroyed, must not be entered
- unclear: Cannot determine damage level from this photo

access_status guide (can responders safely reach and enter the site?):
- clear: No visible obstructions, site appears accessible
- limited: Partial obstruction (debris, damage) — access possible with caution
- blocked: Access route visibly obstructed or site is unsafe to enter
- unknown: Cannot determine from this photo

hazard_indicators: array of zero or more visible safety hazards from this list only:
  "structural_collapse_risk", "fire_damage", "flood_damage",
  "debris_blocking_access", "exposed_hazardous_materials", "road_damage"

intervention_priority (urgency for field response):
- low: Minimal or no damage, monitoring only
- medium: Repairable damage, address within days
- high: Significant damage or hazards, respond within 24–48 hours
- critical: Severe/complete damage or immediate safety risk, respond immediately

Set rejection_reason to "no_structure", "too_dark", or "unrelated" if the photo is not usable.
Set infrastructure_visible to false if no structure is clearly visible."""


def _ai_vision_score(photo_bytes: bytes, crisis_nature: str | None = None) -> dict:
    """
    Use Azure OpenAI GPT-4o (via Azure AI Foundry) to assess structural damage
    from a submitted photo. Returns a dict with confidence, suggested_level,
    plain-English summary, and debris flag.
    Falls back gracefully if the service is unavailable.
    """
    endpoint = os.environ.get("AOAI_ENDPOINT", "").rstrip("/")
    key      = os.environ.get("AOAI_KEY", "")
    deploy   = os.environ.get("AOAI_DEPLOYMENT", "gpt-5.4-mini")

    _null = {"confidence": 0.0, "suggested_level": None, "summary": None,
             "debris_confirmed": None, "infrastructure_visible": True, "rejection_reason": None,
             "access_status": None, "hazard_indicators": [], "intervention_priority": None}

    if not endpoint or not key:
        logging.warning("AI vision skipped: AOAI_ENDPOINT or AOAI_KEY not configured")
        return _null

    logging.info("AI vision: calling %s/openai/deployments/%s, photo=%d bytes, crisis=%s",
                 endpoint, deploy, len(photo_bytes), crisis_nature or "unknown")
    b64 = base64.b64encode(photo_bytes).decode()
    # Prepend crisis context so the model calibrates its assessment correctly
    prompt_text = _DAMAGE_PROMPT
    if crisis_nature:
        prompt_text = (
            f"Context: this photo was submitted during a {crisis_nature} crisis response.\n\n"
            + prompt_text
        )
    payload = json.dumps({
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "low",   # low detail = faster + cheaper, sufficient for damage grading
                }},
            ],
        }],
        "max_completion_tokens": 400,
        "response_format": {"type": "json_object"},
        "temperature": 0,   # deterministic — same image → same score every time
        "seed": 42,
    }).encode()

    url = f"{endpoint}/openai/deployments/{deploy}/chat/completions?api-version=2024-10-21"
    req = urllib.request.Request(
        url, data=payload,
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
        content = json.loads(result["choices"][0]["message"]["content"])
    except Exception as exc:
        logging.warning("AI vision scoring failed (non-fatal): %s: %s", type(exc).__name__, exc)
        return _null

    level = content.get("damage_level", "unclear")
    _valid_access   = {"clear", "limited", "blocked", "unknown"}
    _valid_priority = {"low", "medium", "high", "critical"}
    _valid_hazards  = {
        "structural_collapse_risk", "fire_damage", "flood_damage",
        "debris_blocking_access", "exposed_hazardous_materials", "road_damage",
    }
    raw_hazards = content.get("hazard_indicators") or []
    return {
        "confidence":             float(content.get("confidence", 0.0)),
        "suggested_level":        level if level in ("minimal", "partial", "complete") else None,
        "summary":                content.get("summary"),
        "debris_confirmed":       content.get("debris_visible"),
        "infrastructure_visible": content.get("infrastructure_visible", True),
        "rejection_reason":       content.get("rejection_reason"),
        "access_status":          content.get("access_status") if content.get("access_status") in _valid_access else None,
        "hazard_indicators":      [h for h in raw_hazards if h in _valid_hazards],
        "intervention_priority":  content.get("intervention_priority") if content.get("intervention_priority") in _valid_priority else None,
    }


def _submitter_hash(raw_id: str) -> str:
    """
    One-way pseudonymous identifier for the submitter.
    Uses HMAC-SHA256 keyed on SUBMITTER_SALT env var so the mapping cannot be
    brute-forced even for sequential inputs (e.g. Telegram user IDs).
    Falls back to plain SHA-256 in dev when no salt is configured.
    """
    salt = os.environ.get("SUBMITTER_SALT", "")
    if salt:
        digest = _hmac.new(salt.encode(), raw_id.encode(), "sha256").hexdigest()
        return "hmac_" + digest[:16]
    # Dev / unsalted fallback — clearly labelled so it's easy to spot in data
    return "sha256_" + hashlib.sha256(raw_id.encode()).hexdigest()[:16]


def _award_badges(submitter_hash: str, crisis_event_id: str) -> None:
    """Delegate badge evaluation to the engagement module (imported lazily)."""
    from engagement.badges import evaluate_badges
    evaluate_badges(submitter_hash, crisis_event_id)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_report(
    submission: DamageReportSubmission,
    photo_bytes: bytes | None,
    raw_submitter_id: str,
) -> dict:
    """
    Execute all 15 ingestion steps and return the persisted report document.
    """
    started = time.monotonic()
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    submitted_at = datetime.now(timezone.utc).isoformat()
    sub_hash = _submitter_hash(raw_submitter_id)

    # Step 1 — rate limiting is enforced by Azure API Management before this runs.

    # Step 2 — schema validation is enforced by Pydantic on the caller side.

    # Step 3 — photo storage + Step 4 — EXIF extraction and strip
    blob_path = None
    exif_lat, exif_lon = None, None
    if photo_bytes:
        # Early size check (before PIL touches the bytes) prevents decompression bombs
        if len(photo_bytes) > _MAX_PHOTO_BYTES:
            raise ValueError(
                f"Photo exceeds maximum allowed size "
                f"({len(photo_bytes) // 1024} KB > {_MAX_PHOTO_BYTES // 1024} KB)"
            )
        exif_lat, exif_lon = _extract_exif_gps(photo_bytes)
        blob_path = _store_photo(photo_bytes, submission.crisis_event_id, report_id)

    # Step 5 — resolve GPS to building_id via PostGIS
    lat = submission.gps_lat or exif_lat
    lon = submission.gps_lon or exif_lon
    building_id = None
    if lat is not None and lon is not None:
        building_id = resolve_building_id(lon, lat)

    # Step 6 — what3words resolution (only if no GPS building match yet)
    if building_id is None and submission.what3words_address:
        lat, lon = _resolve_w3w(submission.what3words_address)
        if lat and lon:
            building_id = resolve_building_id(lon, lat)

    # Step 7 — GPT-5.4-mini vision damage assessment
    _ai_null = {"confidence": 0.0, "suggested_level": None, "summary": None,
                "debris_confirmed": None, "infrastructure_visible": True, "rejection_reason": None,
                "access_status": None, "hazard_indicators": [], "intervention_priority": None}
    ai_result = _ai_null
    if photo_bytes:
        crisis_nature_hint = submission.get_crisis_nature()
        ai_result = _ai_vision_score(photo_bytes, crisis_nature=crisis_nature_hint)

    # Step 8 — translate description to English
    desc_original = submission.description or ""
    desc_lang = "en"
    desc_en = desc_original
    if desc_original:
        desc_lang, desc_en = detect_and_translate(desc_original)

    # Step 9 — deduplication check
    submitted_dt = datetime.fromisoformat(submitted_at)
    dup = is_duplicate(building_id or "unknown", submitted_dt) if building_id else False

    # Steps 10 + 11 — building state upsert and version history
    requires_debris = submission.get_requires_debris_clearing()
    if building_id:
        _upsert_building(building_id, report_id, submission, submitted_at, sub_hash,
                         lat, lon, bool(photo_bytes), requires_debris)

    # Step 12 — write full report document
    crisis_nature = submission.get_crisis_nature()
    requires_debris = submission.get_requires_debris_clearing()

    # Data retention: TTL in seconds. Default 2 years; override via REPORT_TTL_SECONDS env var.
    # The Cosmos DB container must have TTL enabled (defaultTtl: -1) for this to take effect.
    _DEFAULT_TTL = 2 * 365 * 24 * 3600  # 63 072 000 s ≈ 2 years
    report_ttl = int(os.environ.get("REPORT_TTL_SECONDS", _DEFAULT_TTL))

    report_doc = {
        "id": report_id,
        "crisis_event_id": submission.crisis_event_id,
        "ttl": report_ttl,
        "building_id": building_id,
        "submitted_at": submitted_at,
        "channel": submission.channel,
        "schema_version": submission.schema_version,
        "damage": {
            "level": submission.damage_level.value,
            "infrastructure_types": [
                t if isinstance(t, str) else t.value
                for t in submission.infrastructure_types
            ],
            "infrastructure_name": submission.infrastructure_name,
            # Kept for backward compat with dashboard/export code reading damage.*
            "crisis_nature": crisis_nature,
            "requires_debris_clearing": requires_debris,
            "description_original": desc_original or None,
            "description_original_lang": desc_lang if desc_original else None,
            "description_en": desc_en if desc_original else None,
            "ai_vision_confidence":        ai_result["confidence"],
            "ai_vision_suggested_level":   ai_result["suggested_level"],
            "ai_vision_summary":           ai_result["summary"],
            "ai_vision_debris_confirmed":  ai_result["debris_confirmed"],
            "ai_vision_rejection_reason":  ai_result["rejection_reason"],
            "ai_vision_access_status":     ai_result["access_status"],
            "ai_vision_hazard_indicators": ai_result["hazard_indicators"],
            "ai_vision_intervention_priority": ai_result["intervention_priority"],
        },
        "location": {
            "type": "Point",
            "coordinates": [lon, lat] if lon is not None and lat is not None else None,
            "building_footprint_matched": building_id is not None,
            "location_description": submission.location_description,
            "what3words": submission.what3words_address,
        },
        "media": {
            "photo_blob_path": blob_path,
            "exif_stripped": photo_bytes is not None,
        },
        # responses replaces modular_fields; contains all custom field answers.
        # get_effective_responses() merges legacy top-level fields for old clients.
        "responses": submission.get_effective_responses(),
        "meta": {
            "submitter_hash": sub_hash,
            "submitter_tier": _get_submitter_tier(sub_hash),
            "is_duplicate": dup,
            "duplicate_of": None,
            "is_flagged": dup,
            "flag_reason": "duplicate_window" if dup else None,
            "processing_ms": int((time.monotonic() - started) * 1000),
        },
    }

    _cosmos_container("reports").upsert_item(report_doc)

    # Step 13 — engagement badges
    _award_badges(sub_hash, submission.crisis_event_id)

    # Step 14 — Event Grid webhook dispatch handled by Azure Functions output binding
    # (configured in function.json — not called directly here)

    # Step 15 — return response payload
    return {
        "report_id": report_id,
        "map_url": f"{os.environ.get('DASHBOARD_URL', 'https://salmon-desert-0b66f1503.7.azurestaticapps.net')}?report={report_id}",
    }


# ---------------------------------------------------------------------------
# Supporting helpers
# ---------------------------------------------------------------------------

def _resolve_w3w(address: str) -> tuple[float | None, float | None]:
    key = os.environ.get("W3W_API_KEY", "")
    if not key:
        return None, None
    # Key sent as a request header, NOT a query parameter, so it never
    # appears in server/proxy access logs or browser history.
    url = f"https://api.what3words.com/v3/convert-to-coordinates?words={address}"
    req = urllib.request.Request(url, headers={"X-Api-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        coords = data.get("coordinates", {})
        return coords.get("lat"), coords.get("lng")
    except Exception:
        return None, None


def _get_submitter_tier(sub_hash: str) -> str:
    try:
        doc = _cosmos_container("contributors").read_item(sub_hash, partition_key=sub_hash)
        return doc.get("tier", "public")
    except Exception:
        return "public"


_DAMAGE_SEVERITY = {"minimal": 0, "partial": 1, "complete": 2}

# Reports submitted within this window compete on severity rather than recency.
# Outside the window, the most recent report always wins.
_SEVERITY_BIAS_WINDOW_SECONDS = int(os.environ.get("SEVERITY_BIAS_WINDOW_SECONDS", "900"))  # 15 min default


def _upsert_building(
    building_id: str,
    report_id: str,
    submission: DamageReportSubmission,
    submitted_at: str,
    sub_hash: str,
    lat: float | None,
    lon: float | None,
    has_photo: bool,
    requires_debris_clearing: bool = False,
) -> None:
    tier = _get_submitter_tier(sub_hash)

    _cosmos_container("building_versions").upsert_item({
        "id": f"ver_{building_id}_{submitted_at}",
        "building_id": building_id,
        "crisis_event_id": submission.crisis_event_id,
        "report_id": report_id,
        "damage_level": submission.damage_level.value,
        "submitted_at": submitted_at,
        "submitter_tier": tier,
        "has_photo": has_photo,
    })

    container = _cosmos_container("buildings")
    try:
        existing = container.read_item(f"building_{building_id}", partition_key=submission.crisis_event_id)
        existing_ts = existing.get("last_updated", "")
        new_severity = _DAMAGE_SEVERITY.get(submission.damage_level.value, 0)
        old_severity = _DAMAGE_SEVERITY.get(existing.get("current_damage_level", "minimal"), 0)

        # Outside the bias window: recency wins unconditionally.
        from datetime import datetime, timezone, timedelta
        try:
            age_seconds = (
                datetime.fromisoformat(submitted_at) - datetime.fromisoformat(existing_ts)
            ).total_seconds()
        except Exception:
            age_seconds = 999999

        if age_seconds > _SEVERITY_BIAS_WINDOW_SECONDS:
            # New report is old enough to simply win on recency.
            is_newer = submitted_at > existing_ts
        else:
            # Within the window: prefer the more severe assessment.
            if new_severity > old_severity:
                is_newer = True
            elif new_severity == old_severity:
                # Same severity — prefer photo-backed, then recency, then verified tier.
                if has_photo and not existing.get("has_photo"):
                    is_newer = True
                elif submitted_at > existing_ts:
                    is_newer = True
                elif tier == "verified" and existing.get("submitter_tier") != "verified":
                    is_newer = True
                else:
                    is_newer = False
            else:
                # New is less severe — keep existing unless it's very old or unverified.
                is_newer = False

        # Verified submitter always breaks ties in their favour.
        if not is_newer and tier == "verified" and existing.get("submitter_tier") != "verified":
            is_newer = True
    except Exception:
        existing = None
        is_newer = True

    if is_newer:
        container.upsert_item({
            "id": f"building_{building_id}",
            "building_id": building_id,
            "crisis_event_id": submission.crisis_event_id,
            "current_damage_level": submission.damage_level.value,
            "current_damage_report_id": report_id,
            "report_count": (existing.get("report_count", 0) + 1) if existing else 1,
            "last_updated": submitted_at,
            "requires_debris_clearing": requires_debris_clearing,
            "submitter_tier": tier,
            "has_photo": has_photo,
            "lat": lat,
            "lon": lon,
        })
