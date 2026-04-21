import { useState } from "react";
import { buildExportUrl } from "../../services/api";

interface Props {
  crisisEventId: string;
}

export function ExportPanel({ crisisEventId }: Props) {
  const [damageFilter, setDamageFilter] = useState("");
  const [infraFilter, setInfraFilter] = useState("");
  const [sinceFilter, setSinceFilter] = useState("");

  function filters() {
    return Object.fromEntries(
      Object.entries({ damage_level: damageFilter, infra_type: infraFilter, since: sinceFilter })
        .filter(([, v]) => v !== "")
    );
  }

  const [downloading, setDownloading] = useState<string | null>(null);

  async function download(format: "geojson" | "csv" | "shapefile") {
    const url = buildExportUrl(crisisEventId, format, filters());
    setDownloading(format);
    try {
      // Fetch via JS so the response is same-origin as a blob: URL.
      // Direct cross-origin <a download> links are silently ignored by browsers.
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `${crisisEventId}.${format === "shapefile" ? "zip" : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Export failed:", err);
      alert(`Export failed: ${err}`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="export-panel">
      <h3>Export data</h3>

      <div className="export-filters">
        <label>
          Damage level
          <select value={damageFilter} onChange={(e) => setDamageFilter(e.target.value)}>
            <option value="">All</option>
            <option value="minimal">Minimal</option>
            <option value="partial">Partial</option>
            <option value="complete">Complete</option>
          </select>
        </label>

        <label>
          Infrastructure type
          <select value={infraFilter} onChange={(e) => setInfraFilter(e.target.value)}>
            <option value="">All</option>
            {["residential","commercial","government","utility","transport","community","public_space","other"]
              .map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>

        <label>
          Since
          <input
            type="datetime-local"
            value={sinceFilter}
            onChange={(e) => setSinceFilter(e.target.value ? new Date(e.target.value).toISOString() : "")}
          />
        </label>
      </div>

      <div className="export-buttons">
        <button onClick={() => download("geojson")} disabled={!!downloading}>
          {downloading === "geojson" ? "Downloading…" : "⬇ GeoJSON (QGIS / ArcGIS)"}
        </button>
        <button onClick={() => download("csv")} disabled={!!downloading}>
          {downloading === "csv" ? "Downloading…" : "⬇ CSV (Excel / Sheets)"}
        </button>
        <button onClick={() => download("shapefile")} disabled={!!downloading}>
          {downloading === "shapefile" ? "Downloading…" : "⬇ Shapefile (.zip)"}
        </button>
      </div>
    </div>
  );
}
