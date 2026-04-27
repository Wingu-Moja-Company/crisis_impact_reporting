/**
 * Schema fetch and cache service.
 *
 * The dynamic form schema is fetched from the pipeline API and cached in
 * localStorage (small JSON doc, no need for IndexedDB).  A lightweight
 * version-check poll (`?version_only=true`) is used to detect stale caches
 * without downloading the full schema on every load.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const INGEST_API_KEY = import.meta.env.VITE_INGEST_API_KEY ?? "";
const EXPORT_API_KEY = import.meta.env.VITE_EXPORT_API_KEY ?? "";

// Use whichever key is available (export key works for reads)
function _authHeader(): Record<string, string> {
  const key = INGEST_API_KEY || EXPORT_API_KEY;
  return key ? { "X-API-Key": key } : {};
}

// ---------------------------------------------------------------------------
// Types
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
  min_selections?: number;
}

export interface SystemFieldDef {
  values_locked: boolean;
  type: string;
  min_selections?: number;
  labels: Record<string, string>;
  /** select field: keyed by value, value is label map */
  options?: Record<string, Record<string, string>> | SchemaOption[];
}

export interface FormSchema {
  id?: string;
  crisis_event_id: string;
  version: number | null;
  system_fields: {
    damage_level: SystemFieldDef;
    infrastructure_type: SystemFieldDef;
  };
  custom_fields: SchemaField[];
  _fallback?: boolean;
}

// ---------------------------------------------------------------------------
// Cache (localStorage)
// ---------------------------------------------------------------------------

function _cacheKey(crisisEventId: string): string {
  return `schema_cache_${crisisEventId}`;
}

function _readCache(crisisEventId: string): FormSchema | null {
  try {
    const raw = localStorage.getItem(_cacheKey(crisisEventId));
    return raw ? (JSON.parse(raw) as FormSchema) : null;
  } catch {
    return null;
  }
}

