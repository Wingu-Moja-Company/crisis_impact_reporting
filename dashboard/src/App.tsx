import { useState } from "react";
import { DashboardMap } from "./components/MapView/DashboardMap";
import { CoverageHeatmap } from "./components/CoverageHeatmap/CoverageHeatmap";
import { IncidentFeed } from "./components/IncidentFeed/IncidentFeed";
import { BuildingHistory } from "./components/BuildingHistory/BuildingHistory";
import { ExportPanel } from "./components/ExportPanel/ExportPanel";
import { StatsCards } from "./components/StatsCards/StatsCards";
import { AdminPanel } from "./components/AdminPanel/AdminPanel";
import { useLiveReports } from "./hooks/useLiveReports";

const DEFAULT_CRISIS_ID = import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev";
const MAP_CENTER: [number, number] = [-1.2577, 36.8614]; // Nairobi default

/** URL param ?crisis_event_id= takes priority, so the page survives refresh. */
function getCrisisIdFromUrl(): string {
  try {
    const param = new URLSearchParams(window.location.search).get("crisis_event_id");
    if (param?.trim()) return param.trim();
  } catch { /* ignore */ }
  return DEFAULT_CRISIS_ID;
}

type View = "map" | "heatmap";

/** Read ?report= from the URL on first load so Telegram links auto-select. */
function getReportFromUrl(): string | null {
  try {
    return new URLSearchParams(window.location.search).get("report");
  } catch {
    return null;
  }
}

export default function App() {
  const [crisisEventId, setCrisisEventId]       = useState(getCrisisIdFromUrl);
  const [view, setView]                         = useState<View>("map");
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedReport, setSelectedReport]     = useState<string | null>(getReportFromUrl);
  const [showExport, setShowExport]             = useState(false);
  const [showAdmin, setShowAdmin]               = useState(false);
  const [drawerOpen, setDrawerOpen]             = useState(false);

  const { reports: liveReports, connected, lastFetched } = useLiveReports(crisisEventId);

  function handleReportSelect(reportId: string) {
    setSelectedReport(reportId);
    setView("map");
    setDrawerOpen(false);
  }

  function handleBuildingSelect(buildingId: string) {
    setSelectedBuilding(buildingId);
    setSelectedReport(null);
  }

  function handleSwitchCrisis(id: string) {
    setCrisisEventId(id);
    setSelectedBuilding(null);
    setSelectedReport(null);
    setShowExport(false);
    // Persist to URL so refresh lands on the same crisis
    const url = new URL(window.location.href);
    url.searchParams.set("crisis_event_id", id);
    window.history.pushState({}, "", url.toString());
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Crisis Damage Dashboard</h1>
        <span className="crisis-id">{crisisEventId}</span>
        <nav>
          <button className={view === "map" ? "active" : ""} onClick={() => setView("map")}>Map</button>
          <button className={view === "heatmap" ? "active" : ""} onClick={() => setView("heatmap")}>Coverage</button>
          <button onClick={() => setShowExport((s) => !s)}>Export</button>
          <button
            className="admin-btn"
            onClick={() => setShowAdmin(true)}
            title="Admin — manage crisis events"
          >
            ⚙️
          </button>
        </nav>
      </header>

      <StatsCards
        crisisEventId={crisisEventId}
        liveCount={liveReports.length}
        wsConnected={connected}
        lastFetched={lastFetched}
      />

      <div className="dashboard-body">
        {drawerOpen && (
          <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />
        )}

        <aside className={`sidebar${drawerOpen ? " sidebar--open" : ""}`}>
          <div className="sidebar-handle">
            <span className="sidebar-handle-label">
              Reports ({liveReports.length})
            </span>
            <button
              className="sidebar-close-btn"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close panel"
            >✕</button>
          </div>

          <IncidentFeed
            reports={liveReports}
            selectedReportId={selectedReport}
            onSelect={handleReportSelect}
          />
        </aside>

        <main className="map-container">
          {view === "map" ? (
            <DashboardMap
              center={MAP_CENTER}
              liveReports={liveReports}
              selectedBuildingId={selectedBuilding}
              selectedReportId={selectedReport}
              onBuildingSelect={handleBuildingSelect}
            />
          ) : (
            <CoverageHeatmap crisisEventId={crisisEventId} center={MAP_CENTER} />
          )}

          <button
            className="feed-fab"
            onClick={() => setDrawerOpen((o) => !o)}
            aria-label="Toggle incident feed"
          >
            📋 {liveReports.length} Reports
          </button>
        </main>

        {selectedBuilding && (
          <BuildingHistory
            buildingId={selectedBuilding}
            onClose={() => setSelectedBuilding(null)}
          />
        )}
      </div>

      {showExport && <ExportPanel crisisEventId={crisisEventId} />}

      {showAdmin && (
        <AdminPanel
          onClose={() => setShowAdmin(false)}
          onSwitchCrisis={handleSwitchCrisis}
          activeCrisisId={crisisEventId}
        />
      )}
    </div>
  );
}
