import { useEffect, useRef, useState } from "react";

export interface LiveReport {
  report_id: string;
  building_id: string | null;
  submitted_at: string;
  damage_level: string;
  channel: string;
  coordinates: [number, number] | null;
}

const WS_URL = import.meta.env.VITE_WS_URL ?? "wss://api.crisisplatform.io/ws";

export function useLiveReports(crisisEventId: string) {
  const [reports, setReports] = useState<LiveReport[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/reports?crisis_event_id=${crisisEventId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const report: LiveReport = JSON.parse(event.data);
        setReports((prev) => [report, ...prev].slice(0, 200));
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [crisisEventId]);

  return { reports, connected };
}
