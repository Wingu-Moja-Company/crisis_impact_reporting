"""Export damage reports as CSV (for spreadsheet analysis and IFRC GO)."""

import csv
import io
import json
from export.geojson import export_geojson

# Fixed core columns that always appear (in this order)
_CORE_FIELDS = [
    "report_id", "crisis_event_id", "building_id", "submitted_at", "channel",
    "schema_version",
    "damage_level", "infrastructure_types", "crisis_nature",
    "requires_debris_clearing", "description_en",
    "ai_vision_confidence", "ai_vision_suggested_level", "ai_vision_summary",
    "ai_vision_access_status", "ai_vision_intervention_priority",
    "latitude", "longitude",
    "what3words", "location_description", "building_footprint_matched",
    "submitter_tier",
]

# Known custom field IDs that have special handling or should appear before
# the generic remainder.  Any additional response keys discovered in the data
# are appended alphabetically after these.
_KNOWN_RESPONSE_FIELDS = [
    "crisis_nature", "requires_debris_clearing", "water_level", "road_passable",
    "electricity_status", "health_services", "pressing_needs",
    "people_trapped", "aftershock_damage", "area_accessible", "civilian_displacement",
]


def _collect_response_keys(features: list[dict]) -> list[str]:
    """
    Discover all unique response field keys across all features.
    Returns keys in a stable order: known fields first, then alphabetical remainder.
    Known response fields that are already in _CORE_FIELDS (crisis_nature,
    requires_debris_clearing) are excluded to avoid duplicate columns.
    """
    all_keys: set[str] = set()
    for feature in features:
        props = feature.get("properties", {})
        # Response keys are everything not in the fixed core set
        for k in props:
            if k not in set(_CORE_FIELDS):
                all_keys.add(k)

    # Order: known first, then alphabetical remainder
    ordered = []
    for k in _KNOWN_RESPONSE_FIELDS:
        if k in all_keys and k not in set(_CORE_FIELDS):
            ordered.append(k)
            all_keys.discard(k)
    ordered.extend(sorted(all_keys))
    return ordered


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
    features = collection["features"]

    # Discover dynamic response columns from actual data
    response_fields = _collect_response_keys(features)
    fieldnames = _CORE_FIELDS + response_fields

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for feature in features:
        props = feature["properties"]
        coords = feature.get("geometry", {}).get("coordinates") or [None, None]

        # Serialise list-valued fields to JSON strings for CSV compatibility
        infra = props.get("infrastructure_types") or []
        pressing = props.get("pressing_needs")
        hazards = props.get("ai_vision_hazard_indicators") or []

        row: dict = {
            "report_id":               props.get("report_id"),
            "crisis_event_id":         props.get("crisis_event_id"),
            "building_id":             props.get("building_id"),
            "submitted_at":            props.get("submitted_at"),
            "channel":                 props.get("channel"),
            "schema_version":          props.get("schema_version"),
            "damage_level":            props.get("damage_level"),
            "infrastructure_types":    ",".join(infra) if isinstance(infra, list) else infra,
            "crisis_nature":           props.get("crisis_nature"),
            "requires_debris_clearing": props.get("requires_debris_clearing"),
            "description_en":          props.get("description_en"),
            "ai_vision_confidence":    props.get("ai_vision_confidence"),
            "ai_vision_suggested_level": props.get("ai_vision_suggested_level"),
            "ai_vision_summary":       props.get("ai_vision_summary"),
            "ai_vision_access_status": props.get("ai_vision_access_status"),
            "ai_vision_intervention_priority": props.get("ai_vision_intervention_priority"),
            "latitude":                coords[1],
            "longitude":               coords[0],
            "what3words":              props.get("what3words"),
            "location_description":    props.get("location_description"),
            "building_footprint_matched": props.get("building_footprint_matched"),
            "submitter_tier":          props.get("submitter_tier"),
        }

        # Dynamic response fields — serialise lists/dicts to JSON strings
        for field_id in response_fields:
            val = props.get(field_id)
            if isinstance(val, (list, dict)):
                row[field_id] = json.dumps(val, ensure_ascii=False)
            else:
                row[field_id] = val

        writer.writerow(row)

    return buf.getvalue()
