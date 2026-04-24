import { useState, useEffect, useCallback } from "react";
import { fetchCurrentBuildings, fetchBuildingSummary } from "../services/api";
import type { BuildingSummary } from "../services/api";

interface State {
  featureCollection: GeoJSON.FeatureCollection | null;
  summary: BuildingSummary | null;
  loading: boolean;
  error: string | null;
}

export function useBuildings(crisisEventId: string, enabled: boolean) {
  const [state, setState] = useState<State>({
    featureCollection: null, summary: null, loading: false, error: null,
  });

  const load = useCallback(async () => {
    if (!enabled || !crisisEventId) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [fc, summary] = await Promise.all([
        fetchCurrentBuildings(crisisEventId),
        fetchBuildingSummary(crisisEventId),
      ]);
      setState({ featureCollection: fc, summary, loading: false, error: null });
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: String(err) }));
    }
  }, [crisisEventId, enabled]);

  useEffect(() => { load(); }, [load]);

  return { ...state, refresh: load };
}
