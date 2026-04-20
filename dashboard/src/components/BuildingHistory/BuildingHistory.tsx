import { useEffect, useState } from "react";
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
        <h3>Building {buildingId}</h3>
        <button onClick={onClose}>✕</button>
      </div>

      {loading && <p>Loading history…</p>}

      {!loading && history.length === 0 && <p>No reports for this building.</p>}

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
                  {new Date(v.submitted_at).toLocaleString()} · {v.submitter_tier}
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
