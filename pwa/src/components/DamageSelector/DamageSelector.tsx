import { useTranslation } from "../../hooks/useTranslation";

const LEVELS = ["minimal", "partial", "complete"] as const;
export type DamageLevel = (typeof LEVELS)[number];

interface Props {
  value: DamageLevel | null;
  onChange: (level: DamageLevel) => void;
}

export function DamageSelector({ value, onChange }: Props) {
  const { t } = useTranslation();

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
              <strong>{t(`form.damage_${level}_label`)}</strong>
              <span>{t(`form.damage_${level}_sub`)}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
