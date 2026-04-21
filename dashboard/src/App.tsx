import { useState } from "react";
import { DashboardMap } from "./components/MapView/DashboardMap";
import { CoverageHeatmap } from "./components/CoverageHeatmap/CoverageHeatmap";
import { IncidentFeed } from "./components/IncidentFeed/IncidentFeed";
import { BuildingHistory } from "./components/BuildingHistory/BuildingHistory";
import { ExportPanel } from "./components/ExportPanel/ExportPanel";
import { StatsCards } from "./components/StatsCards/StatsCards";
import { useLiveReports } from "./hooks/useLiveReports";

const CRISIS_EVENT_ID = import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev";
const MAP_CENTER: [number, number] = [-1.2577, 36.8614]; // Nairobi default

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
  const [view, setView]                         = useState<View>("map");
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedReport, setSelectedReport]     = useState<string | null>(getReportFromUrl);
  const [showExport, setShowExport]             = useState(false);
  const [drawerOpen, setDrawerOpen]             = useState(false);

  const { reports: liveReports, connected } = useLiveReports(CRISIS_EVENT_ID);

  function handleReportSelect(reportId: string) {
    setSelectedReport(reportId);
    setView("map");
    setDrawerOpen(false); // close drawer after selecting on mobile
  }

  function handleBuildingSelect(buildingId: string) {
    setSelectedBuilding(buildingId);
    setSelectedReport(null);
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Crisis Damage Dashboard</h1>
        <span className="crisis-id">{CRISIS_EVENT_ID}</span>
        <nav>
          <button className={view === "map" ? "active" : ""} onClick={() => setView("map")}>Map</button>
          <button className={view === "heatmap" ? "active" : ""} onClick={() => setView("heatmap")}>Coverage</button>
          <button onClick={() => setShowExport((s) => !s)}>Export</button>
        </nav>
      </header>

      <StatsCards
        crisisEventId={CRISIS_EVENT_ID}
        liveCount={liveReports.length}
        wsConnected={connected}
      />

      <div className="dashboard-body">
        {/* Backdrop — tapping closes the drawer on mobile */}
        {drawerOpen && (
          <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />
        )}

        <aside className={`sidebar${drawerOpen ? " sidebar--open" : ""}`}>
          {/* Drag handle / close button visible only on mobile */}
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
            <CoverageHeatmap crisisEventId={CRISIS_EVENT_ID} center={MAP_CENTER} />
          )}

          {/* Floating feed toggle — mobile only */}
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

      {showExport && <ExportPanel crisisEventId={CRISIS_EVENT_ID} />}
    </div>
  );
}
