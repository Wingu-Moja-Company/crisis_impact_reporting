# Humanitarian Field Mapping

This document describes how platform report fields map to humanitarian data standards fields.

## Core field mapping

| Platform field | Humanitarian field | Notes |
|---|---|---|
| `damage.level` | `damage_grade` | `minimal` = Grade 1, `partial` = Grade 2, `complete` = Grade 3 |
| `damage.infrastructure_types` | `infrastructure_category` | Multi-select maps to standard category codes |
| `damage.crisis_nature` | `hazard_type` | Direct mapping |
| `damage.requires_debris_clearing` | `debris_present` | Boolean |
| `location.coordinates` | `geo_point` | WGS84 [lon, lat] |
| `building_id` | `structure_id` | Microsoft Global Building Footprint ID |
| `damage.description_en` | `field_observation` | English translation always stored |
| `submitted_at` | `observation_datetime` | ISO 8601 UTC |
| `channel` | `data_source` | `telegram` / `pwa` |
| `meta.submitter_tier` | `reporter_reliability` | `public` = standard, `verified` = high |

## Damage grade mapping

| Platform `damage_level` | Standard Grade | Description |
|---|---|---|
| `minimal` | Grade 1 | Structurally sound — cosmetic damage only, building still functional |
| `partial` | Grade 2 | Repairable structural damage — building usable with caution |
| `complete` | Grade 3 | Structurally unsafe or destroyed — building must not be entered |

## Dedicated export endpoint

```
GET /api/v1/export/{crisis_event_id}
```

Returns a GeoJSON FeatureCollection with standardised property names, compatible with QGIS, ArcGIS, and OCHA HDX.

## Infrastructure category codes

| Platform value | Standard code | Description |
|---|---|---|
| `residential` | `RES` | Houses and apartments |
| `commercial` | `COM` | Markets, malls, banks, hotels |
| `government` | `GOV` | Admin buildings, police, courts |
| `utility` | `UTL` | Water pumps, power plants, waste treatment |
| `transport` | `TRN` | Roads, bridges, cell towers, railways |
| `community` | `COM_SVC` | Schools, hospitals, community halls |
| `public_space` | `PUB` | Stadiums, playgrounds, religious buildings |
| `other` | `OTH` | Free-text description in `damage.infrastructure_name` |
