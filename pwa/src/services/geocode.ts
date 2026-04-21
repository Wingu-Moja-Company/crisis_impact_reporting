/**
 * Client-side geocoding via OpenStreetMap Nominatim.
 * No API key required. Results biased to the crisis country.
 */

// Derive country from CRISIS_EVENT_ID prefix: "ke-flood-dev" → "ke"
const COUNTRY_CODE = (import.meta.env.VITE_CRISIS_EVENT_ID ?? "ke-flood-dev")
  .split("-")[0]
  .toLowerCase();

// Strip proximity words before geocoding: "Near Westlands Market" → "Westlands Market"
const PROXIMITY_RE =
  /^\s*(near|by|next to|opposite|behind|in front of|outside|beside|around|along|at)\s+/i;

export interface GeocodeResult {
  lat: number;
  lon: number;
  displayName: string; // short form, e.g. "Westlands Market, Woodvale Grove"
}

export async function geocodeLocation(
  query: string
): Promise<GeocodeResult | null> {
  const clean = query.replace(PROXIMITY_RE, "").trim();
  if (clean.length < 3) return null;

  const params = new URLSearchParams({
    q: clean,
    format: "json",
    limit: "1",
    countrycodes: COUNTRY_CODE,
    addressdetails: "0",
  });

  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?${params}`,
      { headers: { Accept: "application/json" } }
    );
    if (!res.ok) return null;
    const results: Array<{ lat: string; lon: string; display_name: string }> =
      await res.json();
    if (!results.length) return null;

    const r = results[0];
    const parts = r.display_name.split(",");
    const displayName = parts
      .slice(0, 2)
      .map((s) => s.trim())
      .join(", ");

    return { lat: parseFloat(r.lat), lon: parseFloat(r.lon), displayName };
  } catch {
    return null;
  }
}
