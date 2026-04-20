import { useStats } from "../../hooks/useStats";

interface Props {
  crisisEventId: string;
  liveCount: number;
  wsConnected: boolean;
}

const LEVEL_COLORS: Record<string, string> = {
  minimal:  "#639922",
  partial:  "#BA7517",
  complete: "#E24B4A",
};

export function StatsCards({ crisisEventId, liveCount, wsConnected }: Props) {
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
          Live feed{" "}
          <span className={`ws-dot ${wsConnected ? "connected" : "disconnected"}`} title={wsConnected ? "Connected" : "Disconnected"} />
        </span>
      </div>
    </div>
  );
}
