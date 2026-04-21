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

const DAMAGE_GRADE: Record<string, string> = {
  minimal:  "Grade 1",
  partial:  "Grade 2",
  complete: "Grade 3",
};

const CHANNEL_ICON: Record<string, string> = {
  telegram: "📱", pwa: "🌐", sms: "💬", api: "🔌",
};

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)    return `${diff}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
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
            {/* Row 1: damage level + grade + debris flag + time */}
            <div className="feed-row">
              <span className="feed-level" style={{ color }}>
                {r.damage_level.toUpperCase()}
              </span>
              {grade && <span className="feed-grade">{grade}</span>}
              {r.requires_debris_clearing && (
                <span className="feed-debris">⚠ Debris</span>
              )}
              <span className="feed-time">{timeAgo(r.submitted_at)}</span>
            </div>

            {/* Row 2: photo + body */}
            <div className="feed-body">
              <div className="feed-text">
                {/* Infra + crisis type */}
                {(r.infrastructure_types?.length > 0 || r.crisis_nature) && (
                  <div className="feed-infra">
                    {r.infrastructure_types.join(", ")}
                    {r.infrastructure_types.length > 0 && r.crisis_nature && " · "}
                    {r.crisis_nature}
                  </div>
                )}

                {/* Location hint */}
                {(r.what3words || r.location_description) && (
                  <div className="feed-location">
                    📍 {r.what3words
                      ? r.what3words.replace(/^\/+/, "")   // strip any leading slashes
                      : r.location_description}
                  </div>
                )}

                {/* Description preview */}
                {r.description_en && (
                  <div className="feed-desc">
                    {r.description_en.slice(0, 72)}
                    {r.description_en.length > 72 ? "…" : ""}
                  </div>
                )}

                {/* Channel + tier */}
                <div className="feed-meta-row">
                  <span>{chanIcon} {r.channel}</span>
                  {r.submitter_tier === "verified" && (
                    <span className="feed-verified">✓ Verified</span>
                  )}
                  {r.ai_vision_confidence != null && (
                    <span className="feed-ai">
                      AI {Math.round(r.ai_vision_confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>

              {/* Photo thumbnail */}
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
