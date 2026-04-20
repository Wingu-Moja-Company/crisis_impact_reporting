import { useTranslation as useI18nTranslation } from "react-i18next";

// Thin wrapper — gives components a single import for translation
export function useTranslation() {
  return useI18nTranslation();
}
