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

export default function App() {
  const [view, setView] = useState<View>("map");
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [showExport, setShowExport] = useState(false);

  const { reports: liveReports, connected } = useLiveReports(CRISIS_EVENT_ID);

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
        <aside className="sidebar">
          <IncidentFeed reports={liveReports} onSelect={setSelectedBuilding} />
        </aside>

        <main className="map-container">
          {view === "map" ? (
            <DashboardMap
              center={MAP_CENTER}
              liveReports={liveReports}
              selectedBuildingId={selectedBuilding}
              onBuildingSelect={setSelectedBuilding}
            />
          ) : (
            <CoverageHeatmap crisisEventId={CRISIS_EVENT_ID} center={MAP_CENTER} />
          )}
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
