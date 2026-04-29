import { useEffect, useRef, useState } from "react";

const API_BASE      = import.meta.env.VITE_API_BASE_URL ?? "/api";
const WS_URL        = import.meta.env.VITE_WS_URL ?? null;
const EXPORT_API_KEY = import.meta.env.VITE_EXPORT_API_KEY ?? "";

function apiHeaders(): HeadersInit {
  return EXPORT_API_KEY ? { "X-API-Key": EXPORT_API_KEY } : {};
}

export interface LiveReport {
  report_id: string;
  building_id: string | null;
  submitted_at: string;
  damage_level: string;
  infrastructure_types: string[];
  infrastructure_name: string | null;
  /** Legacy field — also available in responses.crisis_nature for new reports */
  crisis_nature: string;
  channel: string;
  description_en: string | null;
  /** Legacy field — also available in responses.requires_debris_clearing for new reports */
  requires_debris_clearing: boolean;
  ai_vision_confidence: number | null;
  ai_vision_suggested_level: string | null;
  ai_vision_summary: string | null;
  ai_vision_debris_confirmed: boolean | null;
  ai_vision_access_status: string | null;
  ai_vision_hazard_indicators: string[];
  ai_vision_intervention_priority: string | null;
  what3words: string | null;
  location_description: string | null;
  building_footprint_matched: boolean;
  submitter_tier: "verified" | "public" | string;
  photo_url: string | null;
  coordinates: [number, number] | null; // [lon, lat]
  /** Dynamic custom field responses (new schema-driven format) */
  responses: Record<string, unknown>;
  /** Schema version the report was submitted against (null for pre-schema reports) */
  schema_version: number | null;
}

/** Map a GeoJSON feature (from /v1/reports) to LiveReport */
function featureToReport(f: GeoJSON.Feature): LiveReport | null {
  const p = f.properties as Record<string, unknown>;
  const geom = f.geometry as GeoJSON.Point | null;
  return {
    report_id:                String(p.report_id ?? ""),
    building_id:              (p.building_id as string) ?? null,
    submitted_at:             String(p.submitted_at ?? ""),
    damage_level:             String(p.damage_level ?? "unknown"),
    infrastructure_types:     (p.infrastructure_types as string[]) ?? [],
    infrastructure_name:      (p.infrastructure_name as string) ?? null,
    crisis_nature:            String(p.crisis_nature ?? ""),
    channel:                  String(p.channel ?? ""),
    // description_en: from pipeline translation. Fall back to raw description from
    // responses (flattened into GeoJSON props via **responses in geojson.py) for
    // reports where the PWA stored description inside the responses blob.
    description_en:           (p.description_en as string) ?? (p.description as string) ?? null,
    requires_debris_clearing: Boolean(p.requires_debris_clearing),
    ai_vision_confidence:             (p.ai_vision_confidence as number) ?? null,
    ai_vision_suggested_level:        (p.ai_vision_suggested_level as string) ?? null,
    ai_vision_summary:                (p.ai_vision_summary as string) ?? null,
    ai_vision_debris_confirmed:       p.ai_vision_debris_confirmed != null ? Boolean(p.ai_vision_debris_confirmed) : null,
    ai_vision_access_status:          (p.ai_vision_access_status as string) ?? null,
    ai_vision_hazard_indicators:      (p.ai_vision_hazard_indicators as string[]) ?? [],
    ai_vision_intervention_priority:  (p.ai_vision_intervention_priority as string) ?? null,
    what3words:               (p.what3words as string) ?? null,
    location_description:     (p.location_description as string) ?? null,
    building_footprint_matched: Boolean(p.building_footprint_matched),
    submitter_tier:           String(p.submitter_tier ?? "public"),
    photo_url:                (p.photo_url as string) ?? null,
    coordinates:              geom?.coordinates ? [geom.coordinates[0], geom.coordinates[1]] : null,
    // Dynamic schema fields — present for new reports, empty for legacy ones
    responses:                (p.responses as Record<string, unknown>) ?? {},
    schema_version:           (p.schema_version as number) ?? null,
  };
}

export function useLiveReports(crisisEventId: string) {
  const [reports, setReports] = useState<LiveReport[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastFetched, setLastFetched] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ── Initial REST fetch + 30-second polling ───────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch(
          `${API_BASE}/v1/reports?crisis_event_id=${encodeURIComponent(crisisEventId)}&format=geojson&limit=500`,
          { headers: apiHeaders() },
        );
        if (!res.ok) return;
        const geojson: GeoJSON.FeatureCollection = await res.json();
        if (cancelled) return;
        const loaded = geojson.features
          .map(featureToReport)
          .filter((r): r is LiveReport => r !== null && r.coordinates !== null);
        // Replace only if counts differ or when WS isn't keeping things live.
        // Sort newest-first so the feed always shows the latest at top.
        setReports(loaded.sort((a, b) => b.submitted_at.localeCompare(a.submitted_at)));
        setLastFetched(Date.now());
      } catch {
        // non-critical — map still works, just empty
      }
    }
    load();
    const interval = setInterval(load, 30_000); // poll every 30 s
    return () => { cancelled = true; clearInterval(interval); };
  }, [crisisEventId]);

  // ── WebSocket — prepend incoming reports in real time ────────────────────
  useEffect(() => {
    if (!WS_URL) return; // no WS server configured — skip silently

    const ws = new WebSocket(`${WS_URL}/reports?crisis_event_id=${crisisEventId}`);
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const report: LiveReport = JSON.parse(event.data);
        setReports((prev) => [report, ...prev].slice(0, 500));
      } catch {
        // ignore malformed frames
      }
    };

    return () => { ws.close(); wsRef.current = null; };
  }, [crisisEventId]);

  return { reports, connected, lastFetched };
}
