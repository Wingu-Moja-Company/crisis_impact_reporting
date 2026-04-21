"""
Azure Functions HTTP trigger — POST /api/v1/reports
Accepts multipart/form-data with report fields + optional photo.
"""

import collections
import hashlib
import json
import os
import time
import threading
import azure.functions as func

from ingest.schema import DamageReportSubmission
from ingest.pipeline import process_report


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

        submission = DamageReportSubmission(
            damage_level=form["damage_level"],
            infrastructure_types=json.loads(form["infrastructure_types"]),
            crisis_nature=form["crisis_nature"],
            requires_debris_clearing=form["requires_debris_clearing"].lower() == "true",
            crisis_event_id=form["crisis_event_id"],
            channel=form["channel"],
            gps_lat=float(form["gps_lat"]) if form.get("gps_lat") else None,
            gps_lon=float(form["gps_lon"]) if form.get("gps_lon") else None,
            what3words_address=form.get("what3words_address"),
            location_description=form.get("location_description"),
            description=form.get("description"),
            infrastructure_name=form.get("infrastructure_name"),
            other_infra_description=form.get("other_infra_description"),
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
