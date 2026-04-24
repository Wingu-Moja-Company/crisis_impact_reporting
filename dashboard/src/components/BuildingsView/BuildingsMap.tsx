import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { BuildingProperties } from "../../services/api";

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
  unknown:  "#888780",
};

function damageRadius(level: string, selected: boolean): number {
  const base = level === "complete" ? 13 : level === "partial" ? 10 : 7;
  return selected ? base + 4 : base;
}

function esc(s: string | null | undefined): string {
  return (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

interface Props {
  center: [number, number];
  buildings: GeoJSON.FeatureCollection | null;
  selectedBuildingId: string | null;
  onBuildingSelect: (id: string) => void;
}

export function BuildingsMap({ center, buildings, selectedBuildingId, onBuildingSelect }: Props) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const mapRef        = useRef<L.Map | null>(null);
  const layerRef      = useRef<L.LayerGroup | null>(null);
  // building_id → { marker, damage_level }
  const markerIndex   = useRef<Map<string, { marker: L.CircleMarker; level: string }>>(new Map());

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current).setView(center, 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(mapRef.current);
    layerRef.current = L.layerGroup().addTo(mapRef.current);
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  // Rebuild markers when buildings data changes
  useEffect(() => {
    if (!mapRef.current || !layerRef.current) return;
    layerRef.current.clearLayers();
    markerIndex.current.clear();
    if (!buildings) return;

    const points = buildings.features.filter((f) => f.geometry?.type === "Point");
    if (points.length === 0) return;

    for (const feature of points) {
      const props = feature.properties as BuildingProperties;
      const [lon, lat] = (feature.geometry as GeoJSON.Point).coordinates;
      const isSelected = props.building_id === selectedBuildingId;
      const color = DAMAGE_COLORS[props.current_damage_level ?? "unknown"] ?? DAMAGE_COLORS.unknown;

      const debrisHtml = props.requires_debris_clearing
        ? `<div class="bldg-popup-debris">&#9888;&#65039; Debris clearing required</div>` : "";

      const photoHtml = props.has_photo
        ? `<span class="bldg-popup-badge bldg-popup-badge--photo">&#128247; Photo</span>` : "";

      const tierHtml = props.submitter_tier === "verified"
        ? `<span class="bldg-popup-badge bldg-popup-badge--verified">&#10003; Verified</span>` : "";

      const marker = L.circleMarker([lat, lon], {
        radius:      damageRadius(props.current_damage_level ?? "unknown", isSelected),
        color:       isSelected ? "#fff" : color,
        fillColor:   color,
        fillOpacity: isSelected ? 1 : 0.82,
        weight:      isSelected ? 3 : 1.5,
      })
        .bindTooltip(
          `<strong>${esc(props.building_id)}</strong><br>${esc(props.current_damage_level ?? "unknown")} &middot; ${props.report_count ?? 0} report(s)${props.requires_debris_clearing ? "<br>&#9888; Debris" : ""}`,
          { sticky: true }
        )
        .bindPopup(`
          <div class="bldg-popup">
            <div class="bldg-popup-header bldg-popup-header--${esc(props.current_damage_level ?? "unknown")}">
              <strong>${esc(props.current_damage_level ?? "unknown")} damage</strong>
              <span>${props.report_count ?? 0} report(s)</span>
            </div>
            ${debrisHtml}
            <div class="bldg-popup-meta">
              ${photoHtml}${tierHtml}
            </div>
            <div class="bldg-popup-id">${esc(props.building_id)}</div>
          </div>
        `, { maxWidth: 220 })
        .on("click", () => onBuildingSelect(props.building_id))
        .addTo(layerRef.current!);

      markerIndex.current.set(props.building_id, { marker, level: props.current_damage_level ?? "unknown" });
    }

    if (!selectedBuildingId) {
      const latlngs = points.map((f) => {
        const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
        return [lat, lon] as [number, number];
      });
      mapRef.current.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40], maxZoom: 16 });
    }
  }, [buildings]);

  // Re-style on selection change, fly to selected
  useEffect(() => {
    for (const [id, { marker, level }] of markerIndex.current) {
      const isSelected = id === selectedBuildingId;
      const color = DAMAGE_COLORS[level] ?? DAMAGE_COLORS.unknown;
      marker.setStyle({
        color:       isSelected ? "#fff" : color,
        fillColor:   color,
        fillOpacity: isSelected ? 1 : 0.82,
        weight:      isSelected ? 3 : 1.5,
      });
      marker.setRadius(damageRadius(level, isSelected));
    }

    if (selectedBuildingId && mapRef.current && buildings) {
      const feature = buildings.features.find(
        (f) => (f.properties as BuildingProperties).building_id === selectedBuildingId
      );
      if (feature) {
        const [lon, lat] = (feature.geometry as GeoJSON.Point).coordinates;
        mapRef.current.flyTo([lat, lon], Math.max(mapRef.current.getZoom(), 15), { duration: 0.8 });
        markerIndex.current.get(selectedBuildingId)?.marker.openPopup();
      }
    }
  }, [selectedBuildingId]);

  return (
    <>
      <style>{`
        .bldg-popup { font-size: 13px; line-height: 1.45; min-width: 180px; }
        .bldg-popup-header { display: flex; justify-content: space-between; align-items: center;
          padding: 5px 8px; border-radius: 4px 4px 0 0; margin: -4px -4px 7px; font-size: 12px; }
        .bldg-popup-header--minimal  { background: #639922; color: #fff; }
        .bldg-popup-header--partial  { background: #BA7517; color: #fff; }
        .bldg-popup-header--complete { background: #E24B4A; color: #fff; }
        .bldg-popup-header--unknown  { background: #888780; color: #fff; }
        .bldg-popup-debris { background: #fff3cd; border: 1px solid #f59e0b; border-radius: 4px;
          padding: 3px 7px; font-size: 11px; font-weight: 700; color: #92400e; margin-bottom: 6px; }
        .bldg-popup-meta { display: flex; gap: 5px; margin-bottom: 5px; flex-wrap: wrap; }
        .bldg-popup-badge { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 10px; }
        .bldg-popup-badge--photo    { background: #dbeafe; color: #1e40af; }
        .bldg-popup-badge--verified { background: #dcfce7; color: #166534; }
        .bldg-popup-id { font-family: monospace; font-size: 10px; color: #aaa;
          border-top: 1px solid #f0f0f0; padding-top: 4px; margin-top: 4px; }
      `}</style>
      <div ref={containerRef} style={{ height: "100%", width: "100%" }} />
    </>
  );
}
