# Partner API Reference

Base URL: `https://api.crisisplatform.io/api`

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
