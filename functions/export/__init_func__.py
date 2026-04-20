"""
Azure Functions HTTP triggers for all export endpoints.

GET /api/v1/reports         — GeoJSON | CSV | Shapefile
GET /api/v1/feeds/cap/{id}.xml
GET /api/v1/buildings/{id}/history
GET /api/v1/crisis-events
GET /api/v1/crisis-events/{id}/stats
"""

import json
import os
import azure.functions as func

from functions.export.geojson import export_geojson
from functions.export.csv_export import export_csv
from functions.export.shapefile import export_shapefile
from functions.export.cap_feed import build_cap_feed


def _parse_bbox(raw: str | None):
    if not raw:
        return None
    parts = [float(x) for x in raw.split(",")]
    return tuple(parts) if len(parts) == 4 else None


def reports(req: func.HttpRequest) -> func.HttpResponse:
    crisis_event_id = req.params.get("crisis_event_id")
    if not crisis_event_id:
        return func.HttpResponse('{"error":"crisis_event_id required"}', status_code=400, mimetype="application/json")

    fmt        = req.params.get("format", "geojson")
    bbox       = _parse_bbox(req.params.get("bbox"))
    dmg        = req.params.get("damage_level")
    infra      = req.params.get("infra_type")
    since      = req.params.get("since")
    limit      = int(req.params.get("limit", "1000"))
    offset     = int(req.params.get("offset", "0"))

    if fmt == "csv":
        body = export_csv(crisis_event_id, bbox, dmg, infra, since, limit, offset)
        return func.HttpResponse(body, mimetype="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="{crisis_event_id}.csv"'})

    if fmt == "shapefile":
        body = export_shapefile(crisis_event_id, bbox, dmg, infra, since, limit, offset)
        return func.HttpResponse(body, mimetype="application/zip",
                                 headers={"Content-Disposition": f'attachment; filename="{crisis_event_id}.zip"'})

    # Default: GeoJSON
    collection = export_geojson(crisis_event_id, bbox, dmg, infra, since, limit, offset)
    return func.HttpResponse(json.dumps(collection), mimetype="application/geo+json")


def cap_feed(req: func.HttpRequest) -> func.HttpResponse:
    crisis_event_id = req.route_params.get("crisis_event_id", "")
    xml = build_cap_feed(crisis_event_id)
    return func.HttpResponse(xml, mimetype="application/xml")


def building_history(req: func.HttpRequest) -> func.HttpResponse:
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
    from azure.cosmos import CosmosClient
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    container = client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("crisis_events")
    docs = list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))
    return func.HttpResponse(json.dumps(docs), mimetype="application/json")


def crisis_event_stats(req: func.HttpRequest) -> func.HttpResponse:
    from azure.cosmos import CosmosClient
    crisis_event_id = req.route_params.get("crisis_event_id", "")
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])

    total = next(iter(db.get_container_client("reports").query_items(
        "SELECT VALUE COUNT(1) FROM c WHERE c.crisis_event_id = @cid",
        parameters=[{"name": "@cid", "value": crisis_event_id}],
        enable_cross_partition_query=True,
    )), 0)

    by_level = {}
    for row in db.get_container_client("reports").query_items(
        "SELECT c.damage.level AS lvl, COUNT(1) AS cnt FROM c WHERE c.crisis_event_id = @cid GROUP BY c.damage.level",
        parameters=[{"name": "@cid", "value": crisis_event_id}],
        enable_cross_partition_query=True,
    ):
        by_level[row["lvl"]] = row["cnt"]

    return func.HttpResponse(
        json.dumps({"crisis_event_id": crisis_event_id, "total_reports": total, "by_damage_level": by_level}),
        mimetype="application/json",
    )
