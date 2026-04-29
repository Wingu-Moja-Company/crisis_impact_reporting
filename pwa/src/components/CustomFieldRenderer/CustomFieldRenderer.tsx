/**
 * Renders a single dynamic form field based on its schema definition.
 *
 * Supported field types:
 *   select      — radio buttons (≤6 options) or <select> (>6)
 *   multiselect — checkboxes
 *   boolean     — Yes / No radio
 *   text        — <textarea>
 *   number      — <input type="number">
 */

import { type SchemaField, getLabel } from "../../services/schema";

interface Props {
  field: SchemaField;
  value: unknown;
  onChange: (fieldId: string, value: unknown) => void;
  lang: string;
  /** 1-based index shown in the label (optional) */
  index?: number;
  /** Total number of custom fields (for progress display) */
  total?: number;
}

function _label(labels: Record<string, string> | undefined, lang: string): string {
  return getLabel(labels, lang);
}

export function CustomFieldRenderer({ field, value, onChange, lang }: Props) {
  const question = _label(field.labels, lang);
  const isRequired = field.required !== false;

  const labelText = (
    <div className="form-card-label">
      <span className="sec-num" />
      {question}
      {!isRequired && (
        <span className="field-optional-tag"> — optional</span>
      )}
    </div>
  );

  // ── select ──────────────────────────────────────────────────────────────
  if (field.type === "select") {
    const options = field.options ?? [];
    const selected = typeof value === "string" ? value : "";
    return (
      <div className="form-card">
        {labelText}
        <div className="assessment-options">
          {options.map((opt) => {
            const optLabel = _label(opt.labels, lang);
            const isChecked = selected === opt.value;
            return (
              <label
                key={opt.value}
                className={`assessment-option radio-opt ${isChecked ? "selected" : ""}`}
              >
                <input
                  type="radio"
                  name={`field_${field.id}`}
                  value={opt.value}
                  checked={isChecked}
                  onChange={() => onChange(field.id, opt.value)}
                  required={isRequired && !selected}
                />
                {optLabel}
              </label>
            );
          })}
        </div>
      </div>
    );
  }

  // ── multiselect ──────────────────────────────────────────────────────────
  if (field.type === "multiselect") {
    const options = field.options ?? [];
    const selected: string[] = Array.isArray(value) ? (value as string[]) : [];
    function toggle(val: string) {
      const next = selected.includes(val)
        ? selected.filter((v) => v !== val)
        : [...selected, val];
      onChange(field.id, next);
    }
    return (
      <div className="form-card">
        {labelText}
        <div className="assessment-options">
          {options.map((opt) => {
            const optLabel = _label(opt.labels, lang);
            const isChecked = selected.includes(opt.value);
            return (
              <label
                key={opt.value}
                className={`assessment-option checkbox-opt ${isChecked ? "selected" : ""}`}
              >
                <input
                  type="checkbox"
                  value={opt.value}
                  checked={isChecked}
                  onChange={() => toggle(opt.value)}
                />
                {optLabel}
              </label>
            );
          })}
        </div>
      </div>
    );
  }

  // ── boolean ──────────────────────────────────────────────────────────────
  if (field.type === "boolean") {
    const boolVal = value === true || value === "true";
    const isAnswered = value === true || value === false || value === "true" || value === "false";
    const yesLabels: Record<string, string> = { en: "Yes", fr: "Oui", ar: "نعم", sw: "Ndiyo", es: "Sí", zh: "是" };
    const noLabels: Record<string, string> = { en: "No", fr: "Non", ar: "لا", sw: "Hapana", es: "No", zh: "否" };
    const yesLabel = yesLabels[lang] ?? "Yes";
    const noLabel = noLabels[lang] ?? "No";
    return (
      <div className="form-card">
        {labelText}
        <div className="debris-options">
          <label className={`debris-option yes ${boolVal && isAnswered ? "selected" : ""}`}>
            <input
              type="radio"
              name={`field_${field.id}`}
              onChange={() => onChange(field.id, true)}
              checked={boolVal && isAnswered}
            />
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {yesLabel}
          </label>
          <label className={`debris-option no ${!boolVal && isAnswered ? "selected" : ""}`}>
            <input
              type="radio"
              name={`field_${field.id}`}
              onChange={() => onChange(field.id, false)}
              checked={!boolVal && isAnswered}
            />
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
            </svg>
            {noLabel}
          </label>
        </div>
      </div>
    );
  }

  // ── text ──────────────────────────────────────────────────────────────────
  if (field.type === "text") {
    return (
      <div className="form-card">
        {labelText}
        <textarea
          className="description-textarea"
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(field.id, e.target.value)}
          required={isRequired}
          rows={3}
        />
      </div>
    );
  }

  // ── number ────────────────────────────────────────────────────────────────
  if (field.type === "number") {
    return (
      <div className="form-card">
        {labelText}
        <input
          type="number"
          className="w3w-input"
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            const n = parseFloat(e.target.value);
            onChange(field.id, isNaN(n) ? null : n);
          }}
          required={isRequired}
          style={{ width: "100%" }}
        />
      </div>
    );
  }

  // Unknown type — skip silently
  return null;
}
