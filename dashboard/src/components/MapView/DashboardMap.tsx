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

export function DashboardMap({
  center, zoom = 14, footprints, liveReports, selectedBuildingId, onBuildingSelect,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const footprintLayerRef = useRef<L.GeoJSON | null>(null);
  const liveLayerRef = useRef<L.LayerGroup | null>(null);

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(mapRef.current);
    liveLayerRef.current = L.layerGroup().addTo(mapRef.current);
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  // Re-render building footprint polygons when footprints or selection changes
  useEffect(() => {
    if (!mapRef.current || !footprints) return;
    footprintLayerRef.current?.remove();
    footprintLayerRef.current = L.geoJSON(
      { type: "FeatureCollection", features: footprints } as GeoJSON.FeatureCollection,
      {
        style: (f) => ({
          color: DAMAGE_COLORS[f?.properties?.current_damage_level ?? "unknown"],
          weight: f?.properties?.building_id === selectedBuildingId ? 3 : 1,
          fillOpacity: 0.5,
        }),
        onEachFeature: (f, layer) => {
          const { building_id, current_damage_level, report_count } = (f as BuildingFeature).properties;
          layer.on("click", () => onBuildingSelect(building_id));
          layer.bindTooltip(
            `${current_damage_level ?? "No reports"} | ${report_count ?? 0} report(s)`
          );
        },
      }
    ).addTo(mapRef.current);
  }, [footprints, selectedBuildingId]);

  // Add circle markers for incoming live reports
  useEffect(() => {
    if (!liveLayerRef.current || liveReports.length === 0) return;
    const latest = liveReports[0];
    if (!latest.coordinates) return;
    const [lon, lat] = latest.coordinates;
    L.circleMarker([lat, lon], {
      radius: 6,
      color: DAMAGE_COLORS[latest.damage_level ?? "unknown"],
      fillOpacity: 0.8,
    })
      .bindTooltip(`${latest.damage_level} — ${latest.channel}`)
      .addTo(liveLayerRef.current);
  }, [liveReports]);

  return <div ref={containerRef} className="dashboard-map" style={{ height: "100%", width: "100%" }} />;
}
