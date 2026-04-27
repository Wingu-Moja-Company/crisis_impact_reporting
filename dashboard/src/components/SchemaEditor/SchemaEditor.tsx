/**
 * SchemaEditor — full schema management UI for a crisis event.
 *
 * Sections:
 *   1. System Fields — damage_level (labels only) + infrastructure_type (add/remove options)
 *   2. Custom Fields — add / edit / delete / reorder
 *   3. Version history — read-only list of past published versions
 *   4. Publish — POST /admin/crisis-events/{id}/schema
 */

import { useState, useEffect, useCallback } from "react";
import type { FormSchema, SchemaField, SchemaOption } from "../../hooks/useSchema";
import { getSchemaLabel } from "../../hooks/useSchema";
import { FieldEditorModal } from "./FieldEditorModal";
import "./SchemaEditor.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const LANGS = ["en", "fr", "ar", "sw", "es", "zh"] as const;
const LANG_NAMES: Record<string, string> = {
  en: "English", fr: "Français", ar: "العربية",
  sw: "Kiswahili", es: "Español", zh: "中文",
};

// ── Helpers ─────────────────────────────────────────────────────────────────

function emptyLabels(): Record<string, string> {
  return Object.fromEntries(LANGS.map((l) => [l, ""]));
}

interface VersionMeta {
  version: number;
  published_at: string;
  published_by?: string;
  custom_field_count: number;
}

// ── Sub-components ───────────────────────────────────────────────────────────

/** Editable label grid for a field (6 languages) */
function LabelGrid({
  labels,
  onChange,
}: {
  labels: Record<string, string>;
  onChange: (lang: string, val: string) => void;
}) {
  return (
    <div className="sef-lang-grid">
      {LANGS.map((lang) => (
        <label key={lang} className="ap-label">
          {LANG_NAMES[lang]}
          <input
            className="ap-input"
            value={labels[lang] ?? ""}
            onChange={(e) => onChange(lang, e.target.value)}
            placeholder={lang === "en" ? "Required" : "Optional"}
          />
        </label>
      ))}
    </div>
  );
}

