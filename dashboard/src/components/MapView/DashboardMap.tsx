import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LiveReport } from "../../hooks/useLiveReports";
import i18n from "../../i18n";

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

const CHANNEL_ICON: Record<string, string> = {
  telegram: "📱", pwa: "🌐", sms: "💬", api: "🔌",
};

// ── Shared map-positioning helpers ────────────────────────────────────────────

/** Fly to a lat/lon while offsetting the map centre upward so the popup card
 *  that opens above the marker is fully visible rather than clipped at the top. */
function flyToWithOffset(map: L.Map, lat: number, lon: number, zoom: number) {
  const markerPx  = map.project([lat, lon], zoom);
  const containerH = map.getContainer().getBoundingClientRect().height;
  // Shift centre up by 30 % → marker lands ~65 % down the screen
  const centerPx  = markerPx.subtract([0, containerH * 0.3]);
  map.flyTo(map.unproject(centerPx, zoom), zoom, { duration: 0.8 });
}

/** Smooth pan (no zoom change) with the same upward offset — used when the
 *  user clicks a marker directly on the map. */
function panToWithOffset(map: L.Map, lat: number, lon: number) {
  const zoom      = map.getZoom();
  const markerPx  = map.project([lat, lon], zoom);
  const containerH = map.getContainer().getBoundingClientRect().height;
  const centerPx  = markerPx.subtract([0, containerH * 0.3]);
  map.panTo(map.unproject(centerPx, zoom), { animate: true, duration: 0.5 });
}

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
  const t        = (key: string, opts?: Record<string, unknown>): string => String(i18n.t(key, opts as never));
  const grade    = t(`popup.grade_${r.damage_level}`, { defaultValue: r.damage_level.toUpperCase() });
  const timeStr  = r.submitted_at ? timeAgoPopup(r.submitted_at) : "—";
  const infra    = r.infrastructure_types?.length
    ? r.infrastructure_types.map((it) => esc(t(`infra.${it}`, { defaultValue: it }))).join(", ")
    : "—";
  const nature   = r.crisis_nature
    ? esc(t(`nature.${r.crisis_nature}`, { defaultValue: r.crisis_nature }))
    : "—";
  const chanIcon = CHANNEL_ICON[r.channel] ?? "📡";
  const tier     = r.submitter_tier === "verified"
    ? `✓ ${t("popup.verified")}`
    : `👤 ${t("popup.public_user")}`;

  const photoHtml = r.photo_url ? `
    <div class="pp-media">
      <img src="${esc(r.photo_url)}" alt="Damage photo" class="pp-photo"
           onerror="this.parentElement.style.display='none'">
    </div>` : `<div class="pp-no-photo">📷 ${esc(t("popup.no_photo"))}</div>`;

  const debrisHtml = r.requires_debris_clearing
    ? `<div class="pp-debris">⚠️ ${esc(t("popup.debris"))}</div>` : "";

  const locationHtml = (() => {
    if (r.what3words) {
      const words = r.what3words.replace(/^\/+/, "");
      return `<div class="pp-row">📍 ${esc(t("popup.three_word"))}: ${esc(words)}</div>`;
    }
    if (r.location_description) return `<div class="pp-row">📍 ${esc(r.location_description)}</div>`;
    if (r.building_footprint_matched) return `<div class="pp-row">📍 ${esc(t("popup.gps_matched"))}</div>`;
    return "";
  })();

  const descHtml = r.description_en
    ? `<div class="pp-desc">${esc(r.description_en)}</div>` : "";

  // AI assessment card — only shown when the model returned a result
  const hasAi = r.ai_vision_confidence != null && r.ai_vision_confidence > 0;
  const aiHtml = (() => {
    if (!hasAi) return "";

    const pct  = Math.round((r.ai_vision_confidence ?? 0) * 100);

    // Damage level agreement
    const aiLevel = r.ai_vision_suggested_level;
    const levelMatch = aiLevel && aiLevel === r.damage_level;
    const levelLabel = aiLevel
      ? t(`stats.${aiLevel}`, { defaultValue: aiLevel })
      : null;
    const levelRow = levelLabel
      ? `<div class="pp-ai-row">${levelMatch
          ? `<span class="pp-ai-badge pp-ai-match">✓ ${esc(t("popup.ai_agrees"))}: ${esc(levelLabel)}</span>`
          : `<span class="pp-ai-badge pp-ai-diff">⚡ ${esc(t("popup.ai_suggests"))}: ${esc(levelLabel)}</span>`
        }</div>`
      : "";

    // Access status
    const ACCESS_ICON: Record<string, string> = {
      clear: "🟢", limited: "🟡", blocked: "🔴", unknown: "⚪",
    };
    const accessRow = r.ai_vision_access_status
      ? `<div class="pp-ai-row">${ACCESS_ICON[r.ai_vision_access_status] ?? "⚪"} ${esc(t("popup.access"))}: <strong>${esc(r.ai_vision_access_status)}</strong></div>`
      : "";

    // Hazard indicators
    const hazards = (r.ai_vision_hazard_indicators ?? [])
      .map((h) => esc(t(`hazard.${h}`, { defaultValue: h })))
      .join(" · ");
    const hazardRow = hazards
      ? `<div class="pp-ai-row pp-ai-hazard">⚠️ ${hazards}</div>`
      : "";

    // Intervention priority
    const PRIORITY_CLASS: Record<string, string> = {
      low: "pp-pri-low", medium: "pp-pri-med", high: "pp-pri-high", critical: "pp-pri-crit",
    };
    const pri = r.ai_vision_intervention_priority;
    const priorityRow = pri
      ? `<div class="pp-ai-row"><span class="pp-priority ${PRIORITY_CLASS[pri] ?? ""}">${esc(t(`popup.priority_${pri}`, { defaultValue: pri }))}</span></div>`
      : "";

    // Summary
    const summaryRow = r.ai_vision_summary
      ? `<div class="pp-ai-summary">"${esc(r.ai_vision_summary)}"</div>`
      : "";

    return `
      <div class="pp-ai-card">
        <div class="pp-ai-header">
          <span class="pp-ai-title">🤖 ${esc(t("popup.ai_title"))}</span>
          <span class="pp-ai-conf">${esc(t("popup.ai_confident", { pct }))}</span>
        </div>
        ${levelRow}${accessRow}${hazardRow}${priorityRow}${summaryRow}
      </div>`;
  })();

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
  // tracks which selectedReportId we have already flown to — prevents the
  // 30-second poll rebuild from re-flying and snapping the map back
  const hasPositionedFor = useRef<string | null>(null);

  // Track language so markers (popup HTML) rebuild when language changes
  const [lang, setLang] = useState(i18n.language);
  useEffect(() => {
    const h = () => setLang(i18n.language);
    i18n.on("languageChanged", h);
    return () => { i18n.off("languageChanged", h); };
  }, []);

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

  // ── Diff-update report markers when the list changes ────────────────────
  // We deliberately avoid clearLayers() on every poll — that destroys the open
  // popup DOM node and causes the photo to flash as it reloads. Instead we:
  //   • remove markers whose reports have gone away
  //   • update style + popup content for existing markers in-place
  //   • add markers for brand-new reports
  // For the currently-open popup we skip setPopupContent so the image is
  // never torn down while the user is looking at the card.
  useEffect(() => {
    if (!mapRef.current || !reportLayer.current) return;

    const withCoords = liveReports.filter((r) => r.coordinates !== null);
    const incomingIds = new Set(withCoords.map((r) => r.report_id));

    // 1. Remove stale markers
    for (const [id, m] of markerIndex.current) {
      if (!incomingIds.has(id)) {
        reportLayer.current.removeLayer(m);
        markerIndex.current.delete(id);
      }
    }

    // 2. Update existing / add new
    for (const r of withCoords) {
      const [lon, lat] = r.coordinates!;
      const isSelected = r.report_id === selectedReportId;
      const existing   = markerIndex.current.get(r.report_id);

      if (existing) {
        // Update visual style in-place (no DOM change)
        existing.setStyle({
          radius:      markerRadius(r.damage_level, isSelected),
          color:       isSelected ? "#fff" : DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
          fillColor:   DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
          fillOpacity: isSelected ? 1 : (selectedReportId ? 0.35 : 0.75),
          weight:      isSelected ? 3 : 1.5,
        });
        (existing as L.CircleMarker).setRadius(markerRadius(r.damage_level, isSelected));
        // Only refresh popup HTML when it is NOT open — avoids destroying the
        // img DOM node (and the photo flash) while the user is viewing the card
        if (!existing.isPopupOpen()) {
          existing.setPopupContent(reportPopup(r));
        }
      } else {
        // Brand-new report — create marker from scratch
        const marker = L.circleMarker([lat, lon], {
          radius:      markerRadius(r.damage_level, isSelected),
          color:       isSelected ? "#fff" : DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
          fillColor:   DAMAGE_COLORS[r.damage_level] ?? DAMAGE_COLORS.unknown,
          fillOpacity: isSelected ? 1 : (selectedReportId ? 0.35 : 0.75),
          weight:      isSelected ? 3 : 1.5,
        })
          .bindPopup(reportPopup(r), { maxWidth: 260, autoPan: false })
          .addTo(reportLayer.current!);

        marker.on("click", () => {
          if (!mapRef.current) return;
          panToWithOffset(mapRef.current, lat, lon);
        });

        markerIndex.current.set(r.report_id, marker);
      }
    }

    // Auto-fit bounds on first load only (skip if a report is pre-selected from URL)
    if (!initialFit.current && !selectedReportId && withCoords.length > 0) {
      const latlngs = withCoords.map((r) => [r.coordinates![1], r.coordinates![0]] as [number, number]);
      mapRef.current.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40], maxZoom: 14 });
      initialFit.current = true;
    }

    // If a report was pre-selected (e.g. from ?report= URL param), fly to it now
    // that markers have been built. This handles the race where selectedReportId
    // is set before the REST fetch completes.
    // On subsequent poll refreshes (hasPositionedFor already matches) we only
    // re-open the popup — we do NOT fly again so the user's map position is kept.
    if (selectedReportId) {
      const selectedMarker = markerIndex.current.get(selectedReportId);
      const selectedReport = liveReports.find((r) => r.report_id === selectedReportId);
      if (selectedMarker && selectedReport?.coordinates) {
        if (hasPositionedFor.current !== selectedReportId) {
          // First time we have this marker — fly with offset
          const [lon, lat] = selectedReport.coordinates;
          flyToWithOffset(mapRef.current, lat, lon, Math.max(mapRef.current.getZoom(), 15));
          hasPositionedFor.current = selectedReportId;
        }
        selectedMarker.openPopup();
        initialFit.current = true; // prevent fitBounds from overriding
      }
    }
  }, [liveReports, lang]);

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

    // Fly to with offset so popup card has room above the marker
    if (report?.coordinates) {
      const [lon, lat] = report.coordinates;
      flyToWithOffset(mapRef.current, lat, lon, Math.max(mapRef.current.getZoom(), 15));
      hasPositionedFor.current = selectedReportId; // suppress poll-refresh re-fly
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

        /* AI assessment card */
        .pp-ai-card { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px;
          padding: 6px 8px; margin-top: 6px; font-size: 11px; color: #1e3a5f; }
        .pp-ai-header { display: flex; justify-content: space-between; align-items: center;
          margin-bottom: 5px; }
        .pp-ai-title { font-weight: 700; color: #1a56db; font-size: 11px; }
        .pp-ai-conf { font-size: 10px; color: #6b7280; background: #dbeafe;
          padding: 1px 5px; border-radius: 10px; }
        .pp-ai-row { margin: 3px 0; font-size: 11px; }
        .pp-ai-badge { display: inline-block; padding: 1px 6px; border-radius: 10px;
          font-size: 10px; font-weight: 600; }
        .pp-ai-match { background: #dcfce7; color: #166534; }
        .pp-ai-diff  { background: #fef9c3; color: #854d0e; }
        .pp-ai-hazard { color: #92400e; font-weight: 500; }
        .pp-ai-summary { font-style: italic; color: #374151; margin-top: 5px;
          padding-top: 4px; border-top: 1px solid #bfdbfe; font-size: 11px; }
        /* Intervention priority badges */
        .pp-priority { display: inline-block; padding: 1px 7px; border-radius: 10px;
          font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .4px; }
        .pp-pri-low  { background: #dcfce7; color: #166534; }
        .pp-pri-med  { background: #fef9c3; color: #854d0e; }
        .pp-pri-high { background: #ffedd5; color: #9a3412; }
        .pp-pri-crit { background: #fee2e2; color: #7f1d1d; }

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
