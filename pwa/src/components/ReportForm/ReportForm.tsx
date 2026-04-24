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

const ELECTRICITY_OPTIONS = [
  "no_damage", "minor", "moderate", "severe", "destroyed", "unknown",
] as const;

const HEALTH_OPTIONS = [
  "fully", "partially", "largely_disrupted", "not_functioning", "unknown",
] as const;

const HEALTH_VALUES: Record<string, string> = {
  fully:              "fully_functional",
  partially:          "partially_functional",
  largely_disrupted:  "largely_disrupted",
  not_functioning:    "not_functioning",
  unknown:            "unknown",
};

const NEEDS_OPTIONS = [
  "food_water", "cash", "healthcare", "shelter", "livelihoods",
  "wash", "basic_services", "protection", "community", "other",
] as const;

const NEEDS_VALUES: Record<string, string> = {
  food_water:     "food_water",
  cash:           "cash_financial",
  healthcare:     "healthcare",
  shelter:        "shelter",
  livelihoods:    "livelihoods",
  wash:           "wash",
  basic_services: "basic_services",
  protection:     "protection",
  community:      "community_support",
  other:          "other",
};

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
  const [electricityStatus, setElectricityStatus] = useState("");
  const [healthServices, setHealthServices] = useState("");
  const [pressingNeeds, setPressingNeeds] = useState<string[]>([]);
  const [description, setDescription] = useState("");

  const [locationText, setLocationText] = useState("");
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResult | null>(null);
  const [geocodeFailed, setGeocodeFailed] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<{ reportId: string; offline: boolean } | null>(null);
  const [retrying, setRetrying] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  function resetForm() {
    setPhoto(null);
    setDamageLevel(null);
    setInfraTypes([]);
    setCrisisNature("");
    setDebrisRequired(null);
    setElectricityStatus("");
    setHealthServices("");
    setPressingNeeds([]);
    setDescription("");
    setLocationText("");
    setGeocodeResult(null);
    setGeocodeFailed(false);
    setSubmitError(null);
    setResult(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setPhoto(reader.result as string);
    reader.readAsDataURL(file);
  }

  async function handleLocationBlur() {
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
    if (!damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null || !electricityStatus || !healthServices || pressingNeeds.length === 0) return;

    setSubmitting(true);
    setSubmitError(null);

    const finalLat = coords?.lat ?? geocodeResult?.lat;
    const finalLon = coords?.lon ?? geocodeResult?.lon;

    const fields: Record<string, string> = {
      damage_level:             damageLevel,
      infrastructure_types:     JSON.stringify(infraTypes),
      crisis_nature:            crisisNature,
      requires_debris_clearing: String(debrisRequired),
      crisis_event_id:          crisisEventId,
      channel:                  "pwa",
      modular_fields:           JSON.stringify({
        electricity_status: electricityStatus,
        health_services:    healthServices,
        pressing_needs:     pressingNeeds,
      }),
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
    setResult(null);
  }

  if (result) {
    return (
      <div className="report-success">
        <div className="success-icon">{result.offline ? "⏳" : "✓"}</div>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: ".3rem" }}>
            {result.offline ? t("success.queued_title") : t("success.submitted_title")}
          </h2>
          <p style={{ fontSize: ".88rem", color: "var(--grey-500)" }}>
            {result.offline ? t("success.queued_desc") : t("success.submitted_desc")}
          </p>
          {submitError && (
            <p style={{
              fontSize: ".78rem", color: "#b91c1c", marginTop: ".5rem",
              background: "#fef2f2", padding: ".4rem .6rem", borderRadius: "4px",
            }}>
              {t("success.error_prefix", { message: submitError })}
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
            {retrying ? t("success.retrying") : t("success.retry")}
          </button>
        )}
        <button onClick={resetForm}>{t("success.submit_another")}</button>
      </div>
    );
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>

      {/* Photo */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_photo")}</span>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} hidden />
        {photo ? (
          <>
            <img src={photo} alt="preview" className="photo-preview" />
            <button type="button" className="photo-change-btn" onClick={() => fileRef.current?.click()}>
              {t("form.change_photo")}
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
        <span className="form-card-label">{t("form.section_location")}</span>
        <div className="location-card">
          <button type="button" className="gps-btn" onClick={requestGps} disabled={gpsLoading}>
            <span>📍</span>
            {gpsLoading ? t("form.getting_gps") : t("form.use_gps")}
          </button>
          {coords && (
            <div className="gps-confirmed">
              ✓ {t("form.gps_confirmed")} ({coords.lat.toFixed(4)}, {coords.lon.toFixed(4)})
            </div>
          )}
          {!coords && (
            <>
              <div className="divider-or">{t("form.type_address")}</div>
              <input
                className="w3w-input"
                type="text"
                placeholder={t("form.address_placeholder")}
                value={locationText}
                onChange={(e) => {
                  setLocationText(e.target.value);
                  setGeocodeResult(null);
                  setGeocodeFailed(false);
                }}
                onBlur={handleLocationBlur}
              />
              {geocoding && (
                <div className="geocode-status geocode-searching">🔍 {t("form.looking_up")}</div>
              )}
              {geocodeResult && (
                <div className="geocode-status geocode-found">
                  📍 {t("form.located_at", { name: geocodeResult.displayName })}
                </div>
              )}
              {geocodeFailed && locationText.trim() && (
                <div className="geocode-status geocode-not-found">
                  ℹ️ {t("form.location_not_found")}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Damage level */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_damage")}</span>
        <DamageSelector value={damageLevel} onChange={setDamageLevel} />
      </div>

      {/* Infrastructure type */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_infra")}</span>
        <InfraTypeSelector selected={infraTypes} onChange={setInfraTypes} />
      </div>

      {/* Crisis nature */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_crisis")}</span>
        <select
          className="crisis-select"
          value={crisisNature}
          onChange={(e) => setCrisisNature(e.target.value)}
          required
        >
          <option value="">{t("form.crisis_nature")}</option>
          {CRISIS_NATURES.map((n) => (
            <option key={n} value={n}>{t(`form.crisis_${n}`)}</option>
          ))}
        </select>
      </div>

      {/* Debris */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_debris")}</span>
        <div className="debris-options">
          <label className={`debris-option yes ${debrisRequired === true ? "selected" : ""}`}>
            <input type="radio" name="debris" onChange={() => setDebrisRequired(true)} />
            ⚠️ {t("form.debris_yes")}
          </label>
          <label className={`debris-option no ${debrisRequired === false ? "selected" : ""}`}>
            <input type="radio" name="debris" onChange={() => setDebrisRequired(false)} />
            ✓ {t("form.debris_no")}
          </label>
        </div>
      </div>

      {/* Electricity */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_electricity")}</span>
        <div className="assessment-options">
          {ELECTRICITY_OPTIONS.map((opt) => (
            <label key={opt} className={`assessment-option radio-opt ${electricityStatus === opt ? "selected" : ""}`}>
              <input type="radio" name="electricity_status" value={opt} checked={electricityStatus === opt} onChange={() => setElectricityStatus(opt)} />
              {t(`form.elec_${opt}`)}
            </label>
          ))}
        </div>
      </div>

      {/* Health services */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_health")}</span>
        <div className="assessment-options">
          {HEALTH_OPTIONS.map((opt) => (
            <label key={opt} className={`assessment-option radio-opt ${healthServices === HEALTH_VALUES[opt] ? "selected" : ""}`}>
              <input
                type="radio"
                name="health_services"
                value={HEALTH_VALUES[opt]}
                checked={healthServices === HEALTH_VALUES[opt]}
                onChange={() => setHealthServices(HEALTH_VALUES[opt])}
              />
              {t(`form.health_${opt}`)}
            </label>
          ))}
        </div>
      </div>

      {/* Pressing needs */}
      <div className="form-card">
        <span className="form-card-label">{t("form.section_needs")}</span>
        <div className="assessment-options">
          {NEEDS_OPTIONS.map((opt) => {
            const val = NEEDS_VALUES[opt];
            return (
              <label key={opt} className={`assessment-option checkbox-opt ${pressingNeeds.includes(val) ? "selected" : ""}`}>
                <input
                  type="checkbox"
                  value={val}
                  checked={pressingNeeds.includes(val)}
                  onChange={(e) => setPressingNeeds(
                    e.target.checked ? [...pressingNeeds, val] : pressingNeeds.filter((v) => v !== val)
                  )}
                />
                {t(`form.needs_${opt}`)}
              </label>
            );
          })}
        </div>
      </div>

      {/* Description */}
      <div className="form-card">
        <span className="form-card-label">
          {t("form.section_description")}{" "}
          <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>{t("form.optional")}</span>
        </span>
        <textarea
          className="description-textarea"
          placeholder={t("form.description_placeholder")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={submitting || !damageLevel || infraTypes.length === 0 || !crisisNature || debrisRequired === null || !electricityStatus || !healthServices || pressingNeeds.length === 0}
      >
        {submitting ? t("form.submitting") : t("form.submit")}
      </button>

    </form>
  );
}
