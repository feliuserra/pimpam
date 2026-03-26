import api from "./client";

export const getOverview = () => api.get("/admin/analytics/overview");

export const getTimeseries = (metric, days = 30) =>
  api.get(`/admin/analytics/timeseries?metric=${metric}&days=${days}`);

export const getTopCommunities = (days = 30, limit = 10) =>
  api.get(`/admin/analytics/top-communities?days=${days}&limit=${limit}`);

export const getModerationSummary = (days = 30) =>
  api.get(`/admin/analytics/moderation?days=${days}`);
