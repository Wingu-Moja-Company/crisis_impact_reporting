import { useTranslation } from "react-i18next";
import type { BuildingSummary } from "../../services/api";

const DAMAGE_COLOR: Record<string, string> = {
  complete: "#E24B4A",
  partial:  "#BA7517",
  minimal:  "#639922",
};

const PRIORITY_CLASS: Record<string, string> = {
  critical: "bldg-pri-critical",
  high:     "bldg-pri-high",
  medium:   "bldg-pri-medium",
};

interface Props {
  summary: BuildingSummary | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export function BuildingsSummaryPanel({ summary, loading, error, onRefresh }: Props) {
  const { t } = useTranslation();

  if (loading) return <div className="feed-empty">{t("buildings.loading")}</div>;
  if (error)   return <div className="feed-empty" style={{ color: "var(--red)" }}>{error}</div>;
  if (!summary) return <div className="feed-empty">{t("buildings.no_data")}</div>;

  return (
    <div className="bldg-summary">
      <div className="bldg-summary-header">
        <span className="bldg-summary-title">{t("buildings.overview_title")}</span>
        <button className="bldg-refresh-btn" onClick={onRefresh} title={t("admin.refresh")}>↺</button>
      </div>

      <div className="bldg-kpi-row">
        <div className="bldg-kpi">
          <span className="bldg-kpi-value">{summary.total_buildings}</span>
          <span className="bldg-kpi-label">{t("buildings.total")}</span>
        </div>
        <div className="bldg-kpi bldg-kpi--debris">
          <span className="bldg-kpi-value">{summary.debris_clearing_required}</span>
          <span className="bldg-kpi-label">{t("buildings.debris_required")}</span>
        </div>
      </div>

      <ul className="bldg-damage-list">
        {summary.by_damage_level.map((row) => (
          <li key={row.damage_level} className="bldg-damage-row">
            <span
              className="bldg-damage-swatch"
              style={{ background: DAMAGE_COLOR[row.damage_level] ?? "#888" }}
            />
            <span className="bldg-damage-name">
              {t(`export.${row.damage_level}`, { defaultValue: row.damage_level })}
            </span>
            <span className="bldg-damage-count">{row.count}</span>
            <span className={`bldg-priority-badge ${PRIORITY_CLASS[row.intervention_priority] ?? ""}`}>
              {t(`buildings.priority_${row.intervention_priority}`, { defaultValue: row.intervention_priority })}
            </span>
          </li>
        ))}
      </ul>

      <div className="bldg-legend">
        <div className="bldg-legend-title">{t("buildings.intervention_label")}</div>
        {[
          { key: "critical", cls: "bldg-pri-critical" },
          { key: "high",     cls: "bldg-pri-high"     },
          { key: "medium",   cls: "bldg-pri-medium"   },
        ].map(({ key, cls }) => (
          <div key={key} className="bldg-legend-row">
            <span className={`bldg-priority-badge ${cls}`}>
              {t(`buildings.priority_${key}`, { defaultValue: key })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
