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
        <div className="app-header-inner">
          <div className="app-header-icon">
            {/* Shield icon — trust / protection */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 2L4 6v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V6l-8-4z"
                stroke="white"
                strokeWidth="1.8"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="app-header-body">
            <div className="app-header-title">{t("app.title")}</div>
            <div className="app-header-sub">Crisis Reporting Platform</div>
          </div>
          <LanguageToggle />
        </div>
      </header>
      <OfflineQueue />
      <main>
        <ReportForm crisisEventId={CRISIS_EVENT_ID} />
      </main>
    </div>
  );
}
