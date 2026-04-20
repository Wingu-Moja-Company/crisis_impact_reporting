import { useEffect, useState } from "react";
import { getQueueCount } from "../services/pouchdb";
import { syncQueuedReports } from "../services/sync";

export function useOfflineSync() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [queueCount, setQueueCount] = useState(0);

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      syncQueuedReports().then(refreshCount);
    };
    const onOffline = () => setIsOnline(false);

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  async function refreshCount() {
    setQueueCount(await getQueueCount());
  }

  useEffect(() => {
    refreshCount();
    const interval = setInterval(refreshCount, 10_000);
    return () => clearInterval(interval);
  }, []);

  return { isOnline, queueCount, refreshCount };
}
