import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchBuildingHistory, type BuildingVersion } from "../../services/api";

interface Props {
  buildingId: string;
  onClose: () => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
};

export function BuildingHistory({ buildingId, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const [history, setHistory] = useState<BuildingVersion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchBuildingHistory(buildingId)
      .then(setHistory)
      .finally(() => setLoading(false));
  }, [buildingId]);

  return (
    <div className="building-history-panel">
      <div className="panel-header">
        <h3>{t("building.title", { id: buildingId })}</h3>
        <button onClick={onClose}>✕</button>
      </div>

      {loading && <p>{t("building.loading")}</p>}

      {!loading && history.length === 0 && <p>{t("building.no_reports")}</p>}

      {!loading && history.length > 0 && (
        <ol className="version-timeline">
          {history.map((v) => (
            <li key={v.id} className="version-entry">
              <span
                className="version-dot"
                style={{ background: DAMAGE_COLORS[v.damage_level] ?? "#888" }}
              />
              <div className="version-detail">
                <strong>{v.damage_level}</strong>
                <span className="version-meta">
                  {new Date(v.submitted_at).toLocaleString(i18n.language)} · {v.submitter_tier}
                </span>
                <span className="version-report-id">{v.report_id}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
