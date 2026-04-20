import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useTranslation } from "../../hooks/useTranslation";

interface BuildingFeature {
  type: "Feature";
  geometry: { type: "Polygon"; coordinates: number[][][] };
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
  selectedBuildingId?: string | null;
  onBuildingSelect?: (buildingId: string) => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
  unknown:  "#888780",
};

function getDamageColor(level?: string) {
  return DAMAGE_COLORS[level ?? "unknown"] ?? DAMAGE_COLORS.unknown;
}

export function MapView({ center, zoom = 15, footprints, selectedBuildingId, onBuildingSelect }: Props) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const footprintLayerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    mapRef.current = L.map(containerRef.current).setView(center, zoom);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(mapRef.current);

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !footprints) return;

    footprintLayerRef.current?.remove();

    footprintLayerRef.current = L.geoJSON(
      { type: "FeatureCollection", features: footprints } as GeoJSON.FeatureCollection,
      {
        style: (feature) => ({
          color: getDamageColor(feature?.properties?.current_damage_level),
          weight: feature?.properties?.building_id === selectedBuildingId ? 3 : 1,
          fillOpacity: 0.5,
        }),
        onEachFeature: (feature, layer) => {
          const props = (feature as BuildingFeature).properties;
          layer.on("click", () => onBuildingSelect?.(props.building_id));
          layer.bindTooltip(
            `${t(`map.damage_${props.current_damage_level ?? "unknown"}`, { defaultValue: t("map.no_reports") })} | ${props.report_count ?? 0} reports`
          );
        },
      }
    ).addTo(mapRef.current);
  }, [footprints, selectedBuildingId]);

  return <div ref={containerRef} className="map-view" style={{ height: "100%", width: "100%" }} />;
}
