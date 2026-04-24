import { useState } from "react";
import { useTranslation } from "react-i18next";
import { buildExportUrl } from "../../services/api";

const EXPORT_API_KEY = import.meta.env.VITE_EXPORT_API_KEY ?? "";

interface Props {
  crisisEventId: string;
}

export function ExportPanel({ crisisEventId }: Props) {
  const { t } = useTranslation();
  const [damageFilter, setDamageFilter] = useState("");
  const [infraFilter, setInfraFilter] = useState("");
  const [sinceFilter, setSinceFilter] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);

  function filters() {
    return Object.fromEntries(
      Object.entries({ damage_level: damageFilter, infra_type: infraFilter, since: sinceFilter })
        .filter(([, v]) => v !== "")
    );
  }

  async function download(format: "geojson" | "csv" | "shapefile") {
    const url = buildExportUrl(crisisEventId, format, filters());
    setDownloading(format);
    try {
      const res = await fetch(url, EXPORT_API_KEY ? { headers: { "X-API-Key": EXPORT_API_KEY } } : {});
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
      alert(t("export.failed", { error: String(err) }));
    } finally {
      setDownloading(null);
    }
  }

  const infra = ["residential","commercial","government","utility","transport","community","public_space","other"];

  return (
    <div className="export-panel">
      <h3>{t("export.title")}</h3>

      <div className="export-filters">
        <label>
          {t("export.damage_level")}
          <select value={damageFilter} onChange={(e) => setDamageFilter(e.target.value)}>
            <option value="">{t("export.all")}</option>
            <option value="minimal">{t("export.minimal")}</option>
            <option value="partial">{t("export.partial")}</option>
            <option value="complete">{t("export.complete")}</option>
          </select>
        </label>

        <label>
          {t("export.infra_type")}
          <select value={infraFilter} onChange={(e) => setInfraFilter(e.target.value)}>
            <option value="">{t("export.all")}</option>
            {infra.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </label>

        <label>
          {t("export.since")}
          <input
            type="datetime-local"
            value={sinceFilter}
            onChange={(e) => setSinceFilter(e.target.value ? new Date(e.target.value).toISOString() : "")}
          />
        </label>
      </div>

      <div className="export-buttons">
        <button onClick={() => download("geojson")} disabled={!!downloading}>
          {downloading === "geojson" ? t("export.downloading") : t("export.geojson")}
        </button>
        <button onClick={() => download("csv")} disabled={!!downloading}>
          {downloading === "csv" ? t("export.downloading") : t("export.csv")}
        </button>
        <button onClick={() => download("shapefile")} disabled={!!downloading}>
          {downloading === "shapefile" ? t("export.downloading") : t("export.shapefile")}
        </button>
      </div>
    </div>
  );
}
