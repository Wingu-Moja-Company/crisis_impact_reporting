"""
Export damage reports as a GeoJSON FeatureCollection.
Directly ingestible by OCHA HDX, QGIS, ArcGIS, and the UNDP RAPIDA toolchain.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.cosmos import CosmosClient
from azure.storage.blob import BlobSasPermissions, generate_blob_sas


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


def _photo_url(blob_path: str | None) -> str | None:
    """Generate a 2-hour SAS URL for a photo blob. Returns None on any failure."""
    if not blob_path:
        return None
    try:
        conn_str = os.environ.get("STORAGE_CONNECTION_STRING", "")
        parts = dict(seg.split("=", 1) for seg in conn_str.split(";") if "=" in seg)
        account_name = parts.get("AccountName", "")
        account_key = parts.get("AccountKey", "")
        if not account_name or not account_key:
            return None
        sas = generate_blob_sas(
            account_name=account_name,
            container_name="report-photos",
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        return f"https://{account_name}.blob.core.windows.net/report-photos/{blob_path}?{sas}"
    except Exception:
        return None


_EXPORT_PRECISION = 5  # decimal places ≈ 1.1 m — enough for building-level work,
                       # prevents sub-metre location fingerprinting in public exports.


def _round_coords(coords: list) -> list:
    """Round [lon, lat] to _EXPORT_PRECISION decimal places for exported features."""
    return [round(c, _EXPORT_PRECISION) for c in coords]


def build_feature(doc: dict) -> dict | None:
    coords = doc.get("location", {}).get("coordinates")
    if not coords:
        return None
    blob_path = doc.get("media", {}).get("photo_blob_path")
    damage = doc.get("damage", {})

    # Custom field responses — handle both new (responses) and old (modular_fields) formats
    responses: dict = doc.get("responses") or doc.get("modular_fields") or {}

    # Backward-compat reads for crisis_nature and requires_debris_clearing:
    # In old reports they live in damage.*; in new reports in responses (but also
    # mirrored into damage.* for backward compat by the pipeline).
    crisis_nature = damage.get("crisis_nature") or responses.get("crisis_nature")
    requires_debris = damage.get("requires_debris_clearing")
    if requires_debris is None:
        requires_debris = responses.get("requires_debris_clearing")

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": _round_coords(coords)},
        "properties": {
            # Core identifiers
            "report_id":                doc["id"],
            "crisis_event_id":          doc["crisis_event_id"],
            "building_id":              doc.get("building_id"),
            "submitted_at":             doc["submitted_at"],
            "channel":                  doc["channel"],
            "schema_version":           doc.get("schema_version"),
            # Damage assessment (RAPIDA / OCHA HDX standard fields)
            "damage_level":             damage.get("level"),
            "infrastructure_types":     damage.get("infrastructure_types", []),
            "infrastructure_name":      damage.get("infrastructure_name"),
            "crisis_nature":            crisis_nature,
            "requires_debris_clearing": requires_debris,
            "description_en":           damage.get("description_en"),
            "ai_vision_confidence":           damage.get("ai_vision_confidence"),
            "ai_vision_suggested_level":      damage.get("ai_vision_suggested_level"),
            "ai_vision_summary":              damage.get("ai_vision_summary"),
            "ai_vision_debris_confirmed":     damage.get("ai_vision_debris_confirmed"),
            "ai_vision_access_status":        damage.get("ai_vision_access_status"),
            "ai_vision_hazard_indicators":    damage.get("ai_vision_hazard_indicators") or [],
            "ai_vision_intervention_priority": damage.get("ai_vision_intervention_priority"),
            # Location detail
            "what3words":               doc.get("location", {}).get("what3words"),
            "location_description":     doc.get("location", {}).get("location_description"),
            "building_footprint_matched": doc.get("location", {}).get("building_footprint_matched", False),
            # Reporter trust
            "submitter_tier":           doc.get("meta", {}).get("submitter_tier", "public"),
            # Photo evidence — short-lived SAS URL (valid 2 h)
            "photo_url":                _photo_url(blob_path),
            # Flatten all custom field responses (dynamic — keys vary per schema)
            **responses,
        },
    }


def export_current_buildings(
    crisis_event_id: str,
    bbox: tuple[float, float, float, float] | None = None,
    damage_level: str | None = None,
) -> dict:
    """
    One GeoJSON Feature per building, reflecting its current (authoritative) damage state.
    Queries the `buildings` container — each doc is already the winner of the severity-bias logic.
    """
    conditions = ["c.crisis_event_id = @cid", "IS_DEFINED(c.lat)", "IS_DEFINED(c.lon)"]
    params: list[dict[str, Any]] = [{"name": "@cid", "value": crisis_event_id}]

    if damage_level:
        conditions.append("c.current_damage_level = @dmg")
        params.append({"name": "@dmg", "value": damage_level})

    query = f"SELECT * FROM c WHERE {' AND '.join(conditions)}"

    docs = list(_container("buildings").query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))

    features = []
    for doc in docs:
        lat = doc.get("lat")
        lon = doc.get("lon")
        if lat is None or lon is None:
            continue
        if bbox:
            lat_min, lon_min, lat_max, lon_max = bbox
            if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": _round_coords([lon, lat])},
            "properties": {
                "building_id":              doc["building_id"],
                "crisis_event_id":          doc["crisis_event_id"],
                "current_damage_level":     doc["current_damage_level"],
                "current_damage_report_id": doc.get("current_damage_report_id"),
                "report_count":             doc.get("report_count", 1),
                "last_updated":             doc.get("last_updated"),
                "requires_debris_clearing": doc.get("requires_debris_clearing"),
                "submitter_tier":           doc.get("submitter_tier", "public"),
                "has_photo":                doc.get("has_photo", False),
            },
        })

    return {"type": "FeatureCollection", "features": features}


_SEVERITY_ORDER = ["minimal", "partial", "complete"]
_INTERVENTION_PRIORITY = {
    "complete": "critical",
    "partial":  "high",
    "minimal":  "medium",
}


def export_area_summary(
    crisis_event_id: str,
    bbox: tuple[float, float, float, float] | None = None,
) -> dict:
    """
    Counts of buildings by damage level for the given crisis event / bbox.
    Returns one summary object — not GeoJSON — suitable for dashboard widgets.
    """
    conditions = ["c.crisis_event_id = @cid"]
    params: list[dict[str, Any]] = [{"name": "@cid", "value": crisis_event_id}]

    query = f"SELECT c.current_damage_level, c.lat, c.lon, c.requires_debris_clearing FROM c WHERE {' AND '.join(conditions)}"

    docs = list(_container("buildings").query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))

    counts: dict[str, int] = {}
    debris_required = 0
    total = 0
    for doc in docs:
        if bbox:
            lat = doc.get("lat")
            lon = doc.get("lon")
            if lat is None or lon is None:
                continue
            lat_min, lon_min, lat_max, lon_max = bbox
            if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                continue
        lvl = doc.get("current_damage_level", "unknown")
        counts[lvl] = counts.get(lvl, 0) + 1
        total += 1
        if doc.get("requires_debris_clearing"):
            debris_required += 1

    by_level = [
        {
            "damage_level": lvl,
            "count": counts.get(lvl, 0),
            "intervention_priority": _INTERVENTION_PRIORITY.get(lvl, "low"),
        }
        for lvl in _SEVERITY_ORDER
        if counts.get(lvl, 0) > 0
    ]
    # include any unexpected values
    for lvl, cnt in counts.items():
        if lvl not in _SEVERITY_ORDER:
            by_level.append({"damage_level": lvl, "count": cnt, "intervention_priority": "unknown"})

    return {
        "crisis_event_id": crisis_event_id,
        "total_buildings": total,
        "debris_clearing_required": debris_required,
        "by_damage_level": by_level,
    }


def export_geojson(
    crisis_event_id: str,
    bbox: tuple[float, float, float, float] | None = None,
    damage_level: str | None = None,
    infra_type: str | None = None,
    since: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict:
    conditions = ["c.crisis_event_id = @cid"]
    params: list[dict[str, Any]] = [{"name": "@cid", "value": crisis_event_id}]

    if damage_level:
        conditions.append("c.damage.level = @dmg")
        params.append({"name": "@dmg", "value": damage_level})
    if infra_type:
        conditions.append("ARRAY_CONTAINS(c.damage.infrastructure_types, @infra)")
        params.append({"name": "@infra", "value": infra_type})
    if since:
        conditions.append("c.submitted_at >= @since")
        params.append({"name": "@since", "value": since})

    query = (
        f"SELECT * FROM c WHERE {' AND '.join(conditions)} "
        f"OFFSET {offset} LIMIT {limit}"
    )

    docs = list(_container("reports").query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))

    features = [f for doc in docs if (f := build_feature(doc)) is not None]

    if bbox:
        lat_min, lon_min, lat_max, lon_max = bbox
        features = [
            f for f in features
            if lon_min <= f["geometry"]["coordinates"][0] <= lon_max
            and lat_min <= f["geometry"]["coordinates"][1] <= lat_max
        ]

    return {"type": "FeatureCollection", "features": features}
