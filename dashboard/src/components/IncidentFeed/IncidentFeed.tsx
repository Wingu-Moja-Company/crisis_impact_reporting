import { useTranslation } from "react-i18next";
import type { LiveReport } from "../../hooks/useLiveReports";

interface Props {
  reports: LiveReport[];
  selectedReportId: string | null;
  onSelect: (reportId: string) => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
};

const CHANNEL_ICON: Record<string, string> = {
  telegram: "📱", pwa: "🌐", sms: "💬", api: "🔌",
};

export function IncidentFeed({ reports, selectedReportId, onSelect }: Props) {
  const { t } = useTranslation();

  function timeAgo(iso: string): string {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60)    return t("feed.seconds_ago", { n: diff });
    if (diff < 3600)  return t("feed.minutes_ago", { n: Math.floor(diff / 60) });
    if (diff < 86400) return t("feed.hours_ago",   { n: Math.floor(diff / 3600) });
    return t("feed.days_ago", { n: Math.floor(diff / 86400) });
  }

  const DAMAGE_GRADE: Record<string, string> = {
    minimal:  t("feed.grade_1"),
    partial:  t("feed.grade_2"),
    complete: t("feed.grade_3"),
  };

  if (reports.length === 0) {
    return (
      <div className="feed-empty">
        <p>{t("feed.loading")}</p>
      </div>
    );
  }

  return (
    <ul className="incident-feed">
      {reports.map((r) => {
        const selected = r.report_id === selectedReportId;
        const color = DAMAGE_COLORS[r.damage_level] ?? "#888";
        const grade = DAMAGE_GRADE[r.damage_level] ?? "";
        const chanIcon = CHANNEL_ICON[r.channel] ?? "📡";

        return (
          <li
            key={r.report_id}
            className={`feed-item${selected ? " feed-item--selected" : ""}`}
            style={{ borderLeft: `${selected ? 7 : 4}px solid ${color}` }}
            onClick={() => onSelect(r.report_id)}
          >
            <div className="feed-row">
              <span className="feed-level" style={{ color }}>
                {t(`stats.${r.damage_level}`, r.damage_level).toUpperCase()}
              </span>
              {grade && <span className="feed-grade">{grade}</span>}
              {r.requires_debris_clearing && (
                <span className="feed-debris">⚠ {t("feed.debris")}</span>
              )}
              <span className="feed-time">{timeAgo(r.submitted_at)}</span>
            </div>

            <div className="feed-body">
              <div className="feed-text">
                {(r.infrastructure_types?.length > 0 || r.crisis_nature) && (
                  <div className="feed-infra">
                    {r.infrastructure_types.map((it) => t(`infra.${it}`, it)).join(", ")}
                    {r.infrastructure_types.length > 0 && r.crisis_nature && " · "}
                    {r.crisis_nature ? t(`nature.${r.crisis_nature}`, r.crisis_nature) : ""}
                  </div>
                )}

                {(r.what3words || r.location_description) && (
                  <div className="feed-location">
                    📍 {r.what3words
                      ? r.what3words.replace(/^\/+/, "")
                      : r.location_description}
                  </div>
                )}

                {r.description_en && (
                  <div className="feed-desc">
                    {r.description_en.slice(0, 72)}
                    {r.description_en.length > 72 ? "…" : ""}
                  </div>
                )}

                <div className="feed-meta-row">
                  <span>{chanIcon} {r.channel}</span>
                  {r.submitter_tier === "verified" && (
                    <span className="feed-verified">✓ {t("feed.verified")}</span>
                  )}
                </div>
              </div>

              {r.photo_url && (
                <img
                  src={r.photo_url}
                  alt="Damage"
                  className="feed-thumb"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
