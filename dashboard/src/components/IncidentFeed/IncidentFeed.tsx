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

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function IncidentFeed({ reports, selectedReportId, onSelect }: Props) {
  if (reports.length === 0) {
    return (
      <div className="feed-empty">
        <p>Loading reports…</p>
      </div>
    );
  }

  return (
    <ul className="incident-feed">
      {reports.map((r) => (
        <li
          key={r.report_id}
          className={`feed-item${r.report_id === selectedReportId ? " feed-item--selected" : ""}`}
          style={{ borderLeft: `${r.report_id === selectedReportId ? "7px" : "4px"} solid ${DAMAGE_COLORS[r.damage_level] ?? "#888"}` }}
          onClick={() => onSelect(r.report_id)}
        >
          <div className="feed-row">
            <span className="feed-level">{r.damage_level}</span>
            <span className="feed-channel">{r.channel}</span>
            <span className="feed-time">{timeAgo(r.submitted_at)}</span>
          </div>
          {r.infrastructure_types?.length > 0 && (
            <div className="feed-infra">{r.infrastructure_types.join(", ")}</div>
          )}
          {r.description_en && (
            <div className="feed-desc">{r.description_en.slice(0, 80)}{r.description_en.length > 80 ? "…" : ""}</div>
          )}
        </li>
      ))}
    </ul>
  );
}
