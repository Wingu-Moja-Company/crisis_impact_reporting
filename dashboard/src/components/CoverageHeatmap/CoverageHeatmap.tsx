import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { fetchReports } from "../../services/api";

interface Props {
  crisisEventId: string;
  center: [number, number];
  zoom?: number;
}

interface GridCell {
  lat: number;
  lon: number;
  count: number;
}

const GRID_DEGREES = 0.005; // ~500 m grid squares

function toGrid(lat: number, lon: number): [number, number] {
  return [
    Math.floor(lat / GRID_DEGREES) * GRID_DEGREES,
    Math.floor(lon / GRID_DEGREES) * GRID_DEGREES,
  ];
}

export function CoverageHeatmap({ crisisEventId, center, zoom = 13 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const heatLayerRef = useRef<L.LayerGroup | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(mapRef.current);
    heatLayerRef.current = L.layerGroup().addTo(mapRef.current);
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  async function refresh() {
    const collection = await fetchReports({ crisis_event_id: crisisEventId, limit: 5000 });
    const grid = new Map<string, GridCell>();

    for (const feature of collection.features) {
      const coords = feature.geometry as GeoJSON.Point;
      if (!coords?.coordinates) continue;
      const [lon, lat] = coords.coordinates;
      const [gLat, gLon] = toGrid(lat, lon);
      const key = `${gLat},${gLon}`;
      const cell = grid.get(key) ?? { lat: gLat, lon: gLon, count: 0 };
      cell.count++;
      grid.set(key, cell);
    }

    heatLayerRef.current?.clearLayers();
    for (const cell of grid.values()) {
      const opacity = Math.min(0.8, 0.2 + cell.count * 0.1);
      L.rectangle(
        [[cell.lat, cell.lon], [cell.lat + GRID_DEGREES, cell.lon + GRID_DEGREES]],
        { color: "#1a56db", weight: 0, fillOpacity: opacity }
      )
        .bindTooltip(`${cell.count} report(s)`)
        .addTo(heatLayerRef.current!);
    }
    setLastRefresh(new Date());
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 60_000);
    return () => clearInterval(interval);
  }, [crisisEventId]);

  return (
    <div className="coverage-heatmap-wrapper">
      <div ref={containerRef} style={{ height: "100%", width: "100%" }} />
      {lastRefresh && (
        <p className="heatmap-refresh">Last updated: {lastRefresh.toLocaleTimeString()}</p>
      )}
    </div>
  );
}
