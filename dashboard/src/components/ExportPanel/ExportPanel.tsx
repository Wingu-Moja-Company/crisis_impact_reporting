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

  function download(format: "geojson" | "csv" | "shapefile") {
    const url = buildExportUrl(crisisEventId, format, filters());
    const a = document.createElement("a");
    a.href = url;
    a.download = `${crisisEventId}.${format === "shapefile" ? "zip" : format}`;
    a.click();
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
        <button onClick={() => download("geojson")}>Download GeoJSON</button>
        <button onClick={() => download("csv")}>Download CSV</button>
        <button onClick={() => download("shapefile")}>Download Shapefile</button>
      </div>
    </div>
  );
}
