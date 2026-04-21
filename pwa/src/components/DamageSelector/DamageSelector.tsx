import { useTranslation } from "../../hooks/useTranslation";

const LEVELS = ["minimal", "partial", "complete"] as const;
export type DamageLevel = (typeof LEVELS)[number];

const META: Record<DamageLevel, { label: string; sub: string }> = {
  minimal:  { label: "Minimal",  sub: "Cosmetic damage only, still functional" },
  partial:  { label: "Partial",  sub: "Repairable, usable with caution" },
  complete: { label: "Complete", sub: "Structurally unsafe or destroyed" },
};

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
              <strong>{META[level].label}</strong>
              <span>{META[level].sub}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
