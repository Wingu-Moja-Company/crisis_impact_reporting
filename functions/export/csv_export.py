"""Export damage reports as CSV (for spreadsheet analysis and IFRC GO)."""

import csv
import io
from export.geojson import export_geojson

FIELDS = [
    "report_id", "crisis_event_id", "building_id", "submitted_at", "channel",
    "damage_level", "infrastructure_types", "crisis_nature",
    "requires_debris_clearing", "description_en", "ai_vision_confidence",
    "latitude", "longitude",
]


def export_csv(
    crisis_event_id: str,
    bbox=None,
    damage_level=None,
    infra_type=None,
    since=None,
    limit=1000,
    offset=0,
) -> str:
    collection = export_geojson(
        crisis_event_id, bbox, damage_level, infra_type, since, limit, offset
    )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()

    for feature in collection["features"]:
        props = feature["properties"]
        coords = feature.get("geometry", {}).get("coordinates") or [None, None]
        writer.writerow({
            "report_id":               props.get("report_id"),
            "crisis_event_id":         props.get("crisis_event_id"),
            "building_id":             props.get("building_id"),
            "submitted_at":            props.get("submitted_at"),
            "channel":                 props.get("channel"),
            "damage_level":            props.get("damage_level"),
            "infrastructure_types":    ",".join(props.get("infrastructure_types") or []),
            "crisis_nature":           props.get("crisis_nature"),
            "requires_debris_clearing": props.get("requires_debris_clearing"),
            "description_en":          props.get("description_en"),
            "ai_vision_confidence":    props.get("ai_vision_confidence"),
            "latitude":                coords[1],
            "longitude":               coords[0],
        })

    return buf.getvalue()
