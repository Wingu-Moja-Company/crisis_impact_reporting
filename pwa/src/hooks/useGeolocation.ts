import { useState, useCallback } from "react";

export interface GpsCoords {
  lat: number;
  lon: number;
  accuracy: number;
}

export function useGeolocation() {
  const [coords, setCoords] = useState<GpsCoords | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const request = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported by this browser.");
      return;
    }
    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10_000 }
    );
  }, []);

  return { coords, error, loading, request };
}
