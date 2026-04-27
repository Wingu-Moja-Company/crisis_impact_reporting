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

const STATUS_COLOURS: Record<string, string> = {
  active:   "#16a34a",
  archived: "#6b7280",
  paused:   "#d97706",
};

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

function StatsBadge({ stats }: { stats: EventStats | null }) {
  const { t } = useTranslation();
  if (!stats) return <span className="ap-badge ap-badge--grey">{t("admin.loading_badge")}</span>;
  const total = stats.total_reports;
  if (total === 0) return <span className="ap-badge ap-badge--grey">{t("admin.no_reports_badge")}</span>;
  return (
    <span className="ap-badge ap-badge--blue" title={JSON.stringify(stats.by_damage_level, null, 2)}>
      {t(total === 1 ? "admin.reports_badge_one" : "admin.reports_badge_other", { count: total })}
    </span>
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
        <div className="ap-panel-header">
          <div>
            <h1 className="ap-panel-title">⚙️ {t("admin.panel_title")}</h1>
            <p className="ap-panel-sub">{t("admin.panel_sub")}</p>
          </div>
          <div className="ap-header-actions">
            <button className="ap-btn ap-btn--primary" onClick={() => setShowCreate(true)}>
              {t("admin.new_event")}
            </button>
            <button className="ap-icon-btn" onClick={onClose} title={t("admin.close")}>✕</button>
          </div>
        </div>

        <div className="ap-list">
          {loading && <div className="ap-loading">{t("admin.loading")}</div>}
          {!loading && events.length === 0 && (
            <div className="ap-empty">{t("admin.empty")}</div>
          )}
          {events.map((ev) => (
            <div
              key={ev.id}
              className={`ap-card${ev.id === activeCrisisId ? " ap-card--active" : ""}`}
            >
              <div className="ap-card-top">
                <div className="ap-card-title">
                  <span className="ap-nature-emoji">{NATURE_EMOJI[ev.crisis_nature] ?? "🌐"}</span>
                  <span className="ap-card-name">{ev.name}</span>
                  {ev.id === activeCrisisId && (
                    <span className="ap-badge ap-badge--green">{t("admin.viewing")}</span>
                  )}
                  <span
                    className="ap-status-dot"
                    style={{ background: STATUS_COLOURS[ev.status] ?? "#888" }}
                    title={ev.status}
                  />
                </div>
                <StatsBadge stats={stats[ev.id] ?? null} />
              </div>

              <div className="ap-card-meta">
                <code className="ap-card-id">{ev.id}</code>
                <span>·</span>
                <span>{ev.country_code}{ev.region ? ` / ${ev.region}` : ""}</span>
                <span>·</span>
                <span>{t("admin.created", { date: fmt(ev.created_at, i18n.language) })}</span>
                <span
                  className="ap-status-label"
                  style={{ color: STATUS_COLOURS[ev.status] ?? "#888" }}
                >
                  {ev.status}
                </span>
              </div>

              <div className="ap-card-actions">
                {ev.id !== activeCrisisId && (
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    onClick={() => { onSwitchCrisis(ev.id); onClose(); }}
                  >
                    {t("admin.view_dashboard")}
                  </button>
                )}
                <button
                  className="ap-btn ap-btn--sm ap-btn--ghost"
                  onClick={() => setSchemaEditorId(ev.id)}
                  title="Edit form schema"
                >
                  📋 {t("admin.schema_editor", { defaultValue: "Schema" })}
                </button>
                {ev.status === "active" ? (
                  <button
                    className="ap-btn ap-btn--sm ap-btn--warn"
                    disabled={updating === ev.id}
                    onClick={() => updateStatus(ev.id, "archived")}
                  >
                    {updating === ev.id ? "…" : t("admin.archive")}
                  </button>
                ) : (
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    disabled={updating === ev.id}
                    onClick={() => updateStatus(ev.id, "active")}
                  >
                    {updating === ev.id ? "…" : t("admin.reactivate")}
                  </button>
                )}
                <div className="ap-export-group">
                  <span className="ap-export-label">{t("admin.export_label")}</span>
                  {(["geojson", "csv", "shapefile"] as const).map((f) => (
                    <a
                      key={f}
                      href={exportUrl(ev.id, f)}
                      className="ap-btn ap-btn--sm ap-btn--ghost"
                      download
                    >
                      {f.toUpperCase()}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="ap-panel-footer">
          <button
            className="ap-btn ap-btn--ghost ap-btn--sm"
            onClick={() => { sessionStorage.removeItem("admin_key"); setAdminKey(""); }}
          >
            {t("admin.sign_out")}
          </button>
          <button className="ap-btn ap-btn--ghost ap-btn--sm" onClick={load}>
            {t("admin.refresh")}
          </button>
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
    </div>
  );
}
