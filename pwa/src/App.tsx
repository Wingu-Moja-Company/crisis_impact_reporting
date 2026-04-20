import "./i18n";
import { useTranslation } from "./hooks/useTranslation";
import { LanguageToggle } from "./components/LanguageToggle/LanguageToggle";
import { OfflineQueue } from "./components/OfflineQueue/OfflineQueue";
import { ReportForm } from "./components/ReportForm/ReportForm";
import { registerBackgroundSync } from "./services/sync";

registerBackgroundSync();

const CRISIS_EVENT_ID = import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev";

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
