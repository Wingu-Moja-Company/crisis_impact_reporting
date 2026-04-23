# Partner API Reference

Base URL: `https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api`

Authentication is via API key in the `X-API-Key` header (partner tier) or Azure AD B2C token (admin tier). Public endpoints require no authentication.

---

## Endpoints

### List crisis events

```
GET /v1/crisis-events
```

Returns all active and historical crisis events.

---

### Crisis event statistics

```
GET /v1/crisis-events/{crisis_event_id}/stats
```

**Response**
```json
{
  "crisis_event_id": "ke-flood-2026-04",
  "total_reports": 12847,
  "by_damage_level": { "minimal": 5200, "partial": 5900, "complete": 1747 }
}
```

---

### Export damage reports

```
GET /v1/reports
```

| Parameter | Type | Description |
|---|---|---|
| `crisis_event_id` | string | **Required** |
| `format` | string | `geojson` (default) \| `csv` \| `shapefile` |
| `bbox` | string | `lat_min,lon_min,lat_max,lon_max` (WGS84) |
| `damage_level` | string | `minimal` \| `partial` \| `complete` |
| `infra_type` | string | e.g. `residential` |
| `since` | string | ISO 8601 datetime |
| `limit` | integer | Default 1000, max 5000 |
| `offset` | integer | Pagination offset |

**GeoJSON response** — `Content-Type: application/geo+json`

Compatible with OCHA HDX, QGIS, and ArcGIS.

---

### Current building damage state (latest-per-building GeoJSON)

```
GET /v1/buildings/current
```

One GeoJSON Feature per building, showing its current (authoritative) damage state. This is the primary endpoint for map visualisation — each building appears exactly once, with the winning damage assessment after severity-bias arbitration.

| Parameter | Type | Description |
|---|---|---|
| `crisis_event_id` | string | **Required** |
| `bbox` | string | `lat_min,lon_min,lat_max,lon_max` (WGS84) |
| `damage_level` | string | `minimal` \| `partial` \| `complete` |

**GeoJSON response** — `Content-Type: application/geo+json`

Feature properties include: `building_id`, `current_damage_level`, `report_count`, `last_updated`, `requires_debris_clearing`, `has_photo`, `submitter_tier`.

---

### Area damage summary

```
GET /v1/buildings/summary
```

Aggregate counts of buildings by damage level. Returns intervention priorities for dashboard widgets and situation reports.

| Parameter | Type | Description |
|---|---|---|
| `crisis_event_id` | string | **Required** |
| `bbox` | string | `lat_min,lon_min,lat_max,lon_max` (WGS84) |

**Response**
```json
{
  "crisis_event_id": "ke-flood-dev",
  "total_buildings": 347,
  "debris_clearing_required": 89,
  "by_damage_level": [
    { "damage_level": "complete", "count": 47, "intervention_priority": "critical" },
    { "damage_level": "partial",  "count": 180, "intervention_priority": "high" },
    { "damage_level": "minimal",  "count": 120, "intervention_priority": "medium" }
  ]
}
```

---

### Building version history

```
GET /v1/buildings/{building_id}/history
```

Returns the full append-only version history for a building, ordered by `submitted_at` ascending.

---

### CAP alert feed

```
GET /feeds/cap/{crisis_event_id}.xml
```

Common Alerting Protocol v1.2 (ISO 22324) feed. Updated every 5 minutes. Includes only `complete` (Grade 3) damage reports.

---

## Partner webhooks

Register a callback URL to receive real-time report notifications via CloudEvents 1.0.

**Registration** — contact the platform team to register a subscription with filter criteria:

| Filter | Description |
|---|---|
| `crisis_event_id` | Restrict to one crisis |
| `damage_level` | e.g. receive only `complete` reports |
| `infra_type` | e.g. `transport` only |
| `bbox` | Geographic bounding box |

**Payload** — signed with HMAC-SHA256 (`X-Signature-SHA256` header)

```json
{
  "specversion": "1.0",
  "type": "io.crisisplatform.report.submitted",
  "source": "/crisis-platform/ke-flood-2026-04",
  "id": "uuid",
  "time": "2026-04-20T14:32:00Z",
  "datacontenttype": "application/json",
  "data": { "...full report document..." }
}
```

---

## Rate limits

| Tier | Rate limit | Auth |
|---|---|---|
| Public | 100 req/min per IP | None |
| Partner | 1,000 req/min | API key |
| Platform Admin | Unlimited | Azure AD B2C |
