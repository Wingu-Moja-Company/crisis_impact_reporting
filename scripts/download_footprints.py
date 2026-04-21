"""
Download building footprints from the Microsoft Global Building Footprints dataset.

Usage:
    python scripts/download_footprints.py --country KE --output data/footprints/ke.geojson
    python scripts/download_footprints.py --country KE --region nairobi --output data/footprints/ke-nairobi.geojson
"""

import argparse
import gzip
import json
import math
import sys
import urllib.request
from pathlib import Path

# Microsoft Global Building Footprints — country index
# https://github.com/microsoft/GlobalMLBuildingFootprints
MS_FOOTPRINTS_INDEX = (
    "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
)

AFRICA_COUNTRY_CODES = {
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD",
    "KM", "CG", "CD", "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET",
    "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG",
    "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW",
    "ST", "SN", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN",
    "UG", "ZM", "ZW",
}

# Bounding boxes for commonly used regions (lon_min, lat_min, lon_max, lat_max)
REGION_BBOX: dict[str, tuple[float, float, float, float]] = {
    "nairobi":    (36.65, -1.45, 37.05, -1.10),
    "mombasa":    (39.55,  -4.10, 39.80,  -3.90),
    "kisumu":     (34.68,  -0.18, 34.85,   0.00),
    "kampala":    (32.50,   0.20, 32.80,   0.40),
    "dar es salaam": (39.15, -7.00, 39.50, -6.70),
    "lagos":      (3.10,   6.35,  3.60,   6.70),
    "accra":      (-0.35,   5.50,  0.05,   5.75),
    "addis ababa": (38.60,  8.90, 38.95,  9.10),
}


# ---------------------------------------------------------------------------
# Quadkey helpers
# ---------------------------------------------------------------------------

def _tile_from_latlon(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Return (tile_x, tile_y) for a lat/lon at the given zoom level."""
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def _quadkey_prefix(lat: float, lon: float, zoom: int) -> str:
    """Return the quadkey string for the tile containing (lat, lon) at given zoom."""
    x, y = _tile_from_latlon(lat, lon, zoom)
    qk = []
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if x & mask:
            digit += 1
        if y & mask:
            digit += 2
        qk.append(str(digit))
    return "".join(qk)


def _bbox_quadkey_prefixes(bbox: tuple[float, float, float, float], zoom: int = 9) -> set[str]:
    """Return the set of quadkey prefixes at `zoom` that intersect the bounding box."""
    lon_min, lat_min, lon_max, lat_max = bbox
    prefixes = set()
    # Sample a grid of points across the bbox
    steps = 10
    for i in range(steps + 1):
        for j in range(steps + 1):
            lat = lat_min + (lat_max - lat_min) * i / steps
            lon = lon_min + (lon_max - lon_min) * j / steps
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                prefixes.add(_quadkey_prefix(lat, lon, zoom))
    return prefixes


# ---------------------------------------------------------------------------
# Download logic
# ---------------------------------------------------------------------------

def fetch_index() -> list[dict]:
    print("Fetching Microsoft footprints index …")
    with urllib.request.urlopen(MS_FOOTPRINTS_INDEX, timeout=30) as resp:
        lines = resp.read().decode().splitlines()
    header = [h.strip() for h in lines[0].split(",")]
    return [dict(zip(header, [v.strip() for v in line.split(",")])) for line in lines[1:] if line.strip()]


def _download_tile(url: str) -> list[dict]:
    """Download and parse a .csv.gz tile (actually newline-delimited GeoJSON)."""
    with urllib.request.urlopen(url, timeout=120) as resp:
        raw = resp.read()
    # Decompress if gzipped
    try:
        data = gzip.decompress(raw)
    except Exception:
        data = raw
    features = []
    for line in data.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            feat = json.loads(line)
            if feat.get("type") == "Feature":
                features.append(feat)
        except json.JSONDecodeError:
            continue
    return features


def download_country(country: str, region: str | None, output: Path) -> None:
    country = country.upper()
    if country not in AFRICA_COUNTRY_CODES:
        print(f"Warning: {country} is not in the known Africa country list.", file=sys.stderr)

    records = fetch_index()
    # Match by Location column (e.g. "Kenya")
    matches = [r for r in records if country in r.get("Location", "").upper()
               or r.get("Location", "").upper().startswith(country)]

    if not matches:
        print(f"No footprint tiles found for country '{country}'.", file=sys.stderr)
        sys.exit(1)

    # Filter by region bounding box if known
    if region:
        bbox = REGION_BBOX.get(region.lower())
        if bbox:
            prefixes = _bbox_quadkey_prefixes(bbox, zoom=9)
            filtered = [r for r in matches if any(r.get("QuadKey", "").startswith(p) for p in prefixes)]
            if filtered:
                print(f"Filtered to {len(filtered)} tiles covering '{region}' (from {len(matches)} total).")
                matches = filtered
            else:
                print(f"No quadkey match for '{region}', downloading all {len(matches)} country tiles.")
        else:
            print(f"No bounding box for region '{region}', downloading all {len(matches)} country tiles.")

    print(f"Downloading {len(matches)} tile(s) …")
    output.parent.mkdir(parents=True, exist_ok=True)

    all_features: list[dict] = []
    for i, record in enumerate(matches, 1):
        url = record.get("Url") or record.get("url") or ""
        if not url:
            continue
        qk = record.get("QuadKey", "?")
        print(f"  [{i}/{len(matches)}] quadkey={qk} …", end=" ", flush=True)
        try:
            features = _download_tile(url)
            all_features.extend(features)
            print(f"{len(features)} buildings")
        except Exception as exc:
            print(f"FAILED: {exc}", file=sys.stderr)

    collection = {"type": "FeatureCollection", "features": all_features}
    output.write_text(json.dumps(collection))
    print(f"\nSaved {len(all_features):,} footprints → {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Microsoft building footprints")
    parser.add_argument("--country", required=True, help="ISO 3166-1 alpha-2 country code (e.g. KE)")
    parser.add_argument("--region", default=None, help="Optional region / city name filter")
    parser.add_argument("--output", required=True, type=Path, help="Output GeoJSON file path")
    args = parser.parse_args()
    download_country(args.country, args.region, args.output)


if __name__ == "__main__":
    main()
