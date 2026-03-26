const KEY = "pimpam_seen_stories";

/**
 * Returns a Set of story IDs the user has already viewed.
 * Stored in localStorage only — never sent to the server.
 */
export function getSeenStories() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw));
  } catch {
    return new Set();
  }
}

/**
 * Mark an array of story IDs as seen.
 * Keeps the set capped at 500 entries to avoid unbounded growth.
 */
export function markStoriesSeen(ids) {
  const seen = getSeenStories();
  for (const id of ids) seen.add(id);

  // Cap at 500 — oldest entries naturally expire as stories do
  const arr = [...seen];
  const trimmed = arr.length > 500 ? arr.slice(arr.length - 500) : arr;

  try {
    localStorage.setItem(KEY, JSON.stringify(trimmed));
  } catch {
    // storage full — silently fail
  }
}
