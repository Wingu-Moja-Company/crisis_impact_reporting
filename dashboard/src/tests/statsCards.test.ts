import { describe, it, expect, vi } from "vitest";

vi.mock("../services/api", () => ({
  fetchStats: vi.fn().mockResolvedValue({
    crisis_event_id: "ke-flood-dev",
    total_reports: 42,
    by_damage_level: { minimal: 20, partial: 15, complete: 7 },
  }),
  fetchBuildingHistory: vi.fn().mockResolvedValue([]),
  fetchReports: vi.fn().mockResolvedValue({ type: "FeatureCollection", features: [] }),
  buildExportUrl: vi.fn().mockReturnValue("http://localhost/api/v1/reports?format=csv"),
}));

import { fetchStats, buildExportUrl } from "../services/api";

describe("api service", () => {
  it("fetchStats returns totals and breakdown", async () => {
    const stats = await fetchStats("ke-flood-dev");
    expect(stats.total_reports).toBe(42);
    expect(stats.by_damage_level.complete).toBe(7);
  });

  it("buildExportUrl includes format param", () => {
    const url = buildExportUrl("ke-flood-dev", "csv");
    expect(url).toContain("format=csv");
  });
});
