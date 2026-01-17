const API_BASE = "http://localhost:8000";

export async function fetchTodayPrompt() {
  const res = await fetch(`${API_BASE}/prompt/today`);
  if (!res.ok) 
    throw new Error("Failed to fetch daily prompt");
  return res.json(); // { prompt: { id, category, prompt } }
}
