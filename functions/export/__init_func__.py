"""
Azure Functions HTTP triggers for all export endpoints.

GET /api/v1/reports         — GeoJSON | CSV | Shapefile
GET /api/v1/feeds/cap/{id}.xml
GET /api/v1/buildings/{id}/history
GET /api/v1/crisis-events
GET /api/v1/crisis-events/{id}/stats
"""

import hmac
import json
import os
import re
import azure.functions as func

from export.geojson import export_geojson
from export.cap_feed import build_cap_feed


_UNAUTHORIZED = func.HttpResponse(
    '{"error":"unauthorized"}', status_code=401, mimetype="application/json",
    headers={"WWW-Authenticate": 'ApiKey realm="crisis-export"'},
)

_MAX_LIMIT = 5_000  # hard cap on result set size

# Matches any character that is NOT alphanumeric, hyphen, underscore, or dot.
# Used to sanitise strings embedded in Content-Disposition headers so a
# crafted crisis_event_id cannot inject extra headers or break quoting.
_SAFE_FILENAME_RE = re.compile(r"[^\w.\-]")


def _safe_filename(name: str, max_len: int = 64) -> str:
    """Return a filename-safe version of *name* (ASCII printable, no quotes/CR/LF)."""
    sanitised = _SAFE_FILENAME_RE.sub("_", name)
    return sanitised[:max_len] or "export"


def _check_api_key(req: func.HttpRequest) -> func.HttpResponse | None:
    """
    Validate the X-API-Key header against EXPORT_API_KEY env var.
    Returns a 401 response if invalid; None if the request is authorised.
    When EXPORT_API_KEY is not set the check is skipped (open / dev mode).
    """
    expected = os.environ.get("EXPORT_API_KEY", "")
    if not expected:
        return None  # Not configured — permit all (development)
    provided = req.headers.get("X-API-Key", "")
    if not provided or not hmac.compare_digest(provided, expected):
        return _UNAUTHORIZED
    return None


def _parse_bbox(raw: str | None):
    if not raw:
        return None
    parts = [float(x) for x in raw.split(",")]
    return tuple(parts) if len(parts) == 4 else None


def reports(req: func.HttpRequest) -> func.HttpResponse:
    if (err := _check_api_key(req)):
        return err

    crisis_event_id = req.params.get("crisis_event_id")
    if not crisis_event_id:
        return func.HttpResponse('{"error":"crisis_event_id required"}', status_code=400, mimetype="application/json")

    fmt        = req.params.get("format", "geojson")
    bbox       = _parse_bbox(req.params.get("bbox"))
    dmg        = req.params.get("damage_level")
    infra      = req.params.get("infra_type")
    since      = req.params.get("since")
    limit      = min(int(req.params.get("limit", "1000")), _MAX_LIMIT)
    offset     = int(req.params.get("offset", "0"))

    if fmt == "csv":
        from export.csv_export import export_csv
        body = export_csv(crisis_event_id, bbox, dmg, infra, since, limit, offset)
        safe = _safe_filename(crisis_event_id)
        return func.HttpResponse(body, mimetype="text/csv",
                                 headers={"Content-Disposition": f"attachment; filename=\"{safe}.csv\""})

    if fmt == "shapefile":
        from export.shapefile import export_shapefile
        body = export_shapefile(crisis_event_id, bbox, dmg, infra, since, limit, offset)
        safe = _safe_filename(crisis_event_id)
        return func.HttpResponse(body, mimetype="application/zip",
                                 headers={"Content-Disposition": f"attachment; filename=\"{safe}.zip\""})

    # Default: GeoJSON
    collection = export_geojson(crisis_event_id, bbox, dmg, infra, since, limit, offset)
    return func.HttpResponse(json.dumps(collection), mimetype="application/geo+json")


def cap_feed(req: func.HttpRequest) -> func.HttpResponse:
    if (err := _check_api_key(req)):
        return err
    crisis_event_id = req.route_params.get("crisis_event_id", "")
    xml = build_cap_feed(crisis_event_id)
    return func.HttpResponse(xml, mimetype="application/xml")


def building_history(req: func.HttpRequest) -> func.HttpResponse:
    if (err := _check_api_key(req)):
        return err
    from azure.cosmos import CosmosClient
    building_id = req.route_params.get("building_id", "")
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    container = client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("building_versions")
    docs = list(container.query_items(
        query="SELECT * FROM c WHERE c.building_id = @bid ORDER BY c.submitted_at ASC",
        parameters=[{"name": "@bid", "value": building_id}],
        enable_cross_partition_query=True,
    ))
    return func.HttpResponse(json.dumps(docs), mimetype="application/json")


def crisis_events(req: func.HttpRequest) -> func.HttpResponse:
    if (err := _check_api_key(req)):
        return err
    from azure.cosmos import CosmosClient
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    container = client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("crisis_events")
    docs = list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))
    return func.HttpResponse(json.dumps(docs), mimetype="application/json")


def crisis_event_stats(req: func.HttpRequest) -> func.HttpResponse:
    if (err := _check_api_key(req)):
        return err
    from azure.cosmos import CosmosClient
    crisis_event_id = req.route_params.get("crisis_event_id", "")
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])

    total = next(iter(db.get_container_client("reports").query_items(
        "SELECT VALUE COUNT(1) FROM c WHERE c.crisis_event_id = @cid",
        parameters=[{"name": "@cid", "value": crisis_event_id}],
        enable_cross_partition_query=True,
    )), 0)

    by_level: dict[str, int] = {}
    for doc in db.get_container_client("reports").query_items(
        "SELECT c.damage.level AS lvl FROM c WHERE c.crisis_event_id = @cid",
        parameters=[{"name": "@cid", "value": crisis_event_id}],
        enable_cross_partition_query=True,
    ):
        lvl = doc.get("lvl") or "unknown"
        by_level[lvl] = by_level.get(lvl, 0) + 1

    return func.HttpResponse(
        json.dumps({"crisis_event_id": crisis_event_id, "total_reports": total, "by_damage_level": by_level}),
        mimetype="application/json",
    )
