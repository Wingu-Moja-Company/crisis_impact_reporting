import "./i18n";
import { useTranslation } from "./hooks/useTranslation";
import { LanguageToggle } from "./components/LanguageToggle/LanguageToggle";
import { OfflineQueue } from "./components/OfflineQueue/OfflineQueue";
import { ReportForm } from "./components/ReportForm/ReportForm";
import { registerBackgroundSync } from "./services/sync";

registerBackgroundSync();

/** URL param takes priority over build-time env, enabling one PWA to serve many crises. */
function getCrisisEventId(): string {
  try {
    const param = new URLSearchParams(window.location.search).get("crisis_event_id");
    if (param && param.trim()) return param.trim();
  } catch { /* ignore */ }
  return import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev";
}

const CRISIS_EVENT_ID = getCrisisEventId();

export default function App() {
  const { t } = useTranslation();

  return (
    <div className="app">
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <LanguageToggle />
      </header>
      <OfflineQueue />
      <main>
        <ReportForm crisisEventId={CRISIS_EVENT_ID} />
      </main>
    </div>
  );
}
