import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { SchemaEditor } from "../SchemaEditor/SchemaEditor";
import "./AdminPanel.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

interface CrisisEvent {
  id: string;
  name: string;
  country_code: string;
  region: string;
  crisis_nature: string;
  status: "active" | "archived" | "paused";
  created_at: string;
  updated_at?: string;
}

interface EventStats {
  total_reports: number;
  by_damage_level: Record<string, number>;
}

const CRISIS_NATURES = [
  "flood", "earthquake", "hurricane", "wildfire", "tsunami",
  "conflict", "civil_unrest", "explosion", "chemical",
] as const;

const SCHEMA_TYPES = [
  { value: "flood",      labelKey: "Flood" },
  { value: "earthquake", labelKey: "Earthquake" },
  { value: "conflict",   labelKey: "Conflict" },
  { value: "hurricane",  labelKey: "Hurricane / Cyclone" },
  { value: "wildfire",   labelKey: "Wildfire" },
  { value: "generic",   labelKey: "Generic (no extra fields)" },
] as const;

const NATURE_EMOJI: Record<string, string> = {
  flood: "🌊", earthquake: "🏚", hurricane: "🌀", wildfire: "🔥",
  tsunami: "🌊", conflict: "⚔️", civil_unrest: "🚨",
  explosion: "💥", chemical: "☣️",
};

function fmt(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale, {
    day: "2-digit", month: "short", year: "numeric",
  });
}

function exportUrl(eventId: string, format: "geojson" | "csv" | "shapefile"): string {
  const key = import.meta.env.VITE_EXPORT_API_KEY ?? "";
  const base = `${API_BASE}/v1/reports?crisis_event_id=${encodeURIComponent(eventId)}&format=${format}&limit=5000`;
  return key ? `${base}&_key=${encodeURIComponent(key)}` : base;
}

const PWA_BASE      = (import.meta.env.VITE_PWA_URL ?? "").replace(/\/$/, "");
const BOT_USERNAME  = import.meta.env.VITE_TELEGRAM_BOT_USERNAME ?? "";

function pwaLink(eventId: string): string {
  return PWA_BASE ? `${PWA_BASE}/?crisis_event_id=${encodeURIComponent(eventId)}` : "";
}

function botLink(eventId: string): string {
  return BOT_USERNAME ? `https://t.me/${BOT_USERNAME}?start=${encodeURIComponent(eventId)}` : "";
}

