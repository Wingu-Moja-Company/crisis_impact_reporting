import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LiveReport } from "../../hooks/useLiveReports";

interface BuildingFeature extends GeoJSON.Feature {
  properties: {
    building_id: string;
    current_damage_level?: string;
    report_count?: number;
  };
}

interface Props {
  center: [number, number];
  zoom?: number;
  footprints?: BuildingFeature[];
  liveReports: LiveReport[];
  selectedBuildingId: string | null;
  selectedReportId: string | null;
  onBuildingSelect: (id: string) => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
  unknown:  "#888780",
};

function markerRadius(level: string, selected: boolean) {
  const base = level === "complete" ? 12 : level === "partial" ? 9 : 6;
  return selected ? base + 5 : base;
}

function reportPopup(r: LiveReport): string {
  const infra = r.infrastructure_types?.join(", ") || "—";
  const desc  = r.description_en ? `<p class="popup-desc">${r.description_en}</p>` : "";
  const time  = r.submitted_at
    ? new Date(r.submitted_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
    : "—";
  return `
    <div class="report-popup">
      <span class="popup-badge popup-badge--${r.damage_level}">${r.damage_level.toUpperCase()}</span>
      <div class="popup-meta">
        <span>🏗 ${infra}</span>
        <span>📡 ${r.channel}</span>
        <span>🕐 ${time}</span>
      </div>
      ${desc}
    </div>
  `;
}

export function DashboardMap({
  center, zoom = 13, footprints, liveReports,
  selectedBuildingId, selectedReportId, onBuildingSelect,
}: Props) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const mapRef         = useRef<L.Map | null>(null);
  const footprintLayer = useRef<L.GeoJSON | null>(null);
  const reportLayer    = useRef<L.LayerGroup | null>(null);
  // report_id → circleMarker, so we can highlight / open popup on selection
  const markerIndex    = useRef<Map<string, L.CircleMarker>>(new Map());
  const initialFit     = useRef(false);

  // ── Initialise map once ────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(mapRef.current);
    reportLayer.current = L.layerGroup().addTo(mapRef.current);
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  // ── Footprint polygons ────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || !footprints) return;
    footprintLayer.current?.remove();
    footprintLayer.current = L.geoJSON(
      { type: "FeatureCollection", features: footprints } as GeoJSON.FeatureCollection,
      {
        style: (f) => ({
          color:       DAMAGE_COLORS[f?.properties?.current_damage_level ?? "unknown"],
          weight:      f?.properties?.building_id === selectedBuildingId ? 3 : 1,
          fillOpacity: 0.5,
        }),
        onEachFeature: (f, layer) => {
          const { building_id, current_damage_level, report_count } = (f as BuildingFeature).properties;
          layer.on("click", () => onBuildingSelect(building_id));
          layer.bindTooltip(`${current_damage_level ?? "No reports"} | ${report_count ?? 0} report(s)`);
        },
      }
    ).addTo(mapRef.current);
  }, [footprints, selectedBuildingId]);

  // ── Rebuild all report markers when the list changes ─────────────────────
  useEffect(() => {
    if (!mapRef.current || !reportLayer.current) return;

    reportLayer.current.clearLayers();
    markerIndex.current.clear();

    const withCoords = liveReports.filter((r) => r.coordinates !== null);
    if (withCoords.length === 0) return;

    for (const r of withCoords) {
      const [lon, lat] = r.coordinates!;
      const isSelected = r.report_id === selectedReportId;
      const marker = L.circleMarker([lat, lon], {
        radius:      markerRadius(r.damage_level, isSelected),
        color:       isSelected ? "#fff" : DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
        fillColor:   DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
        fillOpacity: isSelected ? 1 : (selectedReportId ? 0.35 : 0.75),
        weight:      isSelected ? 3 : 1.5,
      })
        .bindPopup(reportPopup(r), { maxWidth: 260 })
        .addTo(reportLayer.current!);

      markerIndex.current.set(r.report_id, marker);
    }

    // Auto-fit bounds on first load only (skip if a report is pre-selected from URL)
    if (!initialFit.current && !selectedReportId) {
      const latlngs = withCoords.map((r) => [r.coordinates![1], r.coordinates![0]] as [number, number]);
      mapRef.current.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40], maxZoom: 14 });
      initialFit.current = true;
    }

    // If a report was pre-selected (e.g. from ?report= URL param), fly to it now
    // that markers have been built. This handles the race where selectedReportId
    // is set before the REST fetch completes.
    if (selectedReportId) {
      const selectedMarker = markerIndex.current.get(selectedReportId);
      const selectedReport = liveReports.find((r) => r.report_id === selectedReportId);
      if (selectedMarker && selectedReport?.coordinates) {
        const [lon, lat] = selectedReport.coordinates;
        mapRef.current.flyTo([lat, lon], Math.max(mapRef.current.getZoom(), 15), { duration: 0.8 });
        selectedMarker.openPopup();
        initialFit.current = true; // prevent fitBounds from overriding
      }
    }
  }, [liveReports]);

  // ── React to selection change: fly to marker + open popup ─────────────────
  useEffect(() => {
    if (!mapRef.current || !selectedReportId) return;

    const marker = markerIndex.current.get(selectedReportId);
    if (!marker) return;

    const report = liveReports.find((r) => r.report_id === selectedReportId);

    // Re-style all markers: highlight selected, dim others
    for (const [id, m] of markerIndex.current) {
      const r = liveReports.find((x) => x.report_id === id);
      const sel = id === selectedReportId;
      m.setStyle({
        radius:      markerRadius(r?.damage_level ?? "unknown", sel),
        color:       sel ? "#fff" : DAMAGE_COLORS[r?.damage_level ?? "unknown"],
        fillColor:   DAMAGE_COLORS[r?.damage_level ?? "unknown"],
        fillOpacity: sel ? 1 : 0.35,
        weight:      sel ? 3 : 1,
      });
      // CircleMarker doesn't inherit setRadius via setStyle — set directly
      (m as L.CircleMarker).setRadius(markerRadius(r?.damage_level ?? "unknown", sel));
    }

    // Fly to and open popup
    if (report?.coordinates) {
      const [lon, lat] = report.coordinates;
      mapRef.current.flyTo([lat, lon], Math.max(mapRef.current.getZoom(), 15), { duration: 0.8 });
    }
    marker.openPopup();
  }, [selectedReportId]);

  return (
    <>
      <style>{`
        .report-popup { font-size: 13px; line-height: 1.5; min-width: 180px; }
        .popup-badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
          font-weight: 700; font-size: 11px; color: #fff; margin-bottom: 6px; }
        .popup-badge--minimal  { background: #639922; }
        .popup-badge--partial  { background: #BA7517; }
        .popup-badge--complete { background: #E24B4A; }
        .popup-badge--unknown  { background: #888780; }
        .popup-meta { display: flex; flex-direction: column; gap: 2px; color: #444; font-size: 12px; }
        .popup-desc { margin-top: 6px; color: #333; border-top: 1px solid #eee; padding-top: 6px; }
      `}</style>
      <div ref={containerRef} className="dashboard-map" style={{ height: "100%", width: "100%" }} />
    </>
  );
}
