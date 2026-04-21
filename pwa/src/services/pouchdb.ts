import { openDB, type IDBPDatabase } from "idb";

export interface OfflineReport {
  id: string;
  status: "queued" | "syncing" | "synced" | "failed";
  created_at: string;
  report_data: Record<string, unknown>;
  photo_base64: string | null;
  sync_attempts: number;
  last_sync_attempt: string | null;
  error_message?: string;
}

type CrisisDB = {
  reports: {
    key: string;
    value: OfflineReport;
    indexes: { by_status: string };
  };
};

let _db: IDBPDatabase<CrisisDB> | null = null;

async function getDB(): Promise<IDBPDatabase<CrisisDB>> {
  if (_db) return _db;
  _db = await openDB<CrisisDB>("crisis-reports", 1, {
    upgrade(db) {
      const store = db.createObjectStore("reports", { keyPath: "id" });
      store.createIndex("by_status", "status");
    },
  });
  return _db;
}

export async function enqueueReport(
  reportData: Record<string, unknown>,
  photoBase64: string | null
): Promise<string> {
  const db = await getDB();
  const id = `report_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  await db.put("reports", {
    id,
    status: "queued",
    created_at: new Date().toISOString(),
    report_data: reportData,
    photo_base64: photoBase64,
    sync_attempts: 0,
    last_sync_attempt: null,
  });
  return id;
}

export async function getQueuedReports(): Promise<OfflineReport[]> {
  const db = await getDB();
  return db.getAllFromIndex("reports", "by_status", "queued");
}

export async function updateReport(report: OfflineReport): Promise<void> {
  const db = await getDB();
  await db.put("reports", report);
}

export async function getQueueCount(): Promise<number> {
  const db = await getDB();
  const [queued, syncing] = await Promise.all([
    db.countFromIndex("reports", "by_status", "queued"),
    db.countFromIndex("reports", "by_status", "syncing"),
  ]);
  return queued + syncing;
}
