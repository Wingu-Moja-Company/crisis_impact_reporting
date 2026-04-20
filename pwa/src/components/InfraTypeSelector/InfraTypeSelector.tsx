import { useTranslation } from "../../hooks/useTranslation";

const TYPES = [
  "residential", "commercial", "government", "utility",
  "transport", "community", "public_space", "other",
] as const;
export type InfraType = (typeof TYPES)[number];

interface Props {
  selected: InfraType[];
  onChange: (types: InfraType[]) => void;
}

export function InfraTypeSelector({ selected, onChange }: Props) {
  const { t } = useTranslation();

  function toggle(type: InfraType) {
    onChange(
      selected.includes(type)
        ? selected.filter((t) => t !== type)
        : [...selected, type]
    );
  }

  return (
    <fieldset className="infra-selector">
      <legend>{t("form.infra_type")}</legend>
      {TYPES.map((type) => (
        <label key={type} className={`infra-option ${selected.includes(type) ? "selected" : ""}`}>
          <input
            type="checkbox"
            value={type}
            checked={selected.includes(type)}
            onChange={() => toggle(type)}
          />
          {t(`form.infra_${type}`)}
        </label>
      ))}
    </fieldset>
  );
}
