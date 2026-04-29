import { useState } from "react";
import { useTranslation } from "react-i18next";
import { DashboardMap } from "./components/MapView/DashboardMap";
import { CoverageHeatmap } from "./components/CoverageHeatmap/CoverageHeatmap";
import { IncidentFeed } from "./components/IncidentFeed/IncidentFeed";
import { BuildingHistory } from "./components/BuildingHistory/BuildingHistory";
import { BuildingsMap } from "./components/BuildingsView/BuildingsMap";
import { BuildingsSummaryPanel } from "./components/BuildingsView/BuildingsSummaryPanel";
import { ExportPanel } from "./components/ExportPanel/ExportPanel";
import { StatsCards } from "./components/StatsCards/StatsCards";
import { AdminPanel } from "./components/AdminPanel/AdminPanel";
import { LanguageToggle } from "./components/LanguageToggle/LanguageToggle";
import { useLiveReports } from "./hooks/useLiveReports";
import { useBuildings } from "./hooks/useBuildings";
import { useSchema } from "./hooks/useSchema";

const DEFAULT_CRISIS_ID = import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev";
const MAP_CENTER: [number, number] = [-1.2577, 36.8614];

function getCrisisIdFromUrl(): string {
  try {
    const param = new URLSearchParams(window.location.search).get("crisis_event_id");
    if (param?.trim()) return param.trim();
  } catch { /* ignore */ }
  return DEFAULT_CRISIS_ID;
}

type View = "map" | "heatmap" | "buildings";

function getReportFromUrl(): string | null {
  try {
    return new URLSearchParams(window.location.search).get("report");
  } catch {
    return null;
  }
}

export default function App() {
  const { t } = useTranslation();
  const [crisisEventId, setCrisisEventId]       = useState(getCrisisIdFromUrl);
  const [view, setView]                         = useState<View>("map");
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null);
  const [selectedReport, setSelectedReport]     = useState<string | null>(getReportFromUrl);
  const [showExport, setShowExport]             = useState(false);
  const [showAdmin, setShowAdmin]               = useState(false);
  const [drawerOpen, setDrawerOpen]             = useState(false);

  const { reports: liveReports, connected, lastFetched } = useLiveReports(crisisEventId);
  const { schema } = useSchema(crisisEventId);
  const {
    featureCollection: buildingsGeoJSON,
    summary: buildingsSummary,
    loading: buildingsLoading,
    error: buildingsError,
    refresh: refreshBuildings,
  } = useBuildings(crisisEventId, view === "buildings");

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
    const url = new URL(window.location.href);
    url.searchParams.set("crisis_event_id", id);
    window.history.pushState({}, "", url.toString());
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>{t("app.title")}</h1>
        <span className="crisis-id">{crisisEventId}</span>
        <nav>
          <button className={view === "map" ? "active" : ""} onClick={() => setView("map")}>{t("app.nav_map")}</button>
          <button className={view === "heatmap" ? "active" : ""} onClick={() => setView("heatmap")}>{t("app.nav_coverage")}</button>
          <button className={view === "buildings" ? "active" : ""} onClick={() => setView("buildings")}>{t("buildings.nav")}</button>
          <button onClick={() => setShowExport((s) => !s)}>{t("app.nav_export")}</button>
          <button
            className="admin-btn"
            onClick={() => setShowAdmin(true)}
            title={t("admin.panel_title")}
          >
            ⚙️
          </button>
        </nav>
        <LanguageToggle />
      </header>

      <StatsCards
        crisisEventId={crisisEventId}
        liveCount={liveReports.length}
        wsConnected={connected}
        lastFetched={lastFetched}
        schema={schema}
      />

      <div className="dashboard-body">
        {drawerOpen && (
          <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />
        )}

        <aside className={`sidebar${drawerOpen ? " sidebar--open" : ""}`}>
          <div className="sidebar-handle">
            <span className="sidebar-handle-label">
              {t("app.reports_count", { count: liveReports.length })}
            </span>
            <button
              className="sidebar-close-btn"
              onClick={() => setDrawerOpen(false)}
              aria-label={t("app.close_panel")}
            >✕</button>
          </div>

          {view === "buildings" ? (
            <BuildingsSummaryPanel
              summary={buildingsSummary}
              loading={buildingsLoading}
              error={buildingsError}
              onRefresh={refreshBuildings}
            />
          ) : (
            <IncidentFeed
              reports={liveReports}
              selectedReportId={selectedReport}
              onSelect={handleReportSelect}
              schema={schema}
              lastFetched={lastFetched}
            />
          )}
        </aside>

        <main className="map-container">
          {view === "map" ? (
            <DashboardMap
              center={MAP_CENTER}
              liveReports={liveReports}
              selectedBuildingId={selectedBuilding}
              selectedReportId={selectedReport}
              onBuildingSelect={handleBuildingSelect}
              schema={schema}
            />
          ) : view === "heatmap" ? (
            <CoverageHeatmap crisisEventId={crisisEventId} center={MAP_CENTER} />
          ) : (
            <BuildingsMap
              center={MAP_CENTER}
              buildings={buildingsGeoJSON}
              selectedBuildingId={selectedBuilding}
              onBuildingSelect={handleBuildingSelect}
            />
          )}

          {view !== "buildings" && (
            <button
              className="feed-fab"
              onClick={() => setDrawerOpen((o) => !o)}
              aria-label={t("app.toggle_feed")}
            >
              📋 {t("app.reports_count", { count: liveReports.length })}
            </button>
          )}
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
