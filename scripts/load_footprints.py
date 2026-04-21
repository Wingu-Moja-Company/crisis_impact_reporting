"""
Load building footprints from a GeoJSON file into PostGIS.

Usage:
    python scripts/load_footprints.py --input data/footprints/ke-nairobi.geojson
    python scripts/load_footprints.py --input data/footprints/ke.geojson --country KE --region nairobi
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras


BATCH_SIZE = 500


def _get_conn():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def _building_id(country: str, region: str, index: int) -> str:
    return f"{country.lower()}_{region.lower()}_{index:08d}"


def _area_sqm(geometry: dict) -> float | None:
    """Rough area estimate — PostGIS ST_Area on geography gives exact value; this is a fallback."""
    props = geometry.get("properties") or {}
    return props.get("area_in_meters") or props.get("area_sqm")


def load(input_path: Path, country: str, region: str) -> None:
    data = json.loads(input_path.read_text())
    features = data.get("features", [])
    if not features:
        print("No features found in GeoJSON.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {len(features):,} footprints (country={country}, region={region}) …")

    insert_sql = """
        INSERT INTO building_footprints
            (building_id, country_code, region, geometry, source, area_sqm)
        VALUES %s
        ON CONFLICT (building_id) DO UPDATE SET
            geometry  = EXCLUDED.geometry,
            area_sqm  = EXCLUDED.area_sqm,
            source    = EXCLUDED.source
    """
    # ST_GeomFromGeoJSON is injected as a literal so execute_values treats the
    # geometry column value as a PostGIS function call, not a plain string.
    template = "(%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s)"

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            batch = []
            for i, feature in enumerate(features):
                geom = json.dumps(feature["geometry"])
                row = (
                    _building_id(country, region, i),
                    country.upper(),
                    region.lower(),
                    geom,
                    "microsoft",
                    _area_sqm(feature),
                )
                batch.append(row)
                if len(batch) >= BATCH_SIZE:
                    psycopg2.extras.execute_values(cur, insert_sql, batch, template=template)
                    conn.commit()
                    print(f"  inserted {i + 1:,} / {len(features):,}", end="\r")
                    batch = []
            if batch:
                psycopg2.extras.execute_values(cur, insert_sql, batch, template=template)
                conn.commit()
    finally:
        conn.close()

    print(f"\nDone — {len(features):,} rows upserted.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load building footprints into PostGIS")
    parser.add_argument("--input",   required=True, type=Path, help="GeoJSON file to load")
    parser.add_argument("--country", default="KE",      help="ISO 3166-1 alpha-2 country code")
    parser.add_argument("--region",  default="nairobi", help="Region / city name")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    load(args.input, args.country, args.region)


if __name__ == "__main__":
    main()
