import { useState, useEffect } from "react";
import { useStats } from "../../hooks/useStats";

const POLL_INTERVAL_S = 30;

interface Props {
  crisisEventId: string;
  liveCount: number;
  wsConnected: boolean;
  lastFetched: number | null;
}

function PollCountdown({ lastFetched }: { lastFetched: number | null }) {
  const [secs, setSecs] = useState<number>(POLL_INTERVAL_S);

  useEffect(() => {
    if (lastFetched === null) return;
    // Recalculate immediately when lastFetched changes
    const tick = () => {
      const elapsed = Math.floor((Date.now() - lastFetched) / 1000);
      setSecs(Math.max(0, POLL_INTERVAL_S - elapsed));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lastFetched]);

  if (lastFetched === null) return <span className="poll-countdown">—</span>;
  return <span className="poll-countdown" title="Seconds until next refresh">↻ {secs}s</span>;
}

const LEVEL_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
};

export function StatsCards({ crisisEventId, liveCount, wsConnected, lastFetched }: Props) {
  const stats = useStats(crisisEventId);

  return (
    <div className="stats-cards">
      <div className="stat-card">
        <span className="stat-value">{stats?.total_reports ?? "—"}</span>
        <span className="stat-label">Total reports</span>
      </div>

      {["minimal", "partial", "complete"].map((lvl) => (
        <div key={lvl} className="stat-card" style={{ borderTop: `4px solid ${LEVEL_COLORS[lvl]}` }}>
          <span className="stat-value">{stats?.by_damage_level[lvl] ?? 0}</span>
          <span className="stat-label">{lvl.charAt(0).toUpperCase() + lvl.slice(1)}</span>
        </div>
      ))}

      <div className="stat-card">
        <span className="stat-value">{liveCount}</span>
        <span className="stat-label">
          {wsConnected ? (
            <>Live feed <span className="ws-dot connected" title="WebSocket connected" /></>
          ) : (
            <>Polling <PollCountdown lastFetched={lastFetched} /></>
          )}
        </span>
      </div>
    </div>
  );
}
