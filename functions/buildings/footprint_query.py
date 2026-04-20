import os
import psycopg2
import psycopg2.extras
from typing import Optional


def _get_conn():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


def resolve_building_id(lon: float, lat: float) -> Optional[str]:
    """Return the building_id whose footprint polygon contains (lon, lat), or None."""
    sql = """
        SELECT building_id
        FROM building_footprints
        WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        LIMIT 1
    """
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (lon, lat))
        row = cur.fetchone()
    return row[0] if row else None


def footprint_exists(country_code: str, region: str) -> bool:
    """Return True if at least one footprint row exists for the given country/region."""
    sql = """
        SELECT 1 FROM building_footprints
        WHERE country_code = %s AND region = %s
        LIMIT 1
    """
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (country_code.upper(), region.lower()))
        return cur.fetchone() is not None
