import type { LiveReport } from "../../hooks/useLiveReports";

interface Props {
  reports: LiveReport[];
  onSelect: (buildingId: string) => void;
}

const DAMAGE_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
};

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function IncidentFeed({ reports, onSelect }: Props) {
  if (reports.length === 0) {
    return <p className="feed-empty">No live reports yet.</p>;
  }

  return (
    <ul className="incident-feed">
      {reports.map((r) => (
        <li
          key={r.report_id}
          className="feed-item"
          style={{ borderLeft: `4px solid ${DAMAGE_COLORS[r.damage_level] ?? "#888"}` }}
          onClick={() => r.building_id && onSelect(r.building_id)}
        >
          <span className="feed-level">{r.damage_level}</span>
          <span className="feed-channel">{r.channel}</span>
          <span className="feed-time">{timeAgo(r.submitted_at)}</span>
        </li>
      ))}
    </ul>
  );
}
