//key used to store entries in localStorage
const KEY = "entries_v1";

// Load all entries from localStorage
export function loadEntries() {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}
// Save a new entry to localStorage
export function saveEntry(entry) {
  const entries = loadEntries();
  entries.push(entry);
  localStorage.setItem(KEY, JSON.stringify(entries));
}
// Get entries from the last 7 days
export function getLast7DaysEntries() {
  const now = Date.now();
  const cutoff = now - 7 * 24 * 60 * 60 * 1000;
  return loadEntries().filter((e) => Number(e.timestamp) >= cutoff);
}
