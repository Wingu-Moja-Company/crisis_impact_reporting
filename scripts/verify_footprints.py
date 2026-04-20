"""
Verify that building footprints are loaded in PostGIS for a given region.

Usage:
    python scripts/verify_footprints.py --region nairobi
    python scripts/verify_footprints.py --region nairobi --country KE
"""

import argparse
import os
import sys

import psycopg2


def _get_conn():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def verify(country: str, region: str) -> None:
    print(f"Verifying footprints for country={country}, region={region} …")
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM building_footprints WHERE country_code = %s AND region = %s",
            (country.upper(), region.lower()),
        )
        count = cur.fetchone()[0]

    if count == 0:
        print(
            f"ERROR: No footprints found for country={country} region={region}.\n"
            "Run: python scripts/download_footprints.py and python scripts/load_footprints.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"OK — {count:,} building footprints loaded for {region}, {country}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify PostGIS footprint coverage for a region")
    parser.add_argument("--country", default="KE",      help="ISO 3166-1 alpha-2 country code")
    parser.add_argument("--region",  required=True,     help="Region / city name")
    args = parser.parse_args()
    verify(args.country, args.region)


if __name__ == "__main__":
    main()
