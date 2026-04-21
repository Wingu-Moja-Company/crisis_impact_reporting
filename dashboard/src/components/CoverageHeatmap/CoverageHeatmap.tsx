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
  counts: Record<string, number>; // damage_level → count
}

const GRID_DEGREES = 0.005; // ~500 m grid squares

const DAMAGE_COLORS: Record<string, string> = {
  complete: "#E24B4A",
  partial:  "#BA7517",
  minimal:  "#639922",
  unknown:  "#888780",
};

/** Return the dominant (highest severity) damage level in a cell */
function dominantLevel(counts: Record<string, number>): string {
  for (const level of ["complete", "partial", "minimal"]) {
    if ((counts[level] ?? 0) > 0) return level;
  }
  return "unknown";
}

function toGridKey(lat: number, lon: number): string {
  const gLat = Math.floor(lat / GRID_DEGREES) * GRID_DEGREES;
  const gLon = Math.floor(lon / GRID_DEGREES) * GRID_DEGREES;
  return `${gLat.toFixed(4)},${gLon.toFixed(4)}`;
}

export function CoverageHeatmap({ crisisEventId, center, zoom = 13 }: Props) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const mapRef        = useRef<L.Map | null>(null);
  const heatLayerRef  = useRef<L.LayerGroup | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [cellCount,   setCellCount]   = useState(0);

  // ── Init map ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(mapRef.current);
    heatLayerRef.current = L.layerGroup().addTo(mapRef.current);
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  // ── Fetch + render grid ────────────────────────────────────────────────────
  async function refresh() {
    if (!heatLayerRef.current) return;
    try {
      const collection = await fetchReports({
        crisis_event_id: crisisEventId,
        limit: 5000,
        format: "geojson",
      } as Parameters<typeof fetchReports>[0]);

      const grid = new Map<string, GridCell>();

      for (const feature of collection.features) {
        const geom = feature.geometry as GeoJSON.Point;
        if (!geom?.coordinates) continue;
        const [lon, lat] = geom.coordinates;
        const key = toGridKey(lat, lon);
        const gLat = Math.floor(lat / GRID_DEGREES) * GRID_DEGREES;
        const gLon = Math.floor(lon / GRID_DEGREES) * GRID_DEGREES;

        const cell = grid.get(key) ?? { lat: gLat, lon: gLon, counts: {} };
        const level = String((feature.properties as Record<string,unknown>)?.damage_level ?? "unknown");
        cell.counts[level] = (cell.counts[level] ?? 0) + 1;
        grid.set(key, cell);
      }

      heatLayerRef.current.clearLayers();

      for (const cell of grid.values()) {
        const total   = Object.values(cell.counts).reduce((a, b) => a + b, 0);
        const level   = dominantLevel(cell.counts);
        const color   = DAMAGE_COLORS[level];
        const opacity = Math.min(0.85, 0.25 + total * 0.12);

        const breakdown = Object.entries(cell.counts)
          .map(([l, n]) => `${l}: ${n}`)
          .join(", ");

        L.rectangle(
          [[cell.lat, cell.lon], [cell.lat + GRID_DEGREES, cell.lon + GRID_DEGREES]],
          { color, weight: 0.5, fillColor: color, fillOpacity: opacity }
        )
          .bindTooltip(`${total} report(s) — ${breakdown}`)
          .addTo(heatLayerRef.current!);
      }

      setCellCount(grid.size);
      setLastRefresh(new Date());
    } catch {
      // non-critical — leave existing grid in place
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 60_000);
    return () => clearInterval(interval);
  }, [crisisEventId]);

  return (
    <div style={{ position: "relative", height: "100%", width: "100%" }}>
      <div ref={containerRef} style={{ height: "100%", width: "100%" }} />

      {/* Legend */}
      <div style={{
        position: "absolute", bottom: 28, right: 10, zIndex: 1000,
        background: "rgba(255,255,255,0.92)", borderRadius: 6, padding: "8px 12px",
        fontSize: 12, boxShadow: "0 1px 5px rgba(0,0,0,0.2)", lineHeight: 1.8,
      }}>
        <strong style={{ display: "block", marginBottom: 4 }}>Damage density</strong>
        {[["complete","#E24B4A","Complete"],["partial","#BA7517","Partial"],["minimal","#639922","Minimal"]]
          .map(([,color,label]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 14, height: 14, background: color, display: "inline-block", borderRadius: 2 }} />
              {label}
            </div>
          ))}
        <div style={{ marginTop: 4, color: "#666" }}>
          {cellCount} grid {cellCount === 1 ? "cell" : "cells"} · darker = more reports
        </div>
      </div>

      {lastRefresh && (
        <p style={{
          position: "absolute", bottom: 6, left: "50%", transform: "translateX(-50%)",
          zIndex: 1000, margin: 0, fontSize: 11, color: "#666",
          background: "rgba(255,255,255,0.8)", padding: "2px 8px", borderRadius: 4,
        }}>
          Updated {lastRefresh.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
