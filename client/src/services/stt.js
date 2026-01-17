const API_BASE = "http://localhost:8000";

export async function transcribeAudioBlob(blob) {
  const form = new FormData();
  form.append("file", blob, "reflection.webm");

  const res = await fetch(`${API_BASE}/stt/transcribe`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`STT failed (${res.status}): ${msg || res.statusText}`);
  }

  return res.json();
}
