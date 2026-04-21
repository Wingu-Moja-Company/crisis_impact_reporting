"""
15-step ingestion pipeline executed for every incoming damage report.
Steps run sequentially; any unhandled exception propagates to the Azure
Functions HTTP trigger which returns a 500 to the caller.
"""

import hashlib
import io
import json
import os
import time
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
  "summary": "One sentence max 20 words for field responders"
}

Damage level guide:
- minimal: Structurally sound, cosmetic damage only (cracks, water marks), building still functional
- partial: Repairable structural damage, some elements compromised, proceed with caution
- complete: Structurally unsafe or destroyed, must not be entered
- unclear: Cannot determine damage level from this photo

Set rejection_reason to "no_structure", "too_dark", or "unrelated" if the photo is not usable.
Set infrastructure_visible to false if no structure is clearly visible."""


def _ai_vision_score(photo_bytes: bytes) -> dict:
    """
    Use Azure OpenAI GPT-4o (via Azure AI Foundry) to assess structural damage
    from a submitted photo. Returns a dict with confidence, suggested_level,
    plain-English summary, and debris flag.
    Falls back gracefully if the service is unavailable.
    """
    import base64

    endpoint = os.environ.get("AOAI_ENDPOINT", "").rstrip("/")
    key      = os.environ.get("AOAI_KEY", "")
    deploy   = os.environ.get("AOAI_DEPLOYMENT", "gpt-4o")

    _null = {"confidence": 0.0, "suggested_level": None, "summary": None,
             "debris_confirmed": None, "infrastructure_visible": True, "rejection_reason": None}

    if not endpoint or not key:
        return _null

    b64 = base64.b64encode(photo_bytes).decode()
    payload = json.dumps({
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _DAMAGE_PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "low",   # low detail = faster + cheaper, sufficient for damage grading
                }},
            ],
        }],
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
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
    except Exception:
        return _null

    level = content.get("damage_level", "unclear")
    return {
        "confidence":           float(content.get("confidence", 0.0)),
        "suggested_level":      level if level in ("minimal", "partial", "complete") else None,
        "summary":              content.get("summary"),
        "debris_confirmed":     content.get("debris_visible"),
        "infrastructure_visible": content.get("infrastructure_visible", True),
        "rejection_reason":     content.get("rejection_reason"),
    }


def _submitter_hash(raw_id: str) -> str:
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

    # Step 7 — GPT-4o vision damage assessment
    _ai_null = {"confidence": 0.0, "suggested_level": None, "summary": None,
                "debris_confirmed": None, "infrastructure_visible": True, "rejection_reason": None}
    ai_result = _ai_null
    if photo_bytes:
        ai_result = _ai_vision_score(photo_bytes)

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
    if building_id:
        _upsert_building(building_id, report_id, submission, submitted_at, sub_hash)

    # Step 12 — write full report document
    report_doc = {
        "id": report_id,
        "crisis_event_id": submission.crisis_event_id,
        "building_id": building_id,
        "submitted_at": submitted_at,
        "channel": submission.channel,
        "damage": {
            "level": submission.damage_level.value,
            "infrastructure_types": [t.value for t in submission.infrastructure_types],
            "infrastructure_name": submission.infrastructure_name,
            "crisis_nature": submission.crisis_nature.value,
            "requires_debris_clearing": submission.requires_debris_clearing,
            "description_original": desc_original or None,
            "description_original_lang": desc_lang if desc_original else None,
            "description_en": desc_en if desc_original else None,
            "ai_vision_confidence":      ai_result["confidence"],
            "ai_vision_suggested_level": ai_result["suggested_level"],
            "ai_vision_summary":         ai_result["summary"],
            "ai_vision_debris_confirmed": ai_result["debris_confirmed"],
            "ai_vision_rejection_reason": ai_result["rejection_reason"],
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
        "modular_fields": submission.modular_fields or {},
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
    import urllib.request
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


def _upsert_building(
    building_id: str,
    report_id: str,
    submission: DamageReportSubmission,
    submitted_at: str,
    sub_hash: str,
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
    })

    container = _cosmos_container("buildings")
    try:
        existing = container.read_item(f"building_{building_id}", partition_key=submission.crisis_event_id)
        is_newer = submitted_at > existing.get("last_updated", "")
        # Verified reporter submissions break ties
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
            "requires_debris_clearing": submission.requires_debris_clearing,
            "submitter_tier": tier,
        })
