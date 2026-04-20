import { useTranslation } from "../../hooks/useTranslation";
import { useOfflineSync } from "../../hooks/useOfflineSync";

export function OfflineQueue() {
  const { t } = useTranslation();
  const { isOnline, queueCount } = useOfflineSync();

  if (isOnline && queueCount === 0) return null;

  return (
    <div className={`offline-banner ${isOnline ? "syncing" : "offline"}`}>
      {!isOnline && <span>{t("app.offline_banner")}</span>}
      {queueCount > 0 && (
        <span>{t("app.queue_count", { count: queueCount })}</span>
      )}
    </div>
  );
}
