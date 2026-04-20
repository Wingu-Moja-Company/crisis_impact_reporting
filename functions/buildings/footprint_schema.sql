-- PostGIS building footprint store
-- Run once against the crisis_footprints database after enabling the PostGIS extension.
--
-- Prerequisites:
--   CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS building_footprints (
    building_id   TEXT PRIMARY KEY,          -- e.g. ke_nairobi_00123456
    country_code  CHAR(2)  NOT NULL,
    region        TEXT,
    geometry      GEOMETRY(Polygon, 4326),    -- WGS84
    source        TEXT     NOT NULL           -- microsoft | google | osm
                  CHECK (source IN ('microsoft', 'google', 'osm')),
    area_sqm      FLOAT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Primary spatial index — used for all point-in-polygon queries at ingestion time
CREATE INDEX IF NOT EXISTS idx_footprints_geom
    ON building_footprints USING GIST(geometry);

-- Country + region index — used when pre-loading footprints for a crisis region
CREATE INDEX IF NOT EXISTS idx_footprints_country_region
    ON building_footprints (country_code, region);


-- Point-in-polygon lookup used by the ingestion pipeline.
-- Returns the building_id whose polygon contains the submitted GPS coordinate.
-- $1 = longitude, $2 = latitude
--
-- Example:
--   SELECT building_id
--   FROM building_footprints
--   WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint($1, $2), 4326))
--   LIMIT 1;
