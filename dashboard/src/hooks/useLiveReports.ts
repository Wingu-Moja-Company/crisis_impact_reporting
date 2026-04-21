import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const WS_URL   = import.meta.env.VITE_WS_URL ?? null; // null = no WS server yet

export interface LiveReport {
  report_id: string;
  building_id: string | null;
  submitted_at: string;
  damage_level: string;
  infrastructure_types: string[];
  crisis_nature: string;
  channel: string;
  description_en: string | null;
  coordinates: [number, number] | null; // [lon, lat]
}

/** Map a GeoJSON feature (from /v1/reports) to LiveReport */
function featureToReport(f: GeoJSON.Feature): LiveReport | null {
  const p = f.properties as Record<string, unknown>;
  const geom = f.geometry as GeoJSON.Point | null;
  return {
    report_id:           String(p.report_id ?? ""),
    building_id:         (p.building_id as string) ?? null,
    submitted_at:        String(p.submitted_at ?? ""),
    damage_level:        String(p.damage_level ?? "unknown"),
    infrastructure_types: (p.infrastructure_types as string[]) ?? [],
    crisis_nature:       String(p.crisis_nature ?? ""),
    channel:             String(p.channel ?? ""),
    description_en:      (p.description_en as string) ?? null,
    coordinates:         geom?.coordinates ? [geom.coordinates[0], geom.coordinates[1]] : null,
  };
}

export function useLiveReports(crisisEventId: string) {
  const [reports, setReports] = useState<LiveReport[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // ── Initial REST fetch — load existing reports ────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch(
          `${API_BASE}/v1/reports?crisis_event_id=${encodeURIComponent(crisisEventId)}&format=geojson&limit=500`
        );
        if (!res.ok) return;
        const geojson: GeoJSON.FeatureCollection = await res.json();
        if (cancelled) return;
        const loaded = geojson.features
          .map(featureToReport)
          .filter((r): r is LiveReport => r !== null && r.coordinates !== null);
        setReports(loaded);
      } catch {
        // non-critical — map still works, just empty
      }
    }
    load();
    return () => { cancelled = true; };
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

  return { reports, connected };
}
