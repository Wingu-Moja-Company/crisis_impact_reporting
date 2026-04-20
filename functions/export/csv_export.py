"""Export damage reports as CSV (for spreadsheet analysis and IFRC GO)."""

import io
import pandas as pd
from functions.export.geojson import export_geojson


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

    rows = []
    for feature in collection["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        rows.append({
            "report_id":               props["report_id"],
            "crisis_event_id":         props["crisis_event_id"],
            "building_id":             props.get("building_id"),
            "submitted_at":            props["submitted_at"],
            "channel":                 props["channel"],
            "damage_level":            props["damage_level"],
            "infrastructure_types":    ",".join(props.get("infrastructure_types") or []),
            "crisis_nature":           props["crisis_nature"],
            "requires_debris_clearing": props["requires_debris_clearing"],
            "description_en":          props.get("description_en"),
            "ai_vision_confidence":    props.get("ai_vision_confidence"),
            "latitude":                lat,
            "longitude":               lon,
        })

    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()
