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
      const id = await enqueueReport(fields, photo);
      setResult({ reportId: id, offline: true });
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className="report-success">
        <div className="success-icon">✓</div>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: ".3rem" }}>
            {result.offline ? "Saved offline" : "Report submitted"}
          </h2>
          <p style={{ fontSize: ".88rem", color: "var(--grey-500)" }}>
            {result.offline
              ? "Will sync automatically when you're back online"
              : "Your report is now being processed"}
          </p>
        </div>
        <span className="success-id">{result.reportId}</span>
        <button onClick={() => setResult(null)}>Submit another report</button>
      </div>
    );
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>

      {/* Photo */}
      <div className="form-card">
        <span className="form-card-label">Photo evidence</span>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} hidden />
        {photo ? (
          <>
            <img src={photo} alt="preview" className="photo-preview" />
            <button type="button" className="photo-change-btn" onClick={() => fileRef.current?.click()}>
              Change photo
            </button>
          </>
        ) : (
          <div className="photo-upload-area" onClick={() => fileRef.current?.click()}>
            <span className="photo-upload-icon">📷</span>
            <span>{t("form.photo_prompt")}</span>
            <span style={{ fontSize: ".75rem", color: "var(--grey-300)" }}>JPG, PNG, HEIC</span>
          </div>
        )}
      </div>

      {/* Location */}
      <div className="form-card">
        <span className="form-card-label">Location</span>
        <div className="location-card">
          <button type="button" className="gps-btn" onClick={requestGps} disabled={gpsLoading}>
            <span>📍</span>
            {gpsLoading ? "Getting location…" : "Use my GPS location"}
          </button>
          {coords && (
            <div className="gps-confirmed">
              ✓ {coords.lat.toFixed(5)}, {coords.lon.toFixed(5)}
            </div>
          )}
          <div className="divider-or">or</div>
          <input
            className="w3w-input"
            type="text"
            placeholder={t("form.what3words_placeholder")}
            value={what3words}
            onChange={(e) => setWhat3words(e.target.value)}
          />
        </div>
      </div>

      {/* Damage level */}
      <div className="form-card">
        <span className="form-card-label">Level of damage</span>
        <DamageSelector value={damageLevel} onChange={setDamageLevel} />
      </div>

      {/* Infrastructure type */}
      <div className="form-card">
        <span className="form-card-label">Type of infrastructure</span>
        <InfraTypeSelector selected={infraTypes} onChange={setInfraTypes} />
      </div>

      {/* Crisis nature */}
      <div className="form-card">
        <span className="form-card-label">Nature of crisis</span>
        <select
          className="crisis-select"
          value={crisisNature}
          onChange={(e) => setCrisisNature(e.target.value)}
          required
        >
          <option value="">Select crisis type…</option>
          {CRISIS_NATURES.map((n) => (
            <option key={n} value={n}>{n.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
          ))}
        </select>
      </div>

      {/* Debris */}
      <div className="form-card">
        <span className="form-card-label">Debris clearing required?</span>
        <div className="debris-options">
          <label className={`debris-option yes ${debrisRequired === true ? "selected" : ""}`}>
            <input type="radio" name="debris" onChange={() => setDebrisRequired(true)} />
            ⚠️ Yes, required
          </label>
          <label className={`debris-option no ${debrisRequired === false ? "selected" : ""}`}>
            <input type="radio" name="debris" onChange={() => setDebrisRequired(false)} />
            ✓ Not needed
          </label>
        </div>
      </div>

      {/* Description */}
      <div className="form-card">
        <span className="form-card-label">Additional details <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional)</span></span>
        <textarea
          className="description-textarea"
          placeholder="Describe what you see — people trapped, hazards, access routes…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={submitting || !damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null}
      >
        {submitting ? "Submitting…" : "Submit damage report →"}
      </button>

    </form>
  );
}
