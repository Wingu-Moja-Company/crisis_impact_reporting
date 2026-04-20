import PouchDB from "pouchdb";
import PouchDBFind from "pouchdb-find";

PouchDB.plugin(PouchDBFind);

export const localDB = new PouchDB("crisis-reports");

export interface OfflineReport {
  _id: string;
  _rev?: string;
  status: "queued" | "syncing" | "synced" | "failed";
  created_at: string;
  report_data: Record<string, unknown>;
  photo_base64: string | null;
  sync_attempts: number;
  last_sync_attempt: string | null;
  error_message?: string;
}

export async function enqueueReport(
  reportData: Record<string, unknown>,
  photoBase64: string | null
): Promise<string> {
  const id = `report_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  await localDB.put<OfflineReport>({
    _id: id,
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
  const result = await localDB.find({ selector: { status: "queued" } });
  return result.docs as unknown as OfflineReport[];
}

export async function getQueueCount(): Promise<number> {
  const result = await localDB.find({
    selector: { status: { $in: ["queued", "syncing"] } },
  });
  return result.docs.length;
}
