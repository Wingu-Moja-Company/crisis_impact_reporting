import { useState, useEffect, useCallback } from "react";
import "./AdminPanel.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  { value: "flood",      label: "Flood" },
  { value: "earthquake", label: "Earthquake" },
  { value: "conflict",   label: "Conflict" },
  { value: "hurricane",  label: "Hurricane / Cyclone" },
  { value: "wildfire",   label: "Wildfire" },
  { value: "generic",    label: "Generic (no extra fields)" },
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

function exportUrl(eventId: string, format: "geojson" | "csv" | "shapefile"): string {
  const key = import.meta.env.VITE_EXPORT_API_KEY ?? "";
  const base = `${API_BASE}/v1/reports?crisis_event_id=${encodeURIComponent(eventId)}&format=${format}&limit=5000`;
  return key ? `${base}&_key=${encodeURIComponent(key)}` : base;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatsBadge({ stats }: { stats: EventStats | null }) {
  if (!stats) return <span className="ap-badge ap-badge--grey">Loading…</span>;
  const total = stats.total_reports;
  if (total === 0) return <span className="ap-badge ap-badge--grey">No reports</span>;
  return (
    <span className="ap-badge ap-badge--blue" title={JSON.stringify(stats.by_damage_level, null, 2)}>
      {total} report{total !== 1 ? "s" : ""}
    </span>
  );
}

interface CreateModalProps {
  adminKey: string;
  onCreated: () => void;
  onClose: () => void;
}

function CreateModal({ adminKey, onCreated, onClose }: CreateModalProps) {
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

  // Auto-generate ID from name
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
          <h2>New Crisis Event</h2>
          <button className="ap-icon-btn" onClick={onClose}>✕</button>
        </div>
        <form className="ap-form" onSubmit={handleSubmit}>
          <label className="ap-label">
            Event name *
            <input
              className="ap-input"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Kenya Nairobi Floods — May 2026"
              required
            />
          </label>

          <label className="ap-label">
            Event ID (slug) *
            <input
              className="ap-input ap-mono"
              value={form.id}
              onChange={(e) => set("id", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
              placeholder="e.g. ke-floods-2026-05"
              required
              pattern="[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]"
              title="Lowercase letters, numbers, hyphens only (3–50 chars)"
            />
            <span className="ap-hint">Used in API calls and URLs — cannot be changed later</span>
          </label>

          <div className="ap-row">
            <label className="ap-label">
              Country code *
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
              Region
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
              Crisis type *
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
              Form schema
              <select className="ap-input" value={form.schema_type}
                onChange={(e) => set("schema_type", e.target.value)}>
                {SCHEMA_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="ap-section-title">Dashboard map centre (optional)</div>
          <div className="ap-row">
            <label className="ap-label ap-grow">
              Latitude
              <input className="ap-input" type="number" step="any"
                value={form.map_lat} onChange={(e) => set("map_lat", e.target.value)}
                placeholder="-1.2577" />
            </label>
            <label className="ap-label ap-grow">
              Longitude
              <input className="ap-input" type="number" step="any"
                value={form.map_lon} onChange={(e) => set("map_lon", e.target.value)}
                placeholder="36.8614" />
            </label>
          </div>

          {error && <div className="ap-error">⚠ {error}</div>}

          <div className="ap-modal-actions">
            <button type="button" className="ap-btn ap-btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="ap-btn ap-btn--primary" disabled={saving}>
              {saving ? "Creating…" : "Create event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AdminPanel
// ---------------------------------------------------------------------------

interface Props {
  onClose: () => void;
  onSwitchCrisis: (id: string) => void;
  activeCrisisId: string;
}

export function AdminPanel({ onClose, onSwitchCrisis, activeCrisisId }: Props) {
  // Auth gate
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem("admin_key") ?? "");
  const [keyInput, setKeyInput] = useState("");
  const [authError, setAuthError] = useState(false);
  const isAuthed = !import.meta.env.VITE_ADMIN_KEY_REQUIRED || adminKey;

  // Data
  const [events, setEvents] = useState<CrisisEvent[]>([]);
  const [stats, setStats] = useState<Record<string, EventStats>>({});
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  // Status update state
  const [updating, setUpdating] = useState<string | null>(null);

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

      // Fetch stats for each event in parallel
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

  // ---------------------------------------------------------------------------
  // Auth gate
  // ---------------------------------------------------------------------------
  if (!isAuthed || authError) {
    return (
      <div className="ap-overlay">
        <div className="ap-auth-card">
          <div className="ap-auth-icon">🔐</div>
          <h2>Admin access</h2>
          <p>Enter your admin API key to continue.</p>
          {authError && <div className="ap-error">Invalid key — try again.</div>}
          <form onSubmit={handleAuth}>
            <input
              className="ap-input"
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="Admin API key"
              autoFocus
            />
            <div className="ap-modal-actions">
              <button type="button" className="ap-btn ap-btn--ghost" onClick={onClose}>Cancel</button>
              <button type="submit" className="ap-btn ap-btn--primary" disabled={!keyInput}>Unlock</button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Main panel
  // ---------------------------------------------------------------------------
  return (
    <div className="ap-overlay">
      <div className="ap-panel">
        {/* Header */}
        <div className="ap-panel-header">
          <div>
            <h1 className="ap-panel-title">⚙️ Crisis Event Admin</h1>
            <p className="ap-panel-sub">Create, manage and export crisis events</p>
          </div>
          <div className="ap-header-actions">
            <button className="ap-btn ap-btn--primary" onClick={() => setShowCreate(true)}>
              + New event
            </button>
            <button className="ap-icon-btn" onClick={onClose} title="Close admin panel">✕</button>
          </div>
        </div>

        {/* Events list */}
        <div className="ap-list">
          {loading && <div className="ap-loading">Loading events…</div>}
          {!loading && events.length === 0 && (
            <div className="ap-empty">No crisis events found. Create one to get started.</div>
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
                    <span className="ap-badge ap-badge--green">Viewing</span>
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
                <span>Created {fmt(ev.created_at)}</span>
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
                    View in dashboard
                  </button>
                )}
                {ev.status === "active" ? (
                  <button
                    className="ap-btn ap-btn--sm ap-btn--warn"
                    disabled={updating === ev.id}
                    onClick={() => updateStatus(ev.id, "archived")}
                  >
                    {updating === ev.id ? "…" : "Archive"}
                  </button>
                ) : (
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    disabled={updating === ev.id}
                    onClick={() => updateStatus(ev.id, "active")}
                  >
                    {updating === ev.id ? "…" : "Reactivate"}
                  </button>
                )}
                <div className="ap-export-group">
                  <span className="ap-export-label">Export:</span>
                  {(["geojson", "csv", "shapefile"] as const).map((fmt) => (
                    <a
                      key={fmt}
                      href={exportUrl(ev.id, fmt)}
                      className="ap-btn ap-btn--sm ap-btn--ghost"
                      download
                    >
                      {fmt.toUpperCase()}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="ap-panel-footer">
          <button
            className="ap-btn ap-btn--ghost ap-btn--sm"
            onClick={() => { sessionStorage.removeItem("admin_key"); setAdminKey(""); }}
          >
            🔒 Sign out
          </button>
          <button className="ap-btn ap-btn--ghost ap-btn--sm" onClick={load}>
            ↺ Refresh
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
    </div>
  );
}
