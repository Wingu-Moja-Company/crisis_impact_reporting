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
  onBuildingSelect: (id: string) => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
  unknown:  "#888780",
};

const DAMAGE_RADIUS: Record<string, number> = {
  minimal:  6,
  partial:  9,
  complete: 12,
  unknown:  6,
};

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
  center, zoom = 13, footprints, liveReports, selectedBuildingId, onBuildingSelect,
}: Props) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const mapRef         = useRef<L.Map | null>(null);
  const footprintLayer = useRef<L.GeoJSON | null>(null);
  const reportLayer    = useRef<L.LayerGroup | null>(null);

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

  // ── Re-render footprint polygons when selection changes ────────────────────
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

  // ── Re-render ALL report markers whenever the list changes ─────────────────
  useEffect(() => {
    if (!mapRef.current || !reportLayer.current) return;

    reportLayer.current.clearLayers();

    const withCoords = liveReports.filter((r) => r.coordinates !== null);
    if (withCoords.length === 0) return;

    for (const r of withCoords) {
      const [lon, lat] = r.coordinates!;
      L.circleMarker([lat, lon], {
        radius:      DAMAGE_RADIUS[r.damage_level] ?? 6,
        color:       DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
        fillColor:   DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
        fillOpacity: 0.75,
        weight:      1.5,
      })
        .bindPopup(reportPopup(r), { maxWidth: 260 })
        .addTo(reportLayer.current);
    }

    // Auto-fit map bounds to all report markers on first load
    if (withCoords.length > 0 && mapRef.current.getZoom() === zoom) {
      const latlngs = withCoords.map((r) => [r.coordinates![1], r.coordinates![0]] as [number, number]);
      mapRef.current.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40], maxZoom: 14 });
    }
  }, [liveReports]);

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