/** One infrastructure type option row */
function InfraOptionRow({
  opt,
  onLabelChange,
  onRemove,
}: {
  opt: SchemaOption;
  onLabelChange: (lang: string, val: string) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="sef-infra-row">
      <div className="sef-infra-row-header">
        <code className="sef-option-id">{opt.value}</code>
        <span className="sef-option-en">{opt.labels.en || "—"}</span>
        <button
          type="button"
          className="ap-btn ap-btn--sm ap-btn--ghost"
          onClick={() => setExpanded((x) => !x)}
        >
          {expanded ? "▲" : "▼"} Labels
        </button>
        <button
          type="button"
          className="ap-icon-btn"
          onClick={onRemove}
          title="Remove option"
        >
          🗑
        </button>
      </div>
      {expanded && (
        <div className="sef-infra-labels">
          <LabelGrid labels={opt.labels} onChange={onLabelChange} />
        </div>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface Props {
  crisisEventId: string;
  adminKey: string;
  onClose: () => void;
}

export function SchemaEditor({ crisisEventId, adminKey, onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [history, setHistory] = useState<VersionMeta[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [publishState, setPublishState] = useState<"idle" | "publishing" | "done" | "error">("idle");
  const [publishError, setPublishError] = useState<string | null>(null);

  // Local editable copy of the schema (cloned from fetched version)
  const [draft, setDraft] = useState<FormSchema | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<"system" | "custom" | "history">("custom");
  const [editingField, setEditingField] = useState<SchemaField | null | "new">(null);
  const [newInfraValue, setNewInfraValue] = useState("");
  const [newInfraEn, setNewInfraEn] = useState("");

  const authHeaders: Record<string, string> = adminKey
    ? { "X-Admin-Key": adminKey, "X-API-Key": adminKey }
    : {};

  // ── Load schema ────────────────────────────────────────────────────────────
  const loadSchema = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/v1/crisis-events/${encodeURIComponent(crisisEventId)}/schema`,
        { headers: authHeaders },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: FormSchema = await res.json();
      setSchema(data);
      setDraft(JSON.parse(JSON.stringify(data))); // deep clone for editing
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [crisisEventId, adminKey]);

  // ── Load history ───────────────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/v1/admin/crisis-events/${encodeURIComponent(crisisEventId)}/schema/history`,
        { headers: authHeaders },
      );
      if (res.ok) setHistory(await res.json());
    } catch { /* ignore */ }
    finally { setHistoryLoading(false); }
  }, [crisisEventId, adminKey]);

  useEffect(() => { loadSchema(); }, [loadSchema]);
  useEffect(() => {
    if (activeTab === "history") loadHistory();
  }, [activeTab, loadHistory]);

  // ── Draft mutators ─────────────────────────────────────────────────────────

  function setDamageOptionLabel(optKey: string, lang: string, val: string) {
    setDraft((d) => {
      if (!d) return d;
      const opts = { ...(d.system_fields.damage_level.options as Record<string, Record<string, string>>) };
      opts[optKey] = { ...(opts[optKey] ?? {}), [lang]: val };
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          damage_level: { ...d.system_fields.damage_level, options: opts },
        },
      };
    });
  }

  function setDamageLevelQuestionLabel(lang: string, val: string) {
    setDraft((d) => {
      if (!d) return d;
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          damage_level: {
            ...d.system_fields.damage_level,
            labels: { ...d.system_fields.damage_level.labels, [lang]: val },
          },
        },
      };
    });
  }

  function setInfraTypeQuestionLabel(lang: string, val: string) {
    setDraft((d) => {
      if (!d) return d;
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          infrastructure_type: {
            ...d.system_fields.infrastructure_type,
            labels: { ...d.system_fields.infrastructure_type.labels, [lang]: val },
          },
        },
      };
    });
  }

  function setInfraOptionLabel(value: string, lang: string, val: string) {
    setDraft((d) => {
      if (!d) return d;
      const opts = (d.system_fields.infrastructure_type.options as SchemaOption[]).map((o) =>
        o.value === value ? { ...o, labels: { ...o.labels, [lang]: val } } : o
      );
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          infrastructure_type: { ...d.system_fields.infrastructure_type, options: opts },
        },
      };
    });
  }

  function removeInfraOption(value: string) {
    setDraft((d) => {
      if (!d) return d;
      const opts = (d.system_fields.infrastructure_type.options as SchemaOption[])
        .filter((o) => o.value !== value);
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          infrastructure_type: { ...d.system_fields.infrastructure_type, options: opts },
        },
      };
    });
  }

  function addInfraOption() {
    const val = newInfraValue.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
    if (!val || !newInfraEn.trim()) return;
    setDraft((d) => {
      if (!d) return d;
      const opts = [...(d.system_fields.infrastructure_type.options as SchemaOption[])];
      if (opts.some((o) => o.value === val)) return d;
      opts.push({ value: val, labels: { ...emptyLabels(), en: newInfraEn.trim() } });
      return {
        ...d,
        system_fields: {
          ...d.system_fields,
          infrastructure_type: { ...d.system_fields.infrastructure_type, options: opts },
        },
      };
    });
    setNewInfraValue("");
    setNewInfraEn("");
  }

  function saveCustomField(updated: SchemaField) {
    setDraft((d) => {
      if (!d) return d;
      const existing = d.custom_fields.some((f) => f.id === updated.id);
      const fields = existing
        ? d.custom_fields.map((f) => f.id === updated.id ? updated : f)
        : [...d.custom_fields, updated];
      return { ...d, custom_fields: fields.sort((a, b) => a.order - b.order) };
    });
    setEditingField(null);
  }

  function removeCustomField(id: string) {
    if (!window.confirm(`Remove field "${id}"? Existing report data will still be shown but the field won't appear in new submissions.`)) return;
    setDraft((d) => {
      if (!d) return d;
      return { ...d, custom_fields: d.custom_fields.filter((f) => f.id !== id) };
    });
  }

  function moveField(id: string, dir: -1 | 1) {
    setDraft((d) => {
      if (!d) return d;
      const fields = [...d.custom_fields].sort((a, b) => a.order - b.order);
      const idx = fields.findIndex((f) => f.id === id);
      if (idx < 0) return d;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= fields.length) return d;
      // Swap orders
      const tmp = fields[idx].order;
      fields[idx] = { ...fields[idx], order: fields[newIdx].order };
      fields[newIdx] = { ...fields[newIdx], order: tmp };
      return { ...d, custom_fields: fields };
    });
  }

  // ── Publish ────────────────────────────────────────────────────────────────

  async function handlePublish() {
    if (!draft) return;
    if (!window.confirm(`Publish a new schema version for "${crisisEventId}"? This is immutable — all new submissions will use this version.`)) return;
    setPublishState("publishing");
    setPublishError(null);
    try {
      const res = await fetch(
        `${API_BASE}/v1/admin/crisis-events/${encodeURIComponent(crisisEventId)}/schema`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders },
          body: JSON.stringify({
            system_fields: draft.system_fields,
            custom_fields: draft.custom_fields,
          }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`);
      setPublishState("done");
      await loadSchema();
      if (activeTab === "history") await loadHistory();
    } catch (e) {
      setPublishError(e instanceof Error ? e.message : String(e));
      setPublishState("error");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="ap-overlay">
        <div className="sef-panel">
          <div className="sef-loading">Loading schema…</div>
        </div>
      </div>
    );
  }

  if (error || !draft) {
    return (
      <div className="ap-overlay">
        <div className="sef-panel">
          <div className="sef-error">Failed to load schema: {error}</div>
          <button className="ap-btn ap-btn--ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  const sortedFields = [...(draft.custom_fields ?? [])].sort((a, b) => a.order - b.order);
  const nextOrder = sortedFields.length > 0 ? Math.max(...sortedFields.map((f) => f.order)) + 1 : 1;
  const infraOptions = (draft.system_fields.infrastructure_type?.options as SchemaOption[]) ?? [];
  const damageOpts = (draft.system_fields.damage_level?.options as Record<string, Record<string, string>>) ?? {};

  return (
    <div className="ap-overlay">
      <div className="sef-panel">
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="sef-header">
          <div>
            <h1 className="sef-title">📋 Schema Editor</h1>
            <p className="sef-sub">
              <code>{crisisEventId}</code>
              {schema?.version != null && (
                <span className="sef-version-badge">current: v{schema.version}</span>
              )}
            </p>
          </div>
          <button className="ap-icon-btn" onClick={onClose} title="Close">✕</button>
        </div>

        {/* ── Tabs ────────────────────────────────────────────────────── */}
        <div className="sef-tabs">
          {(["custom", "system", "history"] as const).map((tab) => (
            <button
              key={tab}
              className={`sef-tab${activeTab === tab ? " sef-tab--active" : ""}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === "custom" ? "Custom Fields" : tab === "system" ? "System Fields" : "Version History"}
            </button>
          ))}
        </div>

        {/* ── Tab: Custom Fields ───────────────────────────────────────── */}
        {activeTab === "custom" && (
          <div className="sef-body">
            <div className="sef-section-header">
              <span>Custom Fields ({sortedFields.length})</span>
              <button
                className="ap-btn ap-btn--primary ap-btn--sm"
                onClick={() => setEditingField("new")}
              >
                + Add Field
              </button>
            </div>

            {sortedFields.length === 0 && (
              <div className="sef-empty">No custom fields. Click "Add Field" to get started.</div>
            )}

            {sortedFields.map((field, idx) => (
              <div key={field.id} className="sef-field-row">
                <div className="sef-field-info">
                  <div className="sef-field-top">
                    <code className="sef-field-id">{field.id}</code>
                    <span className="sef-field-type">{field.type}</span>
                    {field.required
                      ? <span className="sef-badge sef-badge--req">required</span>
                      : <span className="sef-badge sef-badge--opt">optional</span>
                    }
                  </div>
                  <div className="sef-field-label">
                    {getSchemaLabel(field.labels, "en") || <em>No English label</em>}
                  </div>
                  {field.options && (
                    <div className="sef-field-opts">
                      {field.options.map((o) => (
                        <span key={o.value} className="sef-opt-chip">
                          {getSchemaLabel(o.labels, "en") || o.value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="sef-field-actions">
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    onClick={() => moveField(field.id, -1)}
                    disabled={idx === 0}
                    title="Move up"
                  >↑</button>
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    onClick={() => moveField(field.id, 1)}
                    disabled={idx === sortedFields.length - 1}
                    title="Move down"
                  >↓</button>
                  <button
                    className="ap-btn ap-btn--sm ap-btn--ghost"
                    onClick={() => setEditingField(field)}
                  >Edit</button>
                  <button
                    className="ap-btn ap-btn--sm ap-btn--warn"
                    onClick={() => removeCustomField(field.id)}
                  >Remove</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Tab: System Fields ───────────────────────────────────────── */}
        {activeTab === "system" && (
          <div className="sef-body">
            {/* Damage Level */}
            <div className="sef-section-title">
              🔒 Damage Level
              <span className="sef-locked">values locked (minimal / partial / complete)</span>
            </div>
            <div className="sef-section-sub">Question label</div>
            <LabelGrid
              labels={draft.system_fields.damage_level.labels as Record<string, string>}
              onChange={setDamageLevelQuestionLabel}
            />
            {(["minimal", "partial", "complete"] as const).map((lvl) => (
              <div key={lvl} className="sef-damage-option">
                <div className="sef-section-sub">"{lvl}" option label</div>
                <LabelGrid
                  labels={damageOpts[lvl] ?? emptyLabels()}
                  onChange={(lang, val) => setDamageOptionLabel(lvl, lang, val)}
                />
              </div>
            ))}

            {/* Infrastructure Type */}
            <div className="sef-section-title" style={{ marginTop: 24 }}>
              Infrastructure Type
              <span className="sef-locked">multiselect — options editable</span>
            </div>
            <div className="sef-section-sub">Question label</div>
            <LabelGrid
              labels={draft.system_fields.infrastructure_type.labels as Record<string, string>}
              onChange={setInfraTypeQuestionLabel}
            />
            <div className="sef-section-sub" style={{ marginTop: 12 }}>Options</div>
            {infraOptions.map((opt) => (
              <InfraOptionRow
                key={opt.value}
                opt={opt}
                onLabelChange={(lang, val) => setInfraOptionLabel(opt.value, lang, val)}
                onRemove={() => removeInfraOption(opt.value)}
              />
            ))}
            <div className="sef-add-infra">
              <input
                className="ap-input ap-mono ap-short"
                value={newInfraValue}
                onChange={(e) => setNewInfraValue(e.target.value)}
                placeholder="option_id"
              />
              <input
                className="ap-input ap-grow"
                value={newInfraEn}
                onChange={(e) => setNewInfraEn(e.target.value)}
                placeholder="English label"
              />
              <button
                type="button"
                className="ap-btn ap-btn--primary ap-btn--sm"
                onClick={addInfraOption}
                disabled={!newInfraValue.trim() || !newInfraEn.trim()}
              >
                + Add
              </button>
            </div>
          </div>
        )}

        {/* ── Tab: Version History ─────────────────────────────────────── */}
        {activeTab === "history" && (
          <div className="sef-body">
            <div className="sef-section-header">
              <span>Published Versions</span>
              <button className="ap-btn ap-btn--ghost ap-btn--sm" onClick={loadHistory}>
                Refresh
              </button>
            </div>
            {historyLoading && <div className="sef-loading">Loading history…</div>}
            {!historyLoading && history.length === 0 && (
              <div className="sef-empty">No published versions yet.</div>
            )}
            {history.map((v) => (
              <div key={v.version} className="sef-history-row">
                <div>
                  <span className="sef-version-badge">v{v.version}</span>
                  {v.version === schema?.version && (
                    <span className="sef-badge sef-badge--current">current</span>
                  )}
                </div>
                <div className="sef-history-meta">
                  <span>{new Date(v.published_at).toLocaleString()}</span>
                  {v.published_by && <span>by {v.published_by}</span>}
                  <span>{v.custom_field_count} custom fields</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Footer: publish ──────────────────────────────────────────── */}
        <div className="sef-footer">
          {publishState === "done" && (
            <span className="sef-pub-ok">✓ Published successfully!</span>
          )}
          {publishState === "error" && publishError && (
            <span className="sef-pub-err">⚠ {publishError}</span>
          )}
          <div className="sef-footer-actions">
            <button className="ap-btn ap-btn--ghost" onClick={onClose}>Close</button>
            <button
              className="ap-btn ap-btn--primary"
              disabled={publishState === "publishing"}
              onClick={handlePublish}
            >
              {publishState === "publishing" ? "Publishing…" : "Publish New Version →"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Field editor modal ───────────────────────────────────────────── */}
      {editingField !== null && (
        <FieldEditorModal
          field={editingField === "new" ? null : editingField}
          nextOrder={nextOrder}
          onSave={saveCustomField}
          onClose={() => setEditingField(null)}
        />
      )}
    </div>
  );
}
