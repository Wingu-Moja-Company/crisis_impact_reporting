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

const GRADE_LABEL: Record<string, string> = {
  minimal:  "Grade 1 — Cosmetic damage",
  partial:  "Grade 2 — Repairable",
  complete: "Grade 3 — Structurally unsafe",
};

const CHANNEL_ICON: Record<string, string> = {
  telegram: "📱", pwa: "🌐", sms: "💬", api: "🔌",
};

function esc(s: string | null | undefined): string {
  return (s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function timeAgoPopup(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)    return `${diff}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function reportPopup(r: LiveReport): string {
  const grade    = GRADE_LABEL[r.damage_level] ?? r.damage_level.toUpperCase();
  const timeStr  = r.submitted_at ? timeAgoPopup(r.submitted_at) : "—";
  const infra    = r.infrastructure_types?.length ? r.infrastructure_types.map(esc).join(", ") : "—";
  const nature   = esc(r.crisis_nature) || "—";
  const chanIcon = CHANNEL_ICON[r.channel] ?? "📡";
  const tier     = r.submitter_tier === "verified" ? "✓ Verified" : "👤 Public";

  const photoHtml = r.photo_url ? `
    <div class="pp-media">
      <img src="${esc(r.photo_url)}" alt="Damage photo" class="pp-photo"
           onerror="this.parentElement.style.display='none'">
    </div>` : `<div class="pp-no-photo">📷 No photo submitted</div>`;

  const debrisHtml = r.requires_debris_clearing
    ? `<div class="pp-debris">⚠️ Debris clearing required</div>` : "";

  const locationHtml = (() => {
    if (r.what3words) {
      const words = r.what3words.replace(/^\/+/, ""); // strip any leading slashes
      return `<div class="pp-row">📍 3-word code: ${esc(words)}</div>`;
    }
    if (r.location_description) return `<div class="pp-row">📍 ${esc(r.location_description)}</div>`;
    if (r.building_footprint_matched) return `<div class="pp-row">📍 Building GPS matched</div>`;
    return "";
  })();

  const descHtml = r.description_en
    ? `<div class="pp-desc">${esc(r.description_en)}</div>` : "";

  // AI summary — prefer GPT-4o summary; fall back to nothing
  const aiHtml = r.ai_vision_summary
    ? `<div class="pp-ai">🤖 ${esc(r.ai_vision_summary)}</div>` : "";

  return `
    <div class="report-popup">
      <div class="pp-header pp-header--${r.damage_level}">
        <span class="pp-grade">${esc(grade)}</span>
        <span class="pp-time">${timeStr}</span>
      </div>
      ${photoHtml}
      ${debrisHtml}
      <div class="pp-details">
        <div class="pp-row">🏗 ${infra}</div>
        <div class="pp-row">🌊 ${nature}</div>
        <div class="pp-row">${chanIcon} ${esc(r.channel)} · ${tier}</div>
        ${locationHtml}
      </div>
      ${aiHtml}
      ${descHtml}
      <div class="pp-id">${esc(r.report_id)}</div>
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
        .report-popup { font-size: 13px; line-height: 1.5; min-width: 220px; max-width: 280px; }

        /* Colour header strip */
        .pp-header { display: flex; justify-content: space-between; align-items: center;
          padding: 6px 10px; border-radius: 4px 4px 0 0; margin: -4px -4px 8px -4px; }
        .pp-header--minimal  { background: #639922; color: #fff; }
        .pp-header--partial  { background: #BA7517; color: #fff; }
        .pp-header--complete { background: #E24B4A; color: #fff; }
        .pp-header--unknown  { background: #888780; color: #fff; }
        .pp-grade { font-weight: 700; font-size: 12px; }
        .pp-time  { font-size: 11px; opacity: .85; }

        /* Photo thumbnail */
        .pp-media { position: relative; margin-bottom: 8px; }
        .pp-photo { width: 100%; height: 120px; object-fit: cover; border-radius: 4px;
          display: block; background: #eee; }
        .pp-no-photo { height: 36px; display: flex; align-items: center; justify-content: center;
          font-size: 11px; color: #aaa; background: #f9f9f9; border-radius: 4px;
          margin-bottom: 8px; border: 1px dashed #ddd; }

        /* Debris alert */
        .pp-debris { background: #fff3cd; border: 1px solid #f59e0b; border-radius: 4px;
          padding: 4px 8px; font-size: 12px; font-weight: 700; color: #92400e; margin-bottom: 8px; }

        /* Detail rows */
        .pp-details { display: flex; flex-direction: column; gap: 3px;
          color: #444; font-size: 12px; margin-bottom: 6px; }
        .pp-row { display: flex; align-items: flex-start; gap: 4px; text-transform: capitalize; }

        /* AI summary */
        .pp-ai { font-size: 11px; color: #1a56db; background: #eff6ff;
          border: 1px solid #bfdbfe; border-radius: 4px;
          padding: 4px 8px; margin-top: 4px; }

        /* Reporter description */
        .pp-desc { font-size: 12px; color: #333; border-top: 1px solid #eee;
          padding-top: 6px; margin-top: 4px; font-style: italic; }

        /* Report ID */
        .pp-id { font-family: monospace; font-size: 10px; color: #aaa;
          border-top: 1px solid #f0f0f0; margin-top: 6px; padding-top: 4px; }
      `}</style>
      <div ref={containerRef} className="dashboard-map" style={{ height: "100%", width: "100%" }} />
    </>
  );
}
