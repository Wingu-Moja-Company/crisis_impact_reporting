import { getQueuedReports, updateReport, type OfflineReport } from "./pouchdb";
import { submitReport } from "./api";

let _syncing = false;

export async function syncQueuedReports(): Promise<void> {
  if (_syncing) return;
  _syncing = true;

  try {
    const queued = await getQueuedReports();
    for (const doc of queued) {
      await _syncOne(doc);
    }
  } finally {
    _syncing = false;
  }
}

async function _syncOne(doc: OfflineReport): Promise<void> {
  await updateReport({ ...doc, status: "syncing" });
  try {
    await submitReport(doc.report_data as Record<string, string>, doc.photo_base64);
    await updateReport({ ...doc, status: "synced" });
  } catch (err) {
    await updateReport({
      ...doc,
      status: "failed",
      sync_attempts: doc.sync_attempts + 1,
      last_sync_attempt: new Date().toISOString(),
      error_message: String(err),
    });
  }
}

export function registerBackgroundSync(): void {
  window.addEventListener("online", () => {
    syncQueuedReports();
  });

  if (navigator.onLine) {
    syncQueuedReports();
  }
}
