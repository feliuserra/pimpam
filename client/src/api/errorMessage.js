/**
 * Extract a user-friendly error message from an Axios error.
 *
 * Priority:
 * 1. Status-specific messages (429, 413, 401, 503)
 * 2. The `detail` string from the FastAPI response body
 * 3. The provided fallback
 */
const STATUS_MESSAGES = {
  429: "You're doing that too fast. Wait a moment and try again.",
  413: "That file is too large. Try a smaller one.",
  401: "Your session expired. Please log in again.",
  503: "This feature is temporarily unavailable. Try again later.",
};

export default function errorMessage(err, fallback = "Something went wrong.") {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;

  if (status && STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];
  if (typeof detail === "string" && detail.length > 0 && detail.length < 200) return detail;
  return fallback;
}
