import api from "./client";

// --- Existing endpoints (unchanged) ---

export const getOverview = () => api.get("/admin/analytics/overview");

export const getTimeseries = (metric, days = 30) =>
  api.get(`/admin/analytics/timeseries?metric=${metric}&days=${days}`);

export const getTopCommunities = (days = 30, limit = 10) =>
  api.get(`/admin/analytics/top-communities?days=${days}&limit=${limit}`);

export const getModerationSummary = (days = 30) =>
  api.get(`/admin/analytics/moderation?days=${days}`);

// --- New endpoints ---

/**
 * Active users, new users, new posts, new messages within the given window.
 * @param {string} window - "1h" | "24h" | "7d" | "30d"
 */
export const getWindowOverview = (window = "24h") =>
  api.get(`/admin/analytics/window-overview?window=${window}`);

/**
 * Granular timeseries with auto-bucketing:
 *   1h → 5-min buckets, 24h → hourly, 7d/30d → daily.
 * @param {string} metric - "signups" | "posts" | "comments" | "messages" | "stories"
 * @param {string} window - "1h" | "24h" | "7d" | "30d"
 */
export const getGranularTimeseries = (metric, window = "24h") =>
  api.get(`/admin/analytics/granular-timeseries?metric=${metric}&window=${window}`);

/**
 * Login attempt counts, failure rate, password reset requests, new registrations,
 * and suspicious IP hashes (SHA-256, never plaintext).
 * @param {string} window - "1h" | "24h" | "7d" | "30d"
 */
export const getSecurityMetrics = (window = "1h") =>
  api.get(`/admin/analytics/security?window=${window}`);

/**
 * Active security alerts evaluated against the last hour.
 * Always fresh — never cached on the server.
 */
export const getSecurityAlerts = () =>
  api.get("/admin/analytics/security-alerts");
