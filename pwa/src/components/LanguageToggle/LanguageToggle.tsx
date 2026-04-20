import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", label: "EN" },
  { code: "ar", label: "AR" },
  { code: "fr", label: "FR" },
  { code: "zh", label: "中" },
  { code: "ru", label: "RU" },
  { code: "es", label: "ES" },
];

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language.slice(0, 2);

  return (
    <div className="language-toggle">
      {LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          className={current === code ? "active" : ""}
          onClick={() => i18n.changeLanguage(code)}
          aria-label={code}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
