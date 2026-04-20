# UNDP RAPIDA Field Mapping

This document describes how platform report fields map to UNDP RAPIDA (Rapid Post-Crisis Integrated Digital Assessment) methodology fields.

## Core field mapping

| Platform field | RAPIDA field | Notes |
|---|---|---|
| `damage.level` | `damage_grade` | `minimal` = Grade 1, `partial` = Grade 2, `complete` = Grade 3 |
| `damage.infrastructure_types` | `infrastructure_category` | Multi-select maps to RAPIDA category codes |
| `damage.crisis_nature` | `hazard_type` | Direct mapping |
| `damage.requires_debris_clearing` | `debris_present` | Boolean |
| `location.coordinates` | `geo_point` | WGS84 [lon, lat] |
| `building_id` | `structure_id` | Microsoft Global Building Footprint ID |
| `damage.description_en` | `field_observation` | English translation always stored |
| `submitted_at` | `observation_datetime` | ISO 8601 UTC |
| `channel` | `data_source` | `telegram` / `pwa` / `sms` |
| `meta.submitter_tier` | `reporter_reliability` | `public` = standard, `verified` = high |

## RAPIDA damage grade mapping

| Platform `damage_level` | RAPIDA Grade | Description |
|---|---|---|
| `minimal` | Grade 1 | Structurally sound — cosmetic damage only, building still functional |
| `partial` | Grade 2 | Repairable structural damage — building usable with caution |
| `complete` | Grade 3 | Structurally unsafe or destroyed — building must not be entered |

## Dedicated RAPIDA export endpoint

```
GET /api/v1/rapida/{crisis_event_id}
```

Returns a GeoJSON FeatureCollection with RAPIDA-compatible property names. Compatible with RAPIDA's geospatial toolchain directly — no field remapping required.

## Infrastructure category codes

| Platform value | RAPIDA code | Description |
|---|---|---|
| `residential` | `RES` | Houses and apartments |
| `commercial` | `COM` | Markets, malls, banks, hotels |
| `government` | `GOV` | Admin buildings, police, courts |
| `utility` | `UTL` | Water pumps, power plants, waste treatment |
| `transport` | `TRN` | Roads, bridges, cell towers, railways |
| `community` | `COM_SVC` | Schools, hospitals, community halls |
| `public_space` | `PUB` | Stadiums, playgrounds, religious buildings |
| `other` | `OTH` | Free-text description in `damage.infrastructure_name` |
