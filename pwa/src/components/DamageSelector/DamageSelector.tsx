import { useTranslation } from "../../hooks/useTranslation";

const LEVELS = ["minimal", "partial", "complete"] as const;
export type DamageLevel = (typeof LEVELS)[number];

interface Props {
  value: DamageLevel | null;
  onChange: (level: DamageLevel) => void;
  /**
   * Optional schema options — keyed by damage level value, value is a label map (lang → text).
   * When provided, labels come from the schema instead of i18n keys.
   */
  schemaOptions?: Record<string, Record<string, string>>;
  /** Current UI language (for schema label lookup). */
  lang?: string;
}

export function DamageSelector({ value, onChange, schemaOptions, lang = "en" }: Props) {
  const { t } = useTranslation();

  function levelLabel(level: DamageLevel): string {
    if (schemaOptions?.[level]) {
      return schemaOptions[level][lang] || schemaOptions[level]["en"] || t(`form.damage_${level}_label`);
    }
    return t(`form.damage_${level}_label`);
  }

  function levelSub(level: DamageLevel): string {
    // Sub-text is part of the label in schema — only show separate sub when using i18n
    if (schemaOptions?.[level]) return "";
    return t(`form.damage_${level}_sub`);
  }

  return (
    <fieldset className="damage-selector">
      <legend>{t("form.damage_level")}</legend>
      <div className="damage-options">
        {LEVELS.map((level) => (
          <label
            key={level}
            className={`damage-option damage-${level} ${value === level ? "selected" : ""}`}
          >
            <input
              type="radio"
              name="damage_level"
              value={level}
              checked={value === level}
              onChange={() => onChange(level)}
            />
            <span className="damage-dot" />
            <span className="damage-text">
              <strong>{levelLabel(level)}</strong>
              {levelSub(level) && <span>{levelSub(level)}</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
