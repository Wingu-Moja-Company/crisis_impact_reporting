"""
Simplify building footprint polygons for Leaflet delivery (~80% file size reduction).

Usage:
    python scripts/simplify_footprints.py \
        --input  data/footprints/ke.geojson \
        --output data/footprints/ke-simplified.geojson \
        --tolerance 0.00001
"""

import argparse
import json
import sys
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.validation import make_valid


def simplify(input_path: Path, output_path: Path, tolerance: float) -> None:
    data = json.loads(input_path.read_text())
    features = data.get("features", [])
    if not features:
        print("No features found in input GeoJSON.", file=sys.stderr)
        sys.exit(1)

    print(f"Simplifying {len(features):,} features (tolerance={tolerance}) …")

    simplified_features = []
    skipped = 0
    for feature in features:
        try:
            geom = make_valid(shape(feature["geometry"]))
            simplified = geom.simplify(tolerance, preserve_topology=True)
            if simplified.is_empty:
                skipped += 1
                continue
            simplified_features.append({
                "type": "Feature",
                "geometry": mapping(simplified),
                "properties": feature.get("properties") or {},
            })
        except Exception as exc:
            skipped += 1
            print(f"  Warning: skipped a feature — {exc}")

    collection = {"type": "FeatureCollection", "features": simplified_features}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(collection, separators=(",", ":")))

    original_kb = input_path.stat().st_size / 1024
    output_kb   = output_path.stat().st_size / 1024
    reduction   = 100 * (1 - output_kb / original_kb) if original_kb else 0

    print(
        f"Done — {len(simplified_features):,} features written "
        f"({skipped} skipped). "
        f"{original_kb:,.0f} KB → {output_kb:,.0f} KB ({reduction:.0f}% reduction)"
    )
    print(f"Output: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simplify building footprints for Leaflet delivery")
    parser.add_argument("--input",     required=True, type=Path)
    parser.add_argument("--output",    required=True, type=Path)
    parser.add_argument("--tolerance", type=float, default=0.00001,
                        help="Douglas-Peucker tolerance in degrees (default: 0.00001 ≈ 1 m)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    simplify(args.input, args.output, args.tolerance)


if __name__ == "__main__":
    main()