function _writeCache(crisisEventId: string, schema: FormSchema): void {
  try {
    localStorage.setItem(_cacheKey(crisisEventId), JSON.stringify(schema));
  } catch {
    // Storage quota exceeded — proceed without caching
  }
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function _fetchSchemaFromAPI(crisisEventId: string): Promise<FormSchema | null> {
  try {
    const url = `${API_BASE}/v1/crisis-events/${crisisEventId}/schema`;
    const res = await fetch(url, { headers: _authHeader() });
    if (!res.ok) return null;
    return res.json() as Promise<FormSchema>;
  } catch {
    return null;
  }
}

async function _fetchVersionOnly(crisisEventId: string): Promise<number | null> {
  try {
    const url = `${API_BASE}/v1/crisis-events/${crisisEventId}/schema?version_only=true`;
    const res = await fetch(url, { headers: _authHeader() });
    if (!res.ok) return null;
    const data = await res.json() as { version: number };
    return data.version;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Fallback schema (used when API is unreachable)
// ---------------------------------------------------------------------------

const _FALLBACK_SCHEMA: FormSchema = {
  crisis_event_id: "",
  version: null,
  _fallback: true,
  system_fields: {
    damage_level: {
      values_locked: true,
      type: "select",
      labels: {
        en: "What is the damage level?",
        fr: "Quel est le niveau de dommages ?",
        ar: "ما مستوى الضرر؟",
        sw: "Kiwango cha uharibifu ni kipi?",
        es: "¿Cuál es el nivel de daño?",
        zh: "损坏程度如何？",
      },
      options: {
        minimal: {
          en: "Minimal — structurally sound, cosmetic damage only",
          fr: "Minimal — structure solide, dommages cosmétiques",
          ar: "أدنى — الهيكل سليم، أضرار شكلية",
          sw: "Kidogo — muundo imara",
          es: "Mínimo — estructuralmente sólido",
          zh: "轻微——结构完好",
        },
        partial: {
          en: "Partial — repairable, remains usable with caution",
          fr: "Partiel — réparable, reste utilisable",
          ar: "جزئي — قابل للإصلاح",
          sw: "Sehemu — inaweza kukarabatiwa",
          es: "Parcial — reparable",
          zh: "部分——可修复",
        },
        complete: {
          en: "Complete — structurally unsafe or destroyed",
          fr: "Complet — dangereux ou détruit",
          ar: "كامل — غير آمن هيكلياً",
          sw: "Kamili — si salama",
          es: "Completo — inseguro o destruido",
          zh: "完全——不安全或已毁",
        },
      },
    },
    infrastructure_type: {
      values_locked: false,
      type: "multiselect",
      min_selections: 1,
      labels: {
        en: "What type of infrastructure is affected?",
        fr: "Quel type d'infrastructure est affecté ?",
        ar: "ما نوع البنية التحتية المتضررة؟",
        sw: "Miundombinu ya aina gani imeathiriwa?",
        es: "¿Qué tipo de infraestructura está afectada?",
        zh: "哪类基础设施受到影响？",
      },
      options: [
        { value: "residential",  labels: { en: "Residential",       fr: "Résidentiel",  ar: "سكني",    sw: "Makazi",    es: "Residencial",  zh: "住宅" } },
        { value: "commercial",   labels: { en: "Commercial",        fr: "Commercial",   ar: "تجاري",   sw: "Biashara",  es: "Comercial",    zh: "商业" } },
        { value: "government",   labels: { en: "Government",        fr: "Gouvernement", ar: "حكومي",   sw: "Serikali",  es: "Gobierno",     zh: "政府" } },
        { value: "utility",      labels: { en: "Utility",           fr: "Services",     ar: "مرافق",   sw: "Huduma",    es: "Servicios",    zh: "公用设施" } },
        { value: "transport",    labels: { en: "Transport",         fr: "Transport",    ar: "نقل",     sw: "Usafiri",   es: "Transporte",   zh: "交通" } },
        { value: "community",    labels: { en: "Community",         fr: "Communauté",   ar: "مجتمعي",  sw: "Jamii",     es: "Comunidad",    zh: "社区" } },
        { value: "public_space", labels: { en: "Public space",      fr: "Espace public", ar: "فضاء عام", sw: "Nafasi ya umma", es: "Espacio público", zh: "公共空间" } },
        { value: "other",        labels: { en: "Other",             fr: "Autre",        ar: "أخرى",    sw: "Nyingine",  es: "Otro",         zh: "其他" } },
      ],
    },
  },
  custom_fields: [],
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Load the schema for the given crisis event.
 * - Returns cached schema immediately if available.
 * - Fetches fresh schema from API in parallel and updates cache.
 * - Falls back to hardcoded minimal schema if API unavailable and no cache.
 */
export async function loadSchema(crisisEventId: string): Promise<FormSchema> {
  // Return cached version immediately (for fast first render)
  const cached = _readCache(crisisEventId);
  if (cached) {
    // Background refresh — don't await
    _fetchSchemaFromAPI(crisisEventId).then((fresh) => {
      if (fresh && fresh.version !== cached.version) {
        _writeCache(crisisEventId, fresh);
        // Signal to the hook that a new version is available (custom event)
        window.dispatchEvent(
          new CustomEvent("schema:updated", { detail: { crisisEventId, version: fresh.version } })
        );
      }
    });
    return cached;
  }

  // No cache — fetch synchronously
  const schema = await _fetchSchemaFromAPI(crisisEventId);
  if (schema) {
    _writeCache(crisisEventId, schema);
    return schema;
  }

  return { ..._FALLBACK_SCHEMA, crisis_event_id: crisisEventId };
}

/**
 * Check if a newer schema version is available without downloading it.
 * Returns the new version number if stale, or null if up to date.
 */
export async function checkSchemaVersion(
  crisisEventId: string,
  currentVersion: number | null
): Promise<number | null> {
  const latestVersion = await _fetchVersionOnly(crisisEventId);
  if (latestVersion !== null && latestVersion !== currentVersion) {
    return latestVersion;
  }
  return null;
}

/**
 * Force-refresh the schema from the API and update the cache.
 */
export async function refreshSchema(crisisEventId: string): Promise<FormSchema | null> {
  const schema = await _fetchSchemaFromAPI(crisisEventId);
  if (schema) {
    _writeCache(crisisEventId, schema);
  }
  return schema;
}

// ---------------------------------------------------------------------------
// Label helpers
// ---------------------------------------------------------------------------

export function getLabel(
  labels: Record<string, string> | undefined,
  lang: string
): string {
  if (!labels) return "";
  return labels[lang] || labels["en"] || "";
}