/** Compact inline copy pill — sits in the meta line next to slug/date. */
function MetaCopyBtn({ url, label, icon }: { url: string; label: string; icon: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  if (!url) return null;
  function handleCopy() {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button
      type="button"
      className={`meta-copy-btn${copied ? " meta-copy-btn--copied" : ""}`}
      onClick={handleCopy}
      title={url}
    >
      {copied ? (
        <>
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Copied
        </>
      ) : (
        <>{icon}{label}</>
      )}
    </button>
  );
}


interface CreateModalProps {
  adminKey: string;
  onCreated: () => void;
  onClose: () => void;
}

function CreateModal({ adminKey, onCreated, onClose }: CreateModalProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    id: "", name: "", country_code: "", region: "",
    crisis_nature: "flood", schema_type: "flood",
    map_lat: "", map_lon: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError(null);
  }

  function handleNameChange(name: string) {
    const slug = name.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, "")
      .trim()
      .replace(/\s+/g, "-")
      .slice(0, 40);
    setForm((f) => ({ ...f, name, id: slug }));
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const body: Record<string, unknown> = {
      id:            form.id.trim(),
      name:          form.name.trim(),
      country_code:  form.country_code.trim().toUpperCase(),
      region:        form.region.trim().toLowerCase(),
      crisis_nature: form.crisis_nature,
      schema_type:   form.schema_type,
    };
    if (form.map_lat && form.map_lon) {
      body.map_center = [parseFloat(form.map_lat), parseFloat(form.map_lon)];
    }

    try {
      const res = await fetch(`${API_BASE}/v1/admin/crisis-events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(adminKey ? { "X-Admin-Key": adminKey } : {}),
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`);
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="ap-modal-backdrop" onClick={onClose}>
      <div className="ap-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ap-modal-header">
          <h2>{t("admin.create_title")}</h2>
          <button className="ap-icon-btn" onClick={onClose}>✕</button>
        </div>
        <form className="ap-form" onSubmit={handleSubmit}>
          <label className="ap-label">
            {t("admin.field_name")}
            <input
              className="ap-input"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Kenya Nairobi Floods — May 2026"
              required
            />
          </label>

          <label className="ap-label">
            {t("admin.field_id")}
            <input
              className="ap-input ap-mono"
              value={form.id}
              onChange={(e) => set("id", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
              placeholder="e.g. ke-floods-2026-05"
              required
              pattern="[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]"
              title="Lowercase letters, numbers, hyphens only (3–50 chars)"
            />
            <span className="ap-hint">{t("admin.field_id_hint")}</span>
          </label>

          <div className="ap-row">
            <label className="ap-label">
              {t("admin.field_country")}
              <input
                className="ap-input ap-short"
                value={form.country_code}
                onChange={(e) => set("country_code", e.target.value.toUpperCase().slice(0, 2))}
                placeholder="KE"
                maxLength={2}
                required
              />
            </label>
            <label className="ap-label ap-grow">
              {t("admin.field_region")}
              <input
                className="ap-input"
                value={form.region}
                onChange={(e) => set("region", e.target.value)}
                placeholder="e.g. nairobi"
              />
            </label>
          </div>

          <div className="ap-row">
            <label className="ap-label ap-grow">
              {t("admin.field_crisis_type")}
              <select className="ap-input" value={form.crisis_nature}
                onChange={(e) => {
                  const val = e.target.value;
                  setForm((f) => ({
                    ...f, crisis_nature: val,
                    schema_type: ["flood","earthquake","conflict"].includes(val) ? val : "generic",
                  }));
                }}>
                {CRISIS_NATURES.map((n) => (
                  <option key={n} value={n}>{n.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </label>
            <label className="ap-label ap-grow">
              {t("admin.field_schema")}
              <select className="ap-input" value={form.schema_type}
                onChange={(e) => set("schema_type", e.target.value)}>
                {SCHEMA_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.labelKey}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="ap-section-title">{t("admin.field_map_centre")}</div>
          <div className="ap-row">
            <label className="ap-label ap-grow">
              {t("admin.field_lat")}
              <input className="ap-input" type="number" step="any"
                value={form.map_lat} onChange={(e) => set("map_lat", e.target.value)}
                placeholder="-1.2577" />
            </label>
            <label className="ap-label ap-grow">
              {t("admin.field_lon")}
              <input className="ap-input" type="number" step="any"
                value={form.map_lon} onChange={(e) => set("map_lon", e.target.value)}
                placeholder="36.8614" />
            </label>
          </div>

          {error && <div className="ap-error">⚠ {error}</div>}

          <div className="ap-modal-actions">
            <button type="button" className="ap-btn ap-btn--ghost" onClick={onClose}>
              {t("admin.cancel")}
            </button>
            <button type="submit" className="ap-btn ap-btn--primary" disabled={saving}>
              {saving ? t("admin.creating") : t("admin.create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Reports Manager Modal ──────────────────────────────────────────────────

interface ReportRow {
  report_id: string;
  submitted_at: string;
  channel: string;
  damage_level: string;
  infrastructure_types: string[];
  lat: number | null;
  lon: number | null;
  responses: Record<string, unknown>;
}

const DAMAGE_LEVELS = ["minimal", "partial", "complete"] as const;
const INFRA_OPTIONS = [
  "residential", "commercial", "government", "utility",
  "transport", "community", "public_space", "other",
];
const DAMAGE_COLOUR: Record<string, string> = {
  minimal: "#16a34a", partial: "#d97706", complete: "#dc2626",
};

interface ReportsModalProps {
  crisisEventId: string;
  adminKey: string;
  onClose: () => void;
}

function ReportsModal({ crisisEventId, adminKey, onClose }: ReportsModalProps) {
  const exportKey = import.meta.env.VITE_EXPORT_API_KEY ?? "";
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Edit form state
  const [editDamage, setEditDamage] = useState<string>("");
  const [editInfra, setEditInfra] = useState<string[]>([]);
  const [editResponses, setEditResponses] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const authHeaders = {
    ...(adminKey ? { "X-Admin-Key": adminKey } : {}),
    ...(exportKey ? { "X-API-Key": exportKey } : {}),
  };

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/v1/reports?crisis_event_id=${encodeURIComponent(crisisEventId)}&format=geojson&limit=500`,
          { headers: exportKey ? { "X-API-Key": exportKey } : {} },
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const features = (data.features ?? []) as { properties: Record<string, unknown>; geometry: { coordinates: number[] } | null }[];
        const KNOWN_META = new Set([
          "report_id","crisis_event_id","building_id","submitted_at","channel",
          "schema_version","damage_level","infrastructure_types","infrastructure_name",
          "description_en","description","ai_vision_confidence","ai_vision_suggested_level",
          "ai_vision_summary","ai_vision_debris_confirmed","ai_vision_access_status",
          "ai_vision_hazard_indicators","ai_vision_intervention_priority","what3words",
          "location_description","building_footprint_matched","submitter_tier","photo_url",
        ]);
        const rows: ReportRow[] = features.map((f) => {
          const p = f.properties;
          const responses: Record<string, unknown> = {};
          for (const [k, v] of Object.entries(p)) {
            if (!KNOWN_META.has(k)) responses[k] = v;
          }
          return {
            report_id: String(p.report_id ?? ""),
            submitted_at: String(p.submitted_at ?? ""),
            channel: String(p.channel ?? ""),
            damage_level: String(p.damage_level ?? ""),
            infrastructure_types: (p.infrastructure_types as string[]) ?? [],
            lat: f.geometry?.coordinates?.[1] ?? null,
            lon: f.geometry?.coordinates?.[0] ?? null,
            responses,
          };
        });
        rows.sort((a, b) => b.submitted_at.localeCompare(a.submitted_at));
        setReports(rows);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [crisisEventId, exportKey]);

  function startEdit(r: ReportRow) {
    setEditingId(r.report_id);
    setEditDamage(r.damage_level);
    setEditInfra([...r.infrastructure_types]);
    // Convert responses values to strings for simple text inputs
    setEditResponses(
      Object.fromEntries(
        Object.entries(r.responses).map(([k, v]) => [
          k,
          Array.isArray(v) ? (v as string[]).join(", ") : String(v ?? ""),
        ]),
      ),
    );
    setSaveError(null);
    setConfirmId(null);
  }

  function toggleInfra(val: string) {
    setEditInfra((prev) =>
      prev.includes(val) ? prev.filter((v) => v !== val) : [...prev, val],
    );
  }

  async function handleSave(reportId: string) {
    setSaving(true);
    setSaveError(null);
    try {
      // Convert response strings back — split comma-separated lists for known array fields
      const ARRAY_FIELDS = new Set(["infrastructure_types", "pressing_needs", "ai_vision_hazard_indicators"]);
      const responses: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(editResponses)) {
        if (ARRAY_FIELDS.has(k)) {
          responses[k] = v.split(",").map((s) => s.trim()).filter(Boolean);
        } else if (v === "true") {
          responses[k] = true;
        } else if (v === "false") {
          responses[k] = false;
        } else {
          responses[k] = v;
        }
      }

      const res = await fetch(
        `${API_BASE}/v1/admin/reports/${encodeURIComponent(reportId)}?crisis_event_id=${encodeURIComponent(crisisEventId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json", ...authHeaders },
          body: JSON.stringify({
            damage_level: editDamage,
            infrastructure_types: editInfra,
            responses,
          }),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `HTTP ${res.status}`);
      }
      // Update local state
      setReports((prev) =>
        prev.map((r) =>
          r.report_id === reportId
            ? { ...r, damage_level: editDamage, infrastructure_types: editInfra, responses }
            : r,
        ),
      );
      setEditingId(null);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(reportId: string) {
    setDeleting(reportId);
    setConfirmId(null);
    try {
      const res = await fetch(
        `${API_BASE}/v1/admin/reports/${encodeURIComponent(reportId)}?crisis_event_id=${encodeURIComponent(crisisEventId)}`,
        { method: "DELETE", headers: authHeaders },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `HTTP ${res.status}`);
      }
      setReports((prev) => prev.filter((r) => r.report_id !== reportId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(null);
    }
  }

  function fmtTime(iso: string) {
    try {
      return new Date(iso).toLocaleString(undefined, {
        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
      });
    } catch { return iso; }
  }

  return (
    <div className="ap-modal-backdrop" onClick={() => { if (!editingId) onClose(); }}>
      <div className="rm-panel" onClick={(e) => e.stopPropagation()}>

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="rm-header">
          <div>
            <h2 className="rm-title">🗂 Reports</h2>
            <p className="rm-sub">
              <code>{crisisEventId}</code>
              {!loading && <span> · {reports.length} report{reports.length !== 1 ? "s" : ""}</span>}
            </p>
          </div>
          <button className="ap-icon-btn" onClick={onClose}>✕</button>
        </div>

        {/* ── List ────────────────────────────────────────────────────────── */}
        <div className="rm-list">
          {loading && <div className="ap-loading">Loading reports…</div>}
          {!loading && error && <div className="ap-error" style={{ margin: "1rem" }}>⚠ {error}</div>}
          {!loading && !error && reports.length === 0 && (
            <div className="ap-empty">No reports for this crisis event.</div>
          )}

          {reports.map((r) => (
            <div
              key={r.report_id}
              className="rm-card"
              style={{ borderLeftColor: DAMAGE_COLOUR[r.damage_level] ?? "#9ca3af" }}
            >
              {/* ── Summary row ─────────────────────────────────────────── */}
              <div className="rm-row">
                <div className="rm-row-body">
                  <div className="rm-row-top">
                    <span
                      className="rm-damage-badge"
                      style={{
                        background: DAMAGE_COLOUR[r.damage_level] ? `${DAMAGE_COLOUR[r.damage_level]}18` : "#f3f4f6",
                        color: DAMAGE_COLOUR[r.damage_level] ?? "#6b7280",
                        border: `1px solid ${DAMAGE_COLOUR[r.damage_level] ?? "#d1d5db"}`,
                      }}
                    >
                      {(r.damage_level || "unknown").toUpperCase()}
                    </span>
                    <span className="rm-infra">
                      {r.infrastructure_types.map((t) => t.replace(/_/g, " ")).join(", ") || "—"}
                    </span>
                  </div>
                  <div className="rm-row-meta">
                    <span>{fmtTime(r.submitted_at)}</span>
                    <span className="rm-dot">·</span>
                    <span className="rm-channel">{r.channel}</span>
                    {r.lat != null && (
                      <>
                        <span className="rm-dot">·</span>
                        <span>{r.lat.toFixed(3)}, {r.lon?.toFixed(3)}</span>
                      </>
                    )}
                    <span className="rm-dot">·</span>
                    <code className="rm-id">{r.report_id}</code>
                  </div>
                </div>

                <div className="rm-actions">
                  {editingId !== r.report_id && confirmId !== r.report_id && (
                    <>
                      <button className="rm-btn rm-btn--edit" onClick={() => startEdit(r)}>
                        Edit
                      </button>
                      <button
                        className="rm-btn rm-btn--delete"
                        onClick={() => setConfirmId(r.report_id)}
                        disabled={deleting === r.report_id}
                      >
                        Delete
                      </button>
                    </>
                  )}
                  {confirmId === r.report_id && (
                    <>
                      <span className="rm-confirm-label">Sure?</span>
                      <button
                        className="rm-btn rm-btn--confirm"
                        disabled={deleting === r.report_id}
                        onClick={() => handleDelete(r.report_id)}
                      >
                        {deleting === r.report_id ? "…" : "Yes"}
                      </button>
                      <button className="rm-btn rm-btn--cancel" onClick={() => setConfirmId(null)}>
                        No
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* ── Inline edit form ─────────────────────────────────────── */}
              {editingId === r.report_id && (
                <div className="rm-edit-form">
                  <div className="rm-edit-grid2">
                    {/* Damage level */}
                    <label className="ap-label">
                      Damage level
                      <select
                        className="ap-input"
                        value={editDamage}
                        onChange={(e) => setEditDamage(e.target.value)}
                      >
                        {DAMAGE_LEVELS.map((d) => (
                          <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                        ))}
                      </select>
                    </label>

                    {/* placeholder for grid alignment */}
                    <div />
                  </div>

                  {/* Infrastructure types */}
                  <div className="ap-label" style={{ marginBottom: ".25rem" }}>Infrastructure types</div>
                  <div className="rm-checkboxes">
                    {INFRA_OPTIONS.map((opt) => (
                      <label key={opt} className="rm-checkbox-label">
                        <input type="checkbox" checked={editInfra.includes(opt)} onChange={() => toggleInfra(opt)} />
                        {opt.replace(/_/g, " ")}
                      </label>
                    ))}
                    {editInfra.filter((v) => !INFRA_OPTIONS.includes(v)).map((opt) => (
                      <label key={opt} className="rm-checkbox-label">
                        <input type="checkbox" checked onChange={() => toggleInfra(opt)} />
                        {opt}
                      </label>
                    ))}
                  </div>

                  {/* Custom field responses */}
                  {Object.keys(editResponses).length > 0 && (
                    <>
                      <div className="rm-edit-section-title">Custom fields</div>
                      <div className="rm-responses-grid">
                        {Object.entries(editResponses).map(([key, val]) => (
                          <label key={key} className="ap-label">
                            {key.replace(/_/g, " ")}
                            <input
                              className="ap-input"
                              value={val}
                              onChange={(e) => setEditResponses((prev) => ({ ...prev, [key]: e.target.value }))}
                            />
                          </label>
                        ))}
                      </div>
                    </>
                  )}

                  {saveError && <div className="ap-error">⚠ {saveError}</div>}

                  <div className="rm-edit-actions">
                    <button
                      className="rm-btn rm-btn--cancel"
                      onClick={() => { setEditingId(null); setSaveError(null); }}
                    >
                      Cancel
                    </button>
                    <button
                      className="rm-btn rm-btn--save"
                      disabled={saving}
                      onClick={() => handleSave(r.report_id)}
                    >
                      {saving ? "Saving…" : "Save changes"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <div className="rm-footer">
          <button className="ap-btn ap-btn--ghost ap-btn--sm" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

interface Props {
  onClose: () => void;
  onSwitchCrisis: (id: string) => void;
  activeCrisisId: string;
}

export function AdminPanel({ onClose, onSwitchCrisis, activeCrisisId }: Props) {
  const { t, i18n } = useTranslation();
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem("admin_key") ?? "");
  const [keyInput, setKeyInput] = useState("");
  const [authError, setAuthError] = useState(false);
  const isAuthed = !import.meta.env.VITE_ADMIN_KEY_REQUIRED || adminKey;

  const [events, setEvents] = useState<CrisisEvent[]>([]);
  const [stats, setStats] = useState<Record<string, EventStats>>({});
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [updating, setUpdating] = useState<string | null>(null);
  const [schemaEditorId, setSchemaEditorId] = useState<string | null>(null);
  const [reportsModalId, setReportsModalId] = useState<string | null>(null);
  const [purgeConfirmId, setPurgeConfirmId] = useState<string | null>(null);
  const [purging, setPurging] = useState<string | null>(null);
  const [purgeResult, setPurgeResult] = useState<{ id: string; reports: number; blobs: number } | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/crisis-events`, {
        headers: adminKey ? { "X-Admin-Key": adminKey, "X-API-Key": adminKey } : {},
      });
      if (res.status === 401 || res.status === 403) {
        setAuthError(true);
        setAdminKey("");
        sessionStorage.removeItem("admin_key");
        return;
      }
      const data = await res.json();
      const list: CrisisEvent[] = Array.isArray(data) ? data : [];
      list.sort((a, b) => b.created_at.localeCompare(a.created_at));
      setEvents(list);

      const statsEntries = await Promise.all(
        list.map(async (ev) => {
          try {
            const r = await fetch(
              `${API_BASE}/v1/crisis-events/${encodeURIComponent(ev.id)}/stats`,
              { headers: adminKey ? { "X-API-Key": adminKey } : {} },
            );
            return [ev.id, r.ok ? await r.json() : null] as const;
          } catch {
            return [ev.id, null] as const;
          }
        }),
      );
      setStats(Object.fromEntries(statsEntries.filter(([, v]) => v != null)));
    } catch {
      // non-critical
    } finally {
      setLoading(false);
    }
  }, [adminKey]);

  useEffect(() => {
    if (isAuthed) load();
  }, [isAuthed, load]);

  // Auto-reset click-to-confirm states after 4 seconds
  useEffect(() => {
    if (!deleteConfirmId) return;
    const t = setTimeout(() => setDeleteConfirmId(null), 4000);
    return () => clearTimeout(t);
  }, [deleteConfirmId]);

  useEffect(() => {
    if (!purgeConfirmId) return;
    const t = setTimeout(() => setPurgeConfirmId(null), 4000);
    return () => clearTimeout(t);
  }, [purgeConfirmId]);

  async function updateStatus(eventId: string, status: string) {
    setUpdating(eventId);
    try {
      const res = await fetch(`${API_BASE}/v1/admin/crisis-events/${encodeURIComponent(eventId)}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(adminKey ? { "X-Admin-Key": adminKey } : {}),
        },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        setEvents((prev) =>
          prev.map((ev) => ev.id === eventId ? { ...ev, status: status as CrisisEvent["status"] } : ev),
        );
      }
    } finally {
      setUpdating(null);
    }
  }

  async function handlePurge(eventId: string) {
    setPurging(eventId);
    setPurgeConfirmId(null);
    try {
      const res = await fetch(
        `${API_BASE}/v1/admin/crisis-events/${encodeURIComponent(eventId)}/data?confirm=yes`,
        {
          method: "DELETE",
          headers: adminKey ? { "X-Admin-Key": adminKey } : {},
        },
      );
      const data = await res.json();
      setPurgeResult({ id: eventId, reports: data.deleted_reports ?? 0, blobs: data.deleted_blobs ?? 0 });
      // Refresh stats after purge
      load();
    } catch {
      // non-critical
    } finally {
      setPurging(null);
    }
  }

  async function handleDeleteEvent(eventId: string) {
    setDeleting(eventId);
    setDeleteConfirmId(null);
    try {
      await fetch(
        `${API_BASE}/v1/admin/crisis-events/${encodeURIComponent(eventId)}?confirm=yes`,
        {
          method: "DELETE",
          headers: adminKey ? { "X-Admin-Key": adminKey } : {},
        },
      );
      // Remove from local list immediately
      setEvents((prev) => prev.filter((ev) => ev.id !== eventId));
      setStats((prev) => { const s = { ...prev }; delete s[eventId]; return s; });
    } catch {
      // non-critical
    } finally {
      setDeleting(null);
    }
  }

  function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    sessionStorage.setItem("admin_key", keyInput);
    setAdminKey(keyInput);
    setAuthError(false);
  }

  if (!isAuthed || authError) {
    return (
      <div className="ap-overlay">
        <div className="ap-auth-card">
          <div className="ap-auth-icon">🔐</div>
          <h2>{t("admin.access_title")}</h2>
          <p>{t("admin.access_prompt")}</p>
          {authError && <div className="ap-error">{t("admin.invalid_key")}</div>}
          <form onSubmit={handleAuth}>
            <input
              className="ap-input"
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder={t("admin.key_placeholder")}
              autoFocus
            />
            <div className="ap-modal-actions">
              <button type="button" className="ap-btn ap-btn--ghost" onClick={onClose}>{t("admin.cancel")}</button>
              <button type="submit" className="ap-btn ap-btn--primary" disabled={!keyInput}>{t("admin.unlock")}</button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="ap-overlay">
      <div className="ap-panel">
        {/* ── Panel header ────────────────────────────────────────────────── */}
        <div className="ap-panel-header">
          <div className="ap-panel-icon">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4"/>
              <path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4M12.6 12.6l-1.4-1.4M4.8 4.8L3.4 3.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="ap-panel-title-block">
            <h1 className="ap-panel-title">{t("admin.panel_title")}</h1>
            <p className="ap-panel-sub">{t("admin.panel_sub")}</p>
          </div>
          <div className="ap-header-actions">
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
              {t("admin.new_event")}
            </button>
            <button className="ap-icon-btn" onClick={onClose} title={t("admin.close")}>✕</button>
          </div>
        </div>

        {/* ── Event list ──────────────────────────────────────────────────── */}
        <div className="ap-list">
          {!loading && events.length === 0 && (
            <div className="ap-empty">{t("admin.empty")}</div>
          )}

          {events.map((ev) => {
            const totalReports = stats[ev.id]?.total_reports ?? null;
            const isActive = ev.id === activeCrisisId;
            const isConfirmingDelete = deleteConfirmId === ev.id;
            const isConfirmingPurge = purgeConfirmId === ev.id;

            return (
              <div
                key={ev.id}
                className={`ec-card${isActive ? " ec-card--selected" : ""}`}
              >
                {/* Col 1, rows 1-2: emoji glyph */}
                <div className="ec-glyph">{NATURE_EMOJI[ev.crisis_nature] ?? "🌐"}</div>

                {/* Col 2, row 1: event name + Viewing badge */}
                <div className="ec-head">
                  <div className="ec-title">
                    <span className="ec-name">{ev.name}</span>
                    {isActive && (
                      <span className="badge badge-viewing">{t("admin.viewing")}</span>
                    )}
                  </div>
                </div>

                {/* Col 3, row 1: report count + status badges */}
                <div className="ec-status">
                  {totalReports !== null && (
                    <span className={`badge badge-reports${totalReports === 0 ? " is-empty" : ""}`}>
                      {totalReports === 0
                        ? t("admin.no_reports_badge")
                        : t(totalReports === 1 ? "admin.reports_badge_one" : "admin.reports_badge_other", { count: totalReports })}
                    </span>
                  )}
                  {ev.status === "active"   && <span className="badge badge-status-active">Active</span>}
                  {ev.status === "archived" && <span className="badge badge-status-archived">Archived</span>}
                  {ev.status === "paused"   && <span className="badge badge-status-paused">Paused</span>}
                </div>

                {/* Col 2, row 2: slug · region · created date · share pills */}
                <div className="ec-meta">
                  <span className="ec-slug">{ev.id}</span>
                  <span className="ec-dot">·</span>
                  <span>{ev.country_code}{ev.region ? ` / ${ev.region}` : ""}</span>
                  <span className="ec-dot">·</span>
                  <span>{t("admin.created", { date: fmt(ev.created_at, i18n.language) })}</span>
                  <MetaCopyBtn
                    url={pwaLink(ev.id)}
                    label="PWA"
                    icon={
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ marginRight: 3 }}>
                        <rect x="5" y="2" width="14" height="20" rx="2" stroke="currentColor" strokeWidth="2"/>
                        <circle cx="12" cy="17" r="1.2" fill="currentColor"/>
                      </svg>
                    }
                  />
                  <MetaCopyBtn
                    url={botLink(ev.id)}
                    label="Bot"
                    icon={
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ marginRight: 3 }}>
                        <path d="M21 5L2 12.5l7 1M21 5l-6.5 15L9 13.5M21 5L9 13.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    }
                  />
                </div>

                {/* Row 3, all cols: action shelf */}
                <div className="ec-shelf">
                  {/* Left cluster: Open · Schema · Reports | Export */}
                  <div className="ec-shelf-primary">
                    <div className="ec-group">
                      {!isActive && (
                        <button
                          className="btn btn-sm"
                          onClick={() => { onSwitchCrisis(ev.id); onClose(); }}
                        >
                          Open
                        </button>
                      )}
                      <button className="btn btn-sm" onClick={() => setSchemaEditorId(ev.id)}>
                        Schema
                      </button>
                      <button className="btn btn-sm" onClick={() => setReportsModalId(ev.id)}>
                        Reports
                      </button>
                    </div>

                    <div className="ec-divider-v" />

                    <div className="ec-group">
                      <span className="ec-group-label">Export</span>
                      {(["geojson", "csv", "shapefile"] as const).map((f) => (
                        <a
                          key={f}
                          href={exportUrl(ev.id, f)}
                          className="btn btn-sm"
                          download
                        >
                          {f === "geojson" ? "GeoJSON" : f === "shapefile" ? "Shapefile" : "CSV"}
                        </a>
                      ))}
                    </div>

                  </div>

                  {/* Right cluster: Archive · Purge · Delete (separated by pseudo-divider) */}
                  <div className="ec-danger-group">
                    {ev.status === "active" ? (
                      <button
                        className="btn btn-sm btn-warn"
                        disabled={updating === ev.id}
                        onClick={() => updateStatus(ev.id, "archived")}
                      >
                        {updating === ev.id ? "…" : t("admin.archive")}
                      </button>
                    ) : (
                      <button
                        className="btn btn-sm"
                        disabled={updating === ev.id}
                        onClick={() => updateStatus(ev.id, "active")}
                      >
                        {updating === ev.id ? "…" : t("admin.reactivate")}
                      </button>
                    )}

                    <button
                      className={`btn btn-sm btn-danger${isConfirmingPurge ? " is-confirming" : ""}`}
                      disabled={purging === ev.id}
                      onClick={() => {
                        if (isConfirmingPurge) {
                          handlePurge(ev.id);
                        } else {
                          setPurgeResult(null);
                          setPurgeConfirmId(ev.id);
                          setDeleteConfirmId(null);
                        }
                      }}
                      title={isConfirmingPurge ? "Click again to confirm" : "Permanently delete all reports and photos"}
                    >
                      {purging === ev.id ? "…" : isConfirmingPurge ? "Confirm purge" : "Purge data"}
                    </button>

                    <button
                      className={`btn btn-sm btn-danger${isConfirmingDelete ? " is-confirming" : ""}`}
                      disabled={deleting === ev.id}
                      onClick={() => {
                        if (isConfirmingDelete) {
                          handleDeleteEvent(ev.id);
                        } else {
                          setDeleteConfirmId(ev.id);
                          setPurgeConfirmId(null);
                        }
                      }}
                      title={isConfirmingDelete ? "Click again to confirm" : "Delete event and all its data"}
                    >
                      {deleting === ev.id ? "…" : isConfirmingDelete ? "Confirm delete" : "Delete"}
                    </button>
                  </div>
                </div>

                {/* Purge success notification */}
                {purgeResult?.id === ev.id && (
                  <div className="ec-purge-result">
                    ✓ Purged {purgeResult.reports} report{purgeResult.reports !== 1 ? "s" : ""} and {purgeResult.blobs} photo{purgeResult.blobs !== 1 ? "s" : ""}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Panel footer ────────────────────────────────────────────────── */}
        <div className="ap-panel-footer">
          <button
            className="btn btn-sm"
            onClick={() => { sessionStorage.removeItem("admin_key"); setAdminKey(""); }}
          >
            {t("admin.sign_out")}
          </button>
          <button className="btn btn-sm" onClick={load}>
            {t("admin.refresh")}
          </button>
          <span className="ap-footer-meta">
            {loading
              ? <span className="ap-footer-loading">Loading…</span>
              : <>{events.length} event{events.length !== 1 ? "s" : ""}</>
            }
          </span>
        </div>
      </div>

      {showCreate && (
        <CreateModal
          adminKey={adminKey}
          onCreated={load}
          onClose={() => setShowCreate(false)}
        />
      )}

      {schemaEditorId && (
        <SchemaEditor
          crisisEventId={schemaEditorId}
          adminKey={adminKey}
          onClose={() => setSchemaEditorId(null)}
        />
      )}

      {reportsModalId && (
        <ReportsModal
          crisisEventId={reportsModalId}
          adminKey={adminKey}
          onClose={() => setReportsModalId(null)}
        />
      )}
    </div>
  );
}
