const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface SubmitResult {
  report_id: string;
  map_url: string;
  badges_awarded?: string[];
}

export async function submitReport(
  fields: Record<string, string>,
  photoBase64: string | null
): Promise<SubmitResult> {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    formData.append(key, value);
  }

  if (photoBase64) {
    const blob = await fetch(photoBase64).then((r) => r.blob());
    formData.append("photo", blob, "photo.jpg");
  }

  const response = await fetch(`${API_BASE}/v1/reports`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error ?? `HTTP ${response.status}`);
  }

  return response.json();
}
