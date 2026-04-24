const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

/** Sent as X-API-Key on all export/read requests. Set VITE_EXPORT_API_KEY at build time. */
const EXPORT_API_KEY = import.meta.env.VITE_EXPORT_API_KEY ?? "";

function exportHeaders(): HeadersInit {
  return EXPORT_API_KEY ? { "X-API-Key": EXPORT_API_KEY } : {};
}

export interface Report {
  report_id: string;
  crisis_event_id: string;
  building_id: string | null;
  submitted_at: string;
  channel: string;
  damage_level: string;
  infrastructure_types: string[];
  crisis_nature: string;
  requires_debris_clearing: boolean;
  description_en: string | null;
  ai_vision_confidence: number | null;
  coordinates: [number, number] | null;
}

export interface BuildingVersion {
  id: string;
  building_id: string;
  report_id: string;
  damage_level: string;
  submitted_at: string;
  submitter_tier: string;
}

export interface BuildingProperties {
  building_id: string;
  crisis_event_id: string;
  current_damage_level: string;
  report_count: number;
  last_updated: string;
  requires_debris_clearing: boolean;
  submitter_tier: string;
  has_photo: boolean;
}

export interface BuildingSummaryRow {
  damage_level: string;
  count: number;
  intervention_priority: string;
}

export interface BuildingSummary {
  total_buildings: number;
  debris_clearing_required: number;
  by_damage_level: BuildingSummaryRow[];
}

export interface CrisisStats {
  crisis_event_id: string;
  total_reports: number;
  by_damage_level: Record<string, number>;
}

export async function fetchReports(params: {
  crisis_event_id: string;
  format?: "geojson" | "csv" | "shapefile";
  bbox?: string;
  damage_level?: string;
  infra_type?: string;
  since?: string;
  limit?: number;
  offset?: number;
}): Promise<{ type: string; features: GeoJSON.Feature[] }> {
  const query = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined)) as Record<string, string>
  );
  const res = await fetch(`${API_BASE}/v1/reports?${query}`, { headers: exportHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchBuildingHistory(buildingId: string): Promise<BuildingVersion[]> {
  const res = await fetch(`${API_BASE}/v1/buildings/${buildingId}/history`, { headers: exportHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchStats(crisisEventId: string): Promise<CrisisStats> {
  const res = await fetch(`${API_BASE}/v1/crisis-events/${crisisEventId}/stats`, { headers: exportHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchCurrentBuildings(
  crisisEventId: string
): Promise<GeoJSON.FeatureCollection> {
  const query = new URLSearchParams({ crisis_event_id: crisisEventId });
  const res = await fetch(`${API_BASE}/v1/buildings/current?${query}`, { headers: exportHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchBuildingSummary(crisisEventId: string): Promise<BuildingSummary> {
  const query = new URLSearchParams({ crisis_event_id: crisisEventId });
  const res = await fetch(`${API_BASE}/v1/buildings/summary?${query}`, { headers: exportHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function buildExportUrl(
  crisisEventId: string,
  format: "geojson" | "csv" | "shapefile",
  filters: Record<string, string> = {}
): string {
  const params = new URLSearchParams({ crisis_event_id: crisisEventId, format, ...filters });
  return `${API_BASE}/v1/reports?${params}`;
}
