import { useState, useRef } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import { useGeolocation } from "../../hooks/useGeolocation";
import { DamageSelector, type DamageLevel } from "../DamageSelector/DamageSelector";
import { InfraTypeSelector, type InfraType } from "../InfraTypeSelector/InfraTypeSelector";
import { enqueueReport } from "../../services/pouchdb";
import { submitReport } from "../../services/api";
import { syncQueuedReports } from "../../services/sync";

const CRISIS_NATURES = [
  "earthquake", "flood", "tsunami", "hurricane", "wildfire",
  "explosion", "chemical", "conflict", "civil_unrest",
] as const;

interface Props {
  crisisEventId: string;
  onSuccess?: (reportId: string) => void;
}

export function ReportForm({ crisisEventId, onSuccess }: Props) {
  const { t } = useTranslation();
  const { coords, loading: gpsLoading, request: requestGps } = useGeolocation();

  const [photo, setPhoto] = useState<string | null>(null);
  const [damageLevel, setDamageLevel] = useState<DamageLevel | null>(null);
  const [infraTypes, setInfraTypes] = useState<InfraType[]>([]);
  const [crisisNature, setCrisisNature] = useState("");
  const [debrisRequired, setDebrisRequired] = useState<boolean | null>(null);
  const [description, setDescription] = useState("");
  const [what3words, setWhat3words] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ reportId: string; offline: boolean } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setPhoto(reader.result as string);
    reader.readAsDataURL(file);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null) return;

    setSubmitting(true);

    const fields: Record<string, string> = {
      damage_level: damageLevel,
      infrastructure_types: JSON.stringify(infraTypes),
      crisis_nature: crisisNature,
      requires_debris_clearing: String(debrisRequired),
      crisis_event_id: crisisEventId,
      channel: "pwa",
      ...(description && { description }),
      ...(coords && { gps_lat: String(coords.lat), gps_lon: String(coords.lon) }),
      ...(what3words && { what3words_address: what3words }),
    };

    try {
      if (navigator.onLine) {
        const res = await submitReport(fields, photo);
        setResult({ reportId: res.report_id, offline: false });
        onSuccess?.(res.report_id);
      } else {
        const id = await enqueueReport(fields, photo);
        setResult({ reportId: id, offline: true });
        syncQueuedReports();
      }
    } catch {
      // Network failed mid-flight — save offline
      const id = await enqueueReport(fields, photo);
      setResult({ reportId: id, offline: true });
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className="report-success">
        <p>
          {result.offline
            ? t("confirmation.saved_offline")
            : t("confirmation.success", { report_id: result.reportId })}
        </p>
        <button onClick={() => setResult(null)}>Submit another report</button>
      </div>
    );
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>
      {/* Photo */}
      <section>
        <label className="photo-upload">
          {photo
            ? <img src={photo} alt="preview" className="photo-preview" />
            : <span>{t("form.photo_prompt")}</span>}
          <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} hidden />
        </label>
        <button type="button" onClick={() => fileRef.current?.click()}>
          {t("form.photo_prompt")}
        </button>
      </section>

      {/* Location */}
      <section>
        <p>{t("form.location_prompt")}</p>
        <button type="button" onClick={requestGps} disabled={gpsLoading}>
          {gpsLoading ? "…" : "📍 Use my GPS location"}
        </button>
        {coords && <p>✓ GPS: {coords.lat.toFixed(5)}, {coords.lon.toFixed(5)}</p>}
        <input
          type="text"
          placeholder={t("form.what3words_placeholder")}
          value={what3words}
          onChange={(e) => setWhat3words(e.target.value)}
        />
      </section>

      {/* Damage level */}
      <DamageSelector value={damageLevel} onChange={setDamageLevel} />

      {/* Infrastructure type */}
      <InfraTypeSelector selected={infraTypes} onChange={setInfraTypes} />

      {/* Crisis nature */}
      <section>
        <label>
          {t("form.crisis_nature")}
          <select value={crisisNature} onChange={(e) => setCrisisNature(e.target.value)} required>
            <option value="">—</option>
            {CRISIS_NATURES.map((n) => (
              <option key={n} value={n}>{n.replace("_", " ")}</option>
            ))}
          </select>
        </label>
      </section>

      {/* Debris */}
      <section>
        <p>{t("form.debris")}</p>
        <label>
          <input type="radio" name="debris" onChange={() => setDebrisRequired(true)} /> {t("form.submit") === "Submit report" ? "Yes" : "✓"}
        </label>
        <label>
          <input type="radio" name="debris" onChange={() => setDebrisRequired(false)} /> No
        </label>
      </section>

      {/* Description */}
      <section>
        <textarea
          placeholder={t("form.description")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </section>

      <button
        type="submit"
        disabled={submitting || !damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null}
      >
        {submitting ? t("form.submitting") : t("form.submit")}
      </button>
    </form>
  );
}
