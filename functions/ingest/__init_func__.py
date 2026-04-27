"""
Azure Functions HTTP trigger — POST /api/v1/reports
Accepts multipart/form-data with report fields + optional photo.
"""

import collections
import hashlib
import hmac
import json
import os
import time
import threading
import azure.functions as func

from ingest.schema import DamageReportSubmission
from ingest.pipeline import process_report


_UNAUTHORIZED = func.HttpResponse(
    '{"error":"unauthorized"}', status_code=401, mimetype="application/json",
    headers={"WWW-Authenticate": 'ApiKey realm="crisis-ingest"'},
)


def _check_ingest_key(req: func.HttpRequest) -> func.HttpResponse | None:
    """
    Validate X-API-Key against INGEST_API_KEY env var.
    ADMIN_API_KEY is also accepted as a super-key.
    Returns a 401 response if invalid; None if authorised.
    When INGEST_API_KEY is not set the check is skipped (open / dev mode).
    """
    ingest_key = os.environ.get("INGEST_API_KEY", "")
    admin_key  = os.environ.get("ADMIN_API_KEY", "")
    if not ingest_key and not admin_key:
        return None  # not configured — permit all (development)
    provided = req.headers.get("X-API-Key", "") or req.headers.get("X-Admin-Key", "")
    if not provided:
        return _UNAUTHORIZED
    if ingest_key and hmac.compare_digest(provided, ingest_key):
        return None
    if admin_key and hmac.compare_digest(provided, admin_key):
        return None
    return _UNAUTHORIZED


# ---------------------------------------------------------------------------
# In-process rate limiter
# Keyed on a truncated SHA-256 of the raw submitter ID.  Counts submissions
# within a sliding window; excess requests get a 429.  The dict is shared
# across concurrent invocations on the same worker instance and is protected
# by a lock.  Because Functions workers can be recycled the counter resets
# on cold start — this is intentional and an acceptable trade-off.
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_rate_windows: dict[str, collections.deque] = {}   # hash → deque of timestamps


def _is_rate_limited(raw_id: str) -> bool:
    """Return True if the submitter has exceeded the per-hour quota."""
    max_per_hour = int(os.environ.get("MAX_REPORTS_PER_USER_PER_HOUR", "20"))
    window_secs = 3600

    key = "rl_" + hashlib.sha256(raw_id.encode()).hexdigest()[:20]
    now = time.monotonic()
    cutoff = now - window_secs

    with _rate_lock:
        dq = _rate_windows.setdefault(key, collections.deque())
        # Evict timestamps outside the sliding window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= max_per_hour:
            return True
        dq.append(now)
        return False


# ---------------------------------------------------------------------------
# HTTP trigger
# ---------------------------------------------------------------------------

def main(req: func.HttpRequest) -> func.HttpResponse:
    # ── API key auth ─────────────────────────────────────────────────────────
    if (err := _check_ingest_key(req)):
        return err

    # Raw submitter identifier — hashed inside rate limiter and pipeline; never stored raw
    raw_submitter_id = req.headers.get("X-Submitter-Id", req.headers.get("X-Forwarded-For", "anon"))

    # ── Rate limiting ────────────────────────────────────────────────────────
    if _is_rate_limited(raw_submitter_id):
        return func.HttpResponse(
            json.dumps({"error": "rate_limit_exceeded", "detail": "Too many reports — please wait before submitting again."}),
            status_code=429,
            mimetype="application/json",
            headers={"Retry-After": "3600"},
        )

    # ── Parse multipart form data ────────────────────────────────────────────
    try:
        form = req.form
        photo_bytes = req.files.get("photo", None)
        if photo_bytes:
            photo_bytes = photo_bytes.read()

        # requires_debris_clearing — optional in new schema (lives in responses)
        _rdc_raw = form.get("requires_debris_clearing")
        _rdc = _rdc_raw.lower() in ("true", "1", "yes") if _rdc_raw else None

        submission = DamageReportSubmission(
            damage_level=form["damage_level"],
            infrastructure_types=json.loads(form["infrastructure_types"]),
            crisis_event_id=form["crisis_event_id"],
            channel=form["channel"],
            # Legacy fields — present in old bot/PWA builds; absent in new schema-aware builds
            crisis_nature=form.get("crisis_nature") or None,
            requires_debris_clearing=_rdc,
            # New schema fields — present in schema-aware builds
            schema_version=int(form["schema_version"]) if form.get("schema_version") else None,
            responses=json.loads(form["responses"]) if form.get("responses") else None,
            # Location
            gps_lat=float(form["gps_lat"]) if form.get("gps_lat") else None,
            gps_lon=float(form["gps_lon"]) if form.get("gps_lon") else None,
            what3words_address=form.get("what3words_address"),
            location_description=form.get("location_description"),
            # Extras
            description=form.get("description"),
            infrastructure_name=form.get("infrastructure_name"),
            other_infra_description=form.get("other_infra_description"),
            # Deprecated — kept for very old clients that still send modular_fields
            modular_fields=json.loads(form["modular_fields"]) if form.get("modular_fields") else None,
        )
    except (KeyError, ValueError) as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        result = process_report(submission, photo_bytes, raw_submitter_id)
    except ValueError as exc:
        # Validation errors from the pipeline (e.g. photo too large)
        return func.HttpResponse(
            json.dumps({"error": "validation_failed", "detail": str(exc)}),
            status_code=422,
            mimetype="application/json",
        )
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": "processing_failed", "detail": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(result),
        status_code=201,
        mimetype="application/json",
    )
