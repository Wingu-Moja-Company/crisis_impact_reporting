import { useTranslation } from "react-i18next";

const LANGS = [
  { code: "en", label: "EN" },
  { code: "ar", label: "AR" },
  { code: "fr", label: "FR" },
  { code: "zh", label: "中" },
  { code: "ru", label: "RU" },
  { code: "es", label: "ES" },
];

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language?.slice(0, 2) ?? "en";

  return (
    <div className="lang-toggle">
      {LANGS.map(({ code, label }) => (
        <button
          key={code}
          className={`lang-btn${current === code ? " lang-btn--active" : ""}`}
          onClick={() => i18n.changeLanguage(code)}
          aria-label={code}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
