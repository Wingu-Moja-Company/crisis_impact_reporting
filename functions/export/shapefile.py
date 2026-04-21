"""Export damage reports as a Shapefile (for ArcGIS and legacy GIS tools)."""

import io
import os
import tempfile
import zipfile

import fiona
from fiona.crs import from_epsg
from shapely.geometry import Point, mapping

from export.geojson import export_geojson

SCHEMA = {
    "geometry": "Point",
    "properties": {
        "report_id":    "str",
        "crisis_id":    "str",
        "building_id":  "str",
        "submitted":    "str",
        "channel":      "str",
        "damage":       "str",
        "infra_types":  "str",
        "crisis_type":  "str",
        "debris":       "bool",
        "ai_conf":      "float",
    },
}


def export_shapefile(
    crisis_event_id: str,
    bbox=None,
    damage_level=None,
    infra_type=None,
    since=None,
    limit=1000,
    offset=0,
) -> bytes:
    collection = export_geojson(
        crisis_event_id, bbox, damage_level, infra_type, since, limit, offset
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "reports.shp")

        with fiona.open(shp_path, "w", driver="ESRI Shapefile", crs=from_epsg(4326), schema=SCHEMA) as sink:
            for feature in collection["features"]:
                props = feature["properties"]
                lon, lat = feature["geometry"]["coordinates"]
                sink.write({
                    "geometry": mapping(Point(lon, lat)),
                    "properties": {
                        "report_id":   props["report_id"],
                        "crisis_id":   props["crisis_event_id"],
                        "building_id": props.get("building_id") or "",
                        "submitted":   props["submitted_at"],
                        "channel":     props["channel"],
                        "damage":      props["damage_level"],
                        "infra_types": ",".join(props.get("infrastructure_types") or []),
                        "crisis_type": props["crisis_nature"],
                        "debris":      props["requires_debris_clearing"],
                        "ai_conf":     props.get("ai_vision_confidence") or 0.0,
                    },
                })

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmpdir):
                zf.write(os.path.join(tmpdir, fname), fname)
        return buf.getvalue()
