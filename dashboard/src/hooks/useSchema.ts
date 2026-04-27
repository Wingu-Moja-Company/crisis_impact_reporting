/**
 * React hook for loading the dynamic form schema in the dashboard.
 * Uses the export API key (read-only) to fetch from the pipeline API.
 * Schema is cached in localStorage and refreshed in the background.
 */

import { useState, useEffect, useCallback } from "react";

const API_BASE       = import.meta.env.VITE_API_BASE_URL ?? "/api";
const EXPORT_API_KEY = import.meta.env.VITE_EXPORT_API_KEY ?? "";

function authHeader(): Record<string, string> {
  return EXPORT_API_KEY ? { "X-API-Key": EXPORT_API_KEY } : {};
}

// ---------------------------------------------------------------------------
// Types (mirrored from pwa/src/services/schema.ts — keep in sync)
// ---------------------------------------------------------------------------

export interface SchemaOption {
  value: string;
  labels: Record<string, string>;
}

export interface SchemaField {
  id: string;
  type: "select" | "multiselect" | "boolean" | "text" | "number";
  required: boolean;
  order: number;
  labels: Record<string, string>;
  options?: SchemaOption[];
}

export interface SystemFieldDef {
  values_locked: boolean;
  type: string;
  labels: Record<string, string>;
  options?: Record<string, Record<string, string>> | SchemaOption[];
}

export interface FormSchema {
  id?: string;
  crisis_event_id: string;
  version: number | null;
  published_at?: string;
  system_fields: {
    damage_level: SystemFieldDef;
    infrastructure_type: SystemFieldDef;
  };
  custom_fields: SchemaField[];
}

// ---------------------------------------------------------------------------
// Cache (localStorage)
// ---------------------------------------------------------------------------

function cacheKey(crisisEventId: string): string {
  return `dashboard_schema_${crisisEventId}`;
}

function readCache(crisisEventId: string): FormSchema | null {
  try {
    const raw = localStorage.getItem(cacheKey(crisisEventId));
    return raw ? JSON.parse(raw) as FormSchema : null;
  } catch {
    return null;
  }
}

function writeCache(crisisEventId: string, schema: FormSchema): void {
  try {
    localStorage.setItem(cacheKey(crisisEventId), JSON.stringify(schema));
  } catch { /* quota */ }
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchSchemaFromAPI(crisisEventId: string): Promise<FormSchema | null> {
  try {
    const res = await fetch(
      `${API_BASE}/v1/crisis-events/${crisisEventId}/schema`,
      { headers: authHeader() }
    );
    if (!res.ok) return null;
    return res.json() as Promise<FormSchema>;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseSchemaResult {
  schema: FormSchema | null;
  schemaLoading: boolean;
  refetchSchema: () => void;
}

export function useSchema(crisisEventId: string): UseSchemaResult {
  const [schema, setSchema] = useState<FormSchema | null>(() => readCache(crisisEventId));
  const [schemaLoading, setSchemaLoading] = useState(!readCache(crisisEventId));

  const refetchSchema = useCallback(() => {
    setSchemaLoading(true);
    fetchSchemaFromAPI(crisisEventId).then((fresh) => {
      if (fresh) {
        writeCache(crisisEventId, fresh);
        setSchema(fresh);
      }
      setSchemaLoading(false);
    });
  }, [crisisEventId]);

  useEffect(() => {
    setSchemaLoading(true);
    fetchSchemaFromAPI(crisisEventId).then((fresh) => {
      if (fresh) {
        writeCache(crisisEventId, fresh);
        setSchema(fresh);
      }
      setSchemaLoading(false);
    });
  }, [crisisEventId]);

  return { schema, schemaLoading, refetchSchema };
}

// ---------------------------------------------------------------------------
// Label helper
// ---------------------------------------------------------------------------

export function getSchemaLabel(
  labels: Record<string, string> | undefined,
  lang: string
): string {
  if (!labels) return "";
  return labels[lang] || labels["en"] || "";
}
