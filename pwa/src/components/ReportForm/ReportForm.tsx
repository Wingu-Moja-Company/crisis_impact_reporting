import { useState, useRef } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import { useGeolocation } from "../../hooks/useGeolocation";
import { DamageSelector, type DamageLevel } from "../DamageSelector/DamageSelector";
import { InfraTypeSelector, type InfraType } from "../InfraTypeSelector/InfraTypeSelector";
import { enqueueReport } from "../../services/pouchdb";
import { submitReport } from "../../services/api";
import { syncQueuedReports } from "../../services/sync";
import { geocodeLocation, type GeocodeResult } from "../../services/geocode";

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

  // Location state
  const [locationText, setLocationText] = useState("");
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResult | null>(null);
  const [geocodeFailed, setGeocodeFailed] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<{ reportId: string; offline: boolean } | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setPhoto(reader.result as string);
    reader.readAsDataURL(file);
  }

  async function handleLocationBlur() {
    // If GPS is already confirmed, no need to geocode
    if (coords || !locationText.trim()) return;
    setGeocoding(true);
    setGeocodeResult(null);
    setGeocodeFailed(false);
    const res = await geocodeLocation(locationText);
    setGeocoding(false);
    if (res) {
      setGeocodeResult(res);
    } else {
      setGeocodeFailed(true);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null) return;

    setSubmitting(true);
    setSubmitError(null);

    // Resolve coordinates: GPS > geocoded text > none
    const finalLat = coords?.lat ?? geocodeResult?.lat;
    const finalLon = coords?.lon ?? geocodeResult?.lon;

    const fields: Record<string, string> = {
      damage_level:             damageLevel,
      infrastructure_types:     JSON.stringify(infraTypes),
      crisis_nature:            crisisNature,
      requires_debris_clearing: String(debrisRequired),
      crisis_event_id:          crisisEventId,
      channel:                  "pwa",
      ...(description    && { description }),
      ...(finalLat != null && { gps_lat: String(finalLat), gps_lon: String(finalLon) }),
      ...(locationText   && { location_description: locationText }),
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
    } catch (err) {
      // Online but submission failed — queue locally and surface the error
      const errMsg = err instanceof Error ? err.message : String(err);
      setSubmitError(errMsg);
      const id = await enqueueReport(fields, photo);
      setResult({ reportId: id, offline: true });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRetry() {
    setRetrying(true);
    await syncQueuedReports();
    setRetrying(false);
    setResult(null); // return to form so user can try again if still failing
  }

  if (result) {
    return (
      <div className="report-success">
        <div className="success-icon">{result.offline ? "⏳" : "✓"}</div>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: ".3rem" }}>
            {result.offline ? "Queued for upload" : "Report submitted"}
          </h2>
          <p style={{ fontSize: ".88rem", color: "var(--grey-500)" }}>
            {result.offline
              ? "Couldn't reach the server right now — tap Retry or it will sync automatically."
              : "Your report is now being processed"}
          </p>
          {submitError && (
            <p style={{
              fontSize: ".78rem", color: "#b91c1c", marginTop: ".5rem",
              background: "#fef2f2", padding: ".4rem .6rem", borderRadius: "4px",
            }}>
              Error: {submitError}
            </p>
          )}
        </div>
        <span className="success-id">{result.reportId}</span>
        {result.offline && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            style={{ background: "var(--blue)", color: "#fff", border: "none",
              borderRadius: "8px", padding: ".6rem 1.2rem", fontWeight: 700,
              fontSize: ".9rem", cursor: "pointer", marginBottom: ".5rem" }}
          >
            {retrying ? "Retrying…" : "Retry now"}
          </button>
        )}
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
        <span className="form-card-label">Location of damage</span>
        <div className="location-card">
          {/* GPS button */}
          <button type="button" className="gps-btn" onClick={requestGps} disabled={gpsLoading}>
            <span>📍</span>
            {gpsLoading ? "Getting location…" : "Use my GPS location"}
          </button>
          {coords && (
            <div className="gps-confirmed">
              ✓ GPS confirmed ({coords.lat.toFixed(4)}, {coords.lon.toFixed(4)})
            </div>
          )}

          {/* Text location with geocoding */}
          {!coords && (
            <>
              <div className="divider-or">or type an address / landmark</div>
              <input
                className="w3w-input"
                type="text"
                placeholder="e.g. Near Westlands Market, Kibera Road..."
                value={locationText}
                onChange={(e) => {
                  setLocationText(e.target.value);
                  setGeocodeResult(null);
                  setGeocodeFailed(false);
                }}
                onBlur={handleLocationBlur}
              />
              {geocoding && (
                <div className="geocode-status geocode-searching">🔍 Looking up location…</div>
              )}
              {geocodeResult && (
                <div className="geocode-status geocode-found">
                  📍 Located: {geocodeResult.displayName}
                </div>
              )}
              {geocodeFailed && locationText.trim() && (
                <div className="geocode-status geocode-not-found">
                  ℹ️ Location not found on map — will be saved as a description
                </div>
              )}
            </>
          )}
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
        <span className="form-card-label">
          Additional details{" "}
          <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional)</span>
        </span>
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
