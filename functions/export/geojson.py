"""
Export damage reports as a GeoJSON FeatureCollection.
Directly ingestible by OCHA HDX, QGIS, ArcGIS, and the UNDP RAPIDA toolchain.
"""

import os
from typing import Any

from azure.cosmos import CosmosClient


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


def build_feature(doc: dict) -> dict | None:
    coords = doc.get("location", {}).get("coordinates")
    if not coords:
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": coords},
        "properties": {
            "report_id":              doc["id"],
            "crisis_event_id":        doc["crisis_event_id"],
            "building_id":            doc.get("building_id"),
            "submitted_at":           doc["submitted_at"],
            "channel":                doc["channel"],
            "damage_level":           doc["damage"]["level"],
            "infrastructure_types":   doc["damage"]["infrastructure_types"],
            "crisis_nature":          doc["damage"]["crisis_nature"],
            "requires_debris_clearing": doc["damage"]["requires_debris_clearing"],
            "description_en":         doc["damage"].get("description_en"),
            "ai_vision_confidence":   doc["damage"].get("ai_vision_confidence"),
        },
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
