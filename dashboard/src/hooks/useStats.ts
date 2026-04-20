import { useEffect, useState } from "react";
import { fetchStats, type CrisisStats } from "../services/api";

export function useStats(crisisEventId: string, refreshMs = 60_000) {
  const [stats, setStats] = useState<CrisisStats | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchStats(crisisEventId);
        if (!cancelled) setStats(data);
      } catch {
        // retain last known stats on error
      }
    }

    load();
    const interval = setInterval(load, refreshMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [crisisEventId, refreshMs]);

  return stats;
}
