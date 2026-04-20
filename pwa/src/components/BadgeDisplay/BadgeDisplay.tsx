import { useTranslation } from "../../hooks/useTranslation";

const ALL_BADGES = ["first_responder", "area_champion", "verified_reporter", "crisis_veteran"] as const;
type Badge = (typeof ALL_BADGES)[number];

interface Props {
  earned: Badge[];
}

export function BadgeDisplay({ earned }: Props) {
  const { t } = useTranslation();
  if (earned.length === 0) return null;

  return (
    <div className="badge-display">
      {earned.map((badge) => (
        <span key={badge} className="badge" title={t(`badges.${badge}`)}>
          🏅 {t(`badges.${badge}`)}
        </span>
      ))}
    </div>
  );
}
