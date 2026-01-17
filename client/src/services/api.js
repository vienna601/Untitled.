const API_BASE = "http://localhost:8000";

export async function fetchTodayPrompt() {
  const res = await fetch(`${API_BASE}/prompt/today`);
  if (!res.ok) throw new Error("Failed to fetch daily prompt");
  return res.json(); // { prompt: { id, category, prompt } }
}

export async function fetchWeeklyInsights(entries) {
  const res = await fetch(`${API_BASE}/insights/weekly`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries }),
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(
      `Insights failed (${res.status}): ${msg || res.statusText}`,
    );
  }

  return res.json();
}

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
