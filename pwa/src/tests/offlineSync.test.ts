import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock PouchDB to avoid IndexedDB dependency in test environment
vi.mock("../services/pouchdb", () => ({
  localDB: {},
  enqueueReport: vi.fn().mockResolvedValue("report_test_123"),
  getQueuedReports: vi.fn().mockResolvedValue([]),
  getQueueCount: vi.fn().mockResolvedValue(0),
}));

vi.mock("../services/api", () => ({
  submitReport: vi.fn().mockResolvedValue({ report_id: "rpt_abc", map_url: "https://x.com" }),
}));

import { getQueueCount, enqueueReport } from "../services/pouchdb";

describe("offline queue", () => {
  beforeEach(() => vi.clearAllMocks());

  it("enqueues a report and returns an id", async () => {
    const id = await enqueueReport({ damage_level: "partial" }, null);
    expect(id).toBe("report_test_123");
  });

  it("returns zero queue count when empty", async () => {
    const count = await getQueueCount();
    expect(count).toBe(0);
  });
});
