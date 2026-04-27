/**
 * React hook for dynamic form schema state.
 *
 * - Loads schema from cache or API on mount.
 * - Listens for the `schema:updated` custom event to detect background refreshes.
 * - Re-fetches the full schema when a newer version is detected.
 */

import { useState, useEffect, useCallback } from "react";
import { type FormSchema, loadSchema, refreshSchema } from "../services/schema";

interface UseSchemaResult {
  schema: FormSchema | null;
  schemaLoading: boolean;
  schemaVersion: number | null;
  /** Re-fetch the schema from the API right now. */
  refetchSchema: () => void;
  /** True if the loaded schema is the hardcoded fallback (API unreachable). */
  isFallback: boolean;
}

export function useSchema(crisisEventId: string): UseSchemaResult {
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(true);

  const refetchSchema = useCallback(() => {
    setSchemaLoading(true);
    refreshSchema(crisisEventId)
      .then((fresh) => {
        if (fresh) setSchema(fresh);
      })
      .finally(() => setSchemaLoading(false));
  }, [crisisEventId]);

  // Initial load
  useEffect(() => {
    setSchemaLoading(true);
    loadSchema(crisisEventId)
      .then((s) => setSchema(s))
      .finally(() => setSchemaLoading(false));
  }, [crisisEventId]);

  // Listen for background schema updates
  useEffect(() => {
    function handleSchemaUpdated(e: Event) {
      const detail = (e as CustomEvent<{ crisisEventId: string; version: number }>).detail;
      if (detail.crisisEventId === crisisEventId) {
        // Fetch the updated schema
        refreshSchema(crisisEventId).then((fresh) => {
          if (fresh) setSchema(fresh);
        });
      }
    }
    window.addEventListener("schema:updated", handleSchemaUpdated);
    return () => window.removeEventListener("schema:updated", handleSchemaUpdated);
  }, [crisisEventId]);

  return {
    schema,
    schemaLoading,
    schemaVersion: schema?.version ?? null,
    refetchSchema,
    isFallback: schema?._fallback === true,
  };
}
