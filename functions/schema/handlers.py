"""
HTTP handlers for schema API endpoints.
Thin dispatch layer — all Cosmos logic is in service.py.
"""

import hmac
import json
import logging
import os

import azure.functions as func

from schema.service import (
    get_current_schema,
    get_schema_version,
    get_version_only,
    list_schema_history,
    publish_schema,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared response helpers
# ---------------------------------------------------------------------------

_NOT_FOUND = func.HttpResponse(
    '{"error":"not_found"}', status_code=404, mimetype="application/json"
)
_FORBIDDEN = func.HttpResponse(
    '{"error":"forbidden"}', status_code=403, mimetype="application/json"
)
_BAD_REQUEST = lambda msg: func.HttpResponse(
    json.dumps({"error": msg}), status_code=400, mimetype="application/json"
)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key, X-API-Key",
}


def _json_ok(data: dict | list, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data),
        status_code=status,
        mimetype="application/json",
        headers=_CORS,
    )


def _check_admin_key(req: func.HttpRequest) -> bool:
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected:
        return True  # dev mode — no key required
    provided = req.headers.get("X-Admin-Key", "")
    return bool(provided) and hmac.compare_digest(provided, expected)


# ---------------------------------------------------------------------------
# GET /api/v1/crisis-events/{event_id}/schema
# ---------------------------------------------------------------------------

def get_schema(req: func.HttpRequest) -> func.HttpResponse:
    """
    Public endpoint.
    ?version=N         → return that specific immutable snapshot
    ?version_only=true → return {"version": N} only (lightweight poll)
    (no params)        → return current schema
    """
    event_id = req.route_params.get("event_id", "").strip()
    if not event_id:
        return _BAD_REQUEST("event_id is required")

    version_only = req.params.get("version_only", "").lower() in ("true", "1", "yes")
    if version_only:
        version = get_version_only(event_id)
        if version is None:
            return _NOT_FOUND
        return _json_ok({"version": version})

    version_param = req.params.get("version", "").strip()
    if version_param:
        try:
            version_num = int(version_param)
        except ValueError:
            return _BAD_REQUEST("version must be an integer")
        schema = get_schema_version(event_id, version_num)
    else:
        schema = get_current_schema(event_id)

    if schema is None:
        return _NOT_FOUND

    # Strip internal Cosmos metadata before returning
    for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
        schema.pop(key, None)

    return _json_ok(schema)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/crisis-events/{event_id}/schema
# ---------------------------------------------------------------------------

def post_schema(req: func.HttpRequest) -> func.HttpResponse:
    """
    Admin endpoint — publish a new schema version.
    Requires X-Admin-Key header.
    Body: { system_fields: {...}, custom_fields: [...] }
    """
    if not _check_admin_key(req):
        return _FORBIDDEN

    event_id = req.route_params.get("event_id", "").strip()
    if not event_id:
        return _BAD_REQUEST("event_id is required")

    try:
        body = req.get_json()
    except ValueError:
        return _BAD_REQUEST("Invalid JSON body")

    if "system_fields" not in body and "custom_fields" not in body:
        return _BAD_REQUEST("Body must contain system_fields and/or custom_fields")

    published_by = req.headers.get("X-Published-By", "admin").strip() or "admin"

    try:
        doc = publish_schema(event_id, body, published_by)
    except Exception as exc:
        logger.error("Schema publish failed for %s: %s", event_id, exc, exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "db_error", "detail": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

    for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
        doc.pop(key, None)

    return _json_ok(doc, status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/crisis-events/{event_id}/schema/history
# ---------------------------------------------------------------------------

def get_schema_history(req: func.HttpRequest) -> func.HttpResponse:
    """
    Admin endpoint — list all schema versions with metadata.
    Requires X-Admin-Key header.
    """
    if not _check_admin_key(req):
        return _FORBIDDEN

    event_id = req.route_params.get("event_id", "").strip()
    if not event_id:
        return _BAD_REQUEST("event_id is required")

    try:
        history = list_schema_history(event_id)
    except Exception as exc:
        logger.error("Schema history failed for %s: %s", event_id, exc, exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "db_error", "detail": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

    for item in history:
        for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
            item.pop(key, None)

    return _json_ok({"crisis_event_id": event_id, "versions": history})
