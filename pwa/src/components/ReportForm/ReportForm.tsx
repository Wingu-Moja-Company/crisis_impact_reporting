import { useState, useRef, useEffect } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import { useGeolocation } from "../../hooks/useGeolocation";
import { useSchema } from "../../hooks/useSchema";
import { DamageSelector, type DamageLevel } from "../DamageSelector/DamageSelector";
import { InfraTypeSelector } from "../InfraTypeSelector/InfraTypeSelector";
import { CustomFieldRenderer } from "../CustomFieldRenderer/CustomFieldRenderer";
import { enqueueReport } from "../../services/pouchdb";
import { submitReport } from "../../services/api";
import { syncQueuedReports } from "../../services/sync";
import { geocodeLocation, type GeocodeResult } from "../../services/geocode";
import { getLabel, type SchemaOption } from "../../services/schema";

interface Props {
  crisisEventId: string;
  onSuccess?: (reportId: string) => void;
}

export function ReportForm({ crisisEventId, onSuccess }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || "en";
  const { coords, loading: gpsLoading, request: requestGps } = useGeolocation();
  const { schema, schemaLoading, isFallback, schemaVersion } = useSchema(crisisEventId);

  // ── Mandatory system fields ────────────────────────────────────────────────
  const [photo, setPhoto] = useState<string | null>(null);
  const [damageLevel, setDamageLevel] = useState<DamageLevel | null>(null);
  const [infraTypes, setInfraTypes] = useState<string[]>([]);

  // ── Dynamic custom field responses ────────────────────────────────────────
  const [responses, setResponses] = useState<Record<string, unknown>>({});

  // ── Location ──────────────────────────────────────────────────────────────
  const [locationText, setLocationText] = useState("");
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResult | null>(null);
  const [geocodeFailed, setGeocodeFailed] = useState(false);

  // ── Submission state ──────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<{ reportId: string; offline: boolean } | null>(null);
  const [retrying, setRetrying] = useState(false);

  // ── Schema version banner ─────────────────────────────────────────────────
  const [schemaUpdated, setSchemaUpdated] = useState(false);
  const firstVersion = useRef<number | null>(null);

  useEffect(() => {
    if (schemaVersion === null) return;
    if (firstVersion.current === null) {
      firstVersion.current = schemaVersion;
    } else if (schemaVersion !== firstVersion.current) {
      setSchemaUpdated(true);
    }
  }, [schemaVersion]);

  const fileRef   = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  // ── Helpers ───────────────────────────────────────────────────────────────

  function setResponse(fieldId: string, value: unknown) {
    setResponses((prev) => ({ ...prev, [fieldId]: value }));
  }

  function resetForm() {
    setPhoto(null);
    setDamageLevel(null);
    setInfraTypes([]);
    setResponses({});
    setLocationText("");
    setGeocodeResult(null);
    setGeocodeFailed(false);
    setSubmitError(null);
    setResult(null);
    setSchemaUpdated(false);
    firstVersion.current = null;
    if (fileRef.current) fileRef.current.value = "";
    if (cameraRef.current) cameraRef.current.value = "";
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

  // Check all required custom fields are answered
  function customFieldsComplete(): boolean {
    if (!schema) return true;
    for (const field of schema.custom_fields) {
      if (field.required === false) continue;
      const val = responses[field.id];
      if (val === undefined || val === null || val === "") return false;
      if (Array.isArray(val) && val.length === 0) return false;
    }
    return true;
  }

  const canSubmit =
    !!damageLevel &&
    infraTypes.length > 0 &&
    customFieldsComplete() &&
    !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setSubmitError(null);

    const finalLat = coords?.lat ?? geocodeResult?.lat;
    const finalLon = coords?.lon ?? geocodeResult?.lon;

    const fields: Record<string, string> = {
      damage_level:         damageLevel!,
      infrastructure_types: JSON.stringify(infraTypes),
      crisis_event_id:      crisisEventId,
      channel:              "pwa",
      responses:            JSON.stringify(responses),
      ...(schemaVersion != null && { schema_version: String(schemaVersion) }),
      ...(finalLat != null && { gps_lat: String(finalLat), gps_lon: String(finalLon) }),
      ...(locationText && { location_description: locationText }),
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

  // ── Success screen ────────────────────────────────────────────────────────

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

  // ── Loading state ─────────────────────────────────────────────────────────

  if (schemaLoading && !schema) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--grey-500)" }}>
        {t("form.loading_schema") || "Loading form…"}
      </div>
    );
  }

  // ── Schema-version update banner ──────────────────────────────────────────

  const customFields = schema?.custom_fields ?? [];

  // ── Damage level options from schema ─────────────────────────────────────

  const damageLevelLabels = schema?.system_fields?.damage_level?.options as
    | Record<string, Record<string, string>>
    | undefined;

  // ── Infrastructure type options from schema ───────────────────────────────

  const infraOptions: SchemaOption[] = Array.isArray(
    schema?.system_fields?.infrastructure_type?.options
  )
    ? (schema!.system_fields.infrastructure_type.options as SchemaOption[])
    : [];

  return (
    <form className="report-form" onSubmit={handleSubmit}>

      {/* Schema update banner */}
      {schemaUpdated && (
        <div style={{
          background: "#fef9c3", border: "1px solid #d97706", borderRadius: "8px",
          padding: ".75rem 1rem", marginBottom: "1rem", fontSize: ".85rem",
        }}>
          🔄 {t("form.schema_updated") || "The form has been updated. Please review your answers."}
        </div>
      )}

      {isFallback && (
        <div style={{
          background: "#fef2f2", border: "1px solid #dc2626", borderRadius: "8px",
          padding: ".75rem 1rem", marginBottom: "1rem", fontSize: ".85rem",
        }}>
          ⚠️ {t("form.schema_unavailable") || "Using simplified form — some questions may be missing."}
        </div>
      )}

      {/* Photo */}
      <div className="form-card">
        <div className="form-card-label">
          <span className="sec-num" />
          {t("form.section_photo")}
        </div>
        {/* Camera input (capture from device camera) */}
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} hidden />
        {/* Gallery input (choose existing file) */}
        <input ref={fileRef} type="file" accept="image/*" onChange={handlePhotoChange} hidden />
        {photo ? (
          <>
            <img src={photo} alt="preview" className="photo-preview" />
            <button type="button" className="photo-change-btn" onClick={() => fileRef.current?.click()}>
              {t("form.change_photo")}
            </button>
          </>
        ) : (
          <>
            <div className="photo-drop">
              <div className="photo-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"
                    stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
                  <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.8" />
                </svg>
              </div>
              <span className="photo-hint">{t("form.photo_prompt")}</span>
            </div>
            <div className="photo-btns">
              <button type="button" className="photo-btn" onClick={() => cameraRef.current?.click()}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round"/>
                  <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.8"/>
                </svg>
                {t("form.take_photo")}
              </button>
              <button type="button" className="photo-btn" onClick={() => fileRef.current?.click()}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="17 8 12 3 7 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
                {t("form.choose_photo")}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Location */}
      <div className="form-card">
        <div className="form-card-label">
          <span className="sec-num" />
          {t("form.section_location")}
        </div>
        <div className="location-card">
          <button type="button" className="gps-btn" onClick={requestGps} disabled={gpsLoading}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
              <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8"/>
              <line x1="12" y1="2" x2="12" y2="6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <line x1="12" y1="18" x2="12" y2="22" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <line x1="2" y1="12" x2="6" y2="12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <line x1="18" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            {gpsLoading ? t("form.getting_gps") : t("form.use_gps")}
          </button>
          {coords && (
            <div className="gps-confirmed">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {t("form.gps_confirmed")} ({coords.lat.toFixed(4)}, {coords.lon.toFixed(4)})
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

      {/* Damage level — mandatory system field */}
      <div className="form-card">
        <div className="form-card-label">
          <span className="sec-num" />
          {schema
            ? getLabel(schema.system_fields?.damage_level?.labels, lang)
            : t("form.section_damage")}
        </div>
        <DamageSelector
          value={damageLevel}
          onChange={setDamageLevel}
          schemaOptions={damageLevelLabels}
          lang={lang}
        />
      </div>

      {/* Infrastructure type — mandatory system field */}
      <div className="form-card">
        <div className="form-card-label">
          <span className="sec-num" />
          {schema
            ? getLabel(schema.system_fields?.infrastructure_type?.labels, lang)
            : t("form.section_infra")}
        </div>
        <InfraTypeSelector
          selected={infraTypes}
          onChange={setInfraTypes}
          schemaOptions={infraOptions.length > 0 ? infraOptions : undefined}
          lang={lang}
        />
      </div>

      {/* Custom fields — dynamically rendered from schema */}
      {customFields.map((field, idx) => (
        <CustomFieldRenderer
          key={field.id}
          field={field}
          value={responses[field.id]}
          onChange={setResponse}
          lang={lang}
          index={idx + 1}
          total={customFields.length}
        />
      ))}

      {/* Description (always optional, not in schema custom_fields) */}
      <div className="form-card">
        <div className="form-card-label">
          <span className="sec-num" />
          {t("form.section_description")}
          <span className="sec-optional">{t("form.optional")}</span>
        </div>
        <p className="form-pii-warning">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ display: "inline", verticalAlign: "middle", marginRight: 5, flexShrink: 0 }}>
            <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          {t("form.description_pii_warning")}
        </p>
        <textarea
          className="description-textarea"
          placeholder={t("form.description_placeholder")}
          value={typeof responses["description"] === "string" ? responses["description"] : ""}
          onChange={(e) => setResponse("description", e.target.value)}
          rows={3}
        />
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={!canSubmit}
      >
        {submitting ? t("form.submitting") : t("form.submit")}
      </button>

    </form>
  );
}
