import { useTranslation } from "../../hooks/useTranslation";
import { type SchemaOption, getLabel } from "../../services/schema";

const DEFAULT_TYPES = [
  "residential", "commercial", "government", "utility",
  "transport", "community", "public_space", "other",
] as const;

// Keep backward-compat export — used by old InfraType typed references
export type InfraType = string;

interface Props {
  selected: string[];
  onChange: (types: string[]) => void;
  /**
   * Optional schema options list — when provided, options come from the schema
   * (coordinator-configured) instead of the hardcoded list.
   */
  schemaOptions?: SchemaOption[];
  /** Current UI language (for schema label lookup). */
  lang?: string;
}

export function InfraTypeSelector({ selected, onChange, schemaOptions, lang = "en" }: Props) {
  const { t } = useTranslation();

  function toggle(type: string) {
    onChange(
      selected.includes(type)
        ? selected.filter((v) => v !== type)
        : [...selected, type]
    );
  }

  // Use schema options if provided, otherwise fall back to hardcoded list
  const options: Array<{ value: string; label: string }> = schemaOptions
    ? schemaOptions.map((opt) => ({
        value: opt.value,
        label: getLabel(opt.labels, lang),
      }))
    : DEFAULT_TYPES.map((type) => ({
        value: type,
        label: t(`form.infra_${type}`),
      }));

  return (
    <fieldset className="infra-selector">
      <legend>{t("form.infra_type")}</legend>
      <div className="infra-options-grid">
        {options.map(({ value, label }) => (
          <label key={value} className={`infra-option ${selected.includes(value) ? "selected" : ""}`}>
            <input
              type="checkbox"
              value={value}
              checked={selected.includes(value)}
              onChange={() => toggle(value)}
            />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
