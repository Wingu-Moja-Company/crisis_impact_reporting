"""
Download building footprints from the Microsoft Global Building Footprints dataset.

Usage:
    python scripts/download_footprints.py --country KE --output data/footprints/ke.geojson
    python scripts/download_footprints.py --country KE --region nairobi --output data/footprints/ke-nairobi.geojson
"""

import argparse
import json
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


def fetch_index() -> list[dict]:
    print("Fetching Microsoft footprints index …")
    with urllib.request.urlopen(MS_FOOTPRINTS_INDEX, timeout=30) as resp:
        lines = resp.read().decode().splitlines()
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","))) for line in lines[1:] if line.strip()]


def download_country(country: str, region: str | None, output: Path) -> None:
    country = country.upper()
    if country not in AFRICA_COUNTRY_CODES:
        print(f"Warning: {country} is not in the known Africa country list.", file=sys.stderr)

    records = fetch_index()
    matches = [r for r in records if r.get("Location", "").upper().startswith(country)]

    if region:
        region_lower = region.lower()
        region_matches = [r for r in matches if region_lower in r.get("Location", "").lower()]
        if region_matches:
            matches = region_matches
        else:
            print(f"No region-specific tiles found for '{region}', downloading full country.")

    if not matches:
        print(f"No footprint tiles found for country '{country}'.", file=sys.stderr)
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)

    all_features: list[dict] = []
    for record in matches:
        url = record.get("Url") or record.get("url") or ""
        if not url:
            continue
        print(f"Downloading {url} …")
        with urllib.request.urlopen(url, timeout=120) as resp:
            tile = json.loads(resp.read())
        all_features.extend(tile.get("features", []))

    collection = {"type": "FeatureCollection", "features": all_features}
    output.write_text(json.dumps(collection))
    print(f"Saved {len(all_features):,} footprints → {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Microsoft building footprints")
    parser.add_argument("--country", required=True, help="ISO 3166-1 alpha-2 country code (e.g. KE)")
    parser.add_argument("--region", default=None, help="Optional region / city name filter")
    parser.add_argument("--output", required=True, type=Path, help="Output GeoJSON file path")
    args = parser.parse_args()
    download_country(args.country, args.region, args.output)


if __name__ == "__main__":
    main()
