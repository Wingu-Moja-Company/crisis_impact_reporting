/**
 * FieldEditorModal — add or edit a custom schema field.
 * Used inside SchemaEditor. Supports all field types:
 *   select | multiselect | boolean | text | number
 */

import { useState } from "react";
import type { SchemaField, SchemaOption } from "../../hooks/useSchema";

const LANGS = ["en", "fr", "ar", "sw", "es", "zh"] as const;
const LANG_NAMES: Record<string, string> = {
  en: "English", fr: "Français", ar: "العربية",
  sw: "Kiswahili", es: "Español", zh: "中文",
};

function emptyLabels(): Record<string, string> {
  return Object.fromEntries(LANGS.map((l) => [l, ""]));
}

function emptyOption(): SchemaOption {
  return { value: "", labels: emptyLabels() };
}

interface Props {
  /** Existing field to edit — null/undefined for new field */
  field?: SchemaField | null;
  /** Highest current order value (new field gets order+1) */
  nextOrder: number;
  onSave: (field: SchemaField) => void;
  onClose: () => void;
}

export function FieldEditorModal({ field, nextOrder, onSave, onClose }: Props) {
  const isNew = !field;

  const [id, setId] = useState(field?.id ?? "");
  const [type, setType] = useState<SchemaField["type"]>(field?.type ?? "select");
  const [required, setRequired] = useState(field?.required ?? true);
  const [labels, setLabels] = useState<Record<string, string>>(
    field?.labels ?? emptyLabels()
  );
  const [options, setOptions] = useState<SchemaOption[]>(
    field?.options ? [...field.options] : [emptyOption()]
  );
  const [error, setError] = useState<string | null>(null);

  const hasOptions = type === "select" || type === "multiselect";

  function setLabel(lang: string, val: string) {
    setLabels((prev) => ({ ...prev, [lang]: val }));
    setError(null);
  }

  function setOptionValue(idx: number, val: string) {
    setOptions((prev) => prev.map((o, i) =>
      i === idx ? { ...o, value: val.toLowerCase().replace(/[^a-z0-9_]/g, "_") } : o
    ));
  }

  function setOptionLabel(idx: number, lang: string, val: string) {
    setOptions((prev) => prev.map((o, i) =>
      i === idx ? { ...o, labels: { ...o.labels, [lang]: val } } : o
    ));
  }

  function addOption() {
    setOptions((prev) => [...prev, emptyOption()]);
  }

  function removeOption(idx: number) {
    setOptions((prev) => prev.filter((_, i) => i !== idx));
  }

  function handleSave() {
    if (!id.trim()) { setError("Field ID is required"); return; }
    if (!/^[a-z][a-z0-9_]*$/.test(id)) {
      setError("Field ID must start with a letter and contain only lowercase letters, numbers, underscore");
      return;
    }
    if (!labels.en?.trim()) { setError("English label is required"); return; }
    if (hasOptions) {
      if (options.length === 0) { setError("At least one option is required"); return; }
      for (const opt of options) {
        if (!opt.value.trim()) { setError("All option IDs must be filled"); return; }
        if (!opt.labels.en?.trim()) { setError("English label required for all options"); return; }
      }
      const vals = options.map((o) => o.value);
      if (new Set(vals).size !== vals.length) { setError("Option IDs must be unique"); return; }
    }

    onSave({
      id: id.trim(),
      type,
      required,
      order: field?.order ?? nextOrder,
      labels,
      ...(hasOptions ? { options } : {}),
    });
  }

  return (
    <div className="ap-modal-backdrop" onClick={onClose}>
      <div className="ap-modal sef-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ap-modal-header">
          <h2>{isNew ? "Add Custom Field" : `Edit Field: ${field!.id}`}</h2>
          <button className="ap-icon-btn" onClick={onClose}>✕</button>
        </div>

        <div className="sef-scroll">
          {/* ── Field ID + type ─────────────────────────────────────────── */}
          <div className="ap-row">
            <label className="ap-label ap-grow">
              Field ID
              <input
                className="ap-input ap-mono"
                value={id}
                onChange={(e) => { setId(e.target.value); setError(null); }}
                placeholder="e.g. water_level"
                disabled={!isNew}
              />
              <span className="ap-hint">Lowercase letters, numbers, underscore. Cannot change after publish.</span>
            </label>
            <label className="ap-label">
              Type
              <select
                className="ap-input"
                value={type}
                onChange={(e) => setType(e.target.value as SchemaField["type"])}
              >
                <option value="select">Select (single)</option>
                <option value="multiselect">Multiselect</option>
                <option value="boolean">Boolean (Yes/No)</option>
                <option value="text">Free text</option>
                <option value="number">Number</option>
              </select>
            </label>
          </div>

          <label className="ap-label sef-inline-label">
            <input
              type="checkbox"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
            />
            Required field (respondent cannot skip)
          </label>

          {/* ── Question labels ─────────────────────────────────────────── */}
          <div className="sef-section-title">Question text (shown to respondent)</div>
          <div className="sef-lang-grid">
            {LANGS.map((lang) => (
              <label key={lang} className="ap-label">
                {LANG_NAMES[lang]}
                <input
                  className="ap-input"
                  value={labels[lang] ?? ""}
                  onChange={(e) => setLabel(lang, e.target.value)}
                  placeholder={lang === "en" ? "Required" : "Optional"}
                />
              </label>
            ))}
          </div>

          {/* ── Options (select/multiselect only) ───────────────────────── */}
          {hasOptions && (
            <>
              <div className="sef-section-title">Options</div>
              {options.map((opt, idx) => (
                <div key={idx} className="sef-option-block">
                  <div className="sef-option-header">
                    <span className="sef-option-num">#{idx + 1}</span>
                    <label className="ap-label ap-grow">
                      Option ID
                      <input
                        className="ap-input ap-mono ap-short"
                        value={opt.value}
                        onChange={(e) => setOptionValue(idx, e.target.value)}
                        placeholder="e.g. knee_deep"
                      />
                    </label>
                    <button
                      type="button"
                      className="ap-icon-btn"
                      onClick={() => removeOption(idx)}
                      title="Remove option"
                      disabled={options.length <= 1}
                    >
                      🗑
                    </button>
                  </div>
                  <div className="sef-lang-grid sef-lang-grid--compact">
                    {LANGS.map((lang) => (
                      <label key={lang} className="ap-label">
                        {LANG_NAMES[lang]}
                        <input
                          className="ap-input"
                          value={opt.labels[lang] ?? ""}
                          onChange={(e) => setOptionLabel(idx, lang, e.target.value)}
                          placeholder={lang === "en" ? "Required" : "Optional"}
                        />
                      </label>
                    ))}
                  </div>
                </div>
              ))}
              <button type="button" className="ap-btn ap-btn--ghost ap-btn--sm" onClick={addOption}>
                + Add option
              </button>
            </>
          )}
        </div>

        {error && <div className="ap-error">⚠ {error}</div>}

        <div className="ap-modal-actions">
          <button type="button" className="ap-btn ap-btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="ap-btn ap-btn--primary" onClick={handleSave}>
            {isNew ? "Add Field" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
