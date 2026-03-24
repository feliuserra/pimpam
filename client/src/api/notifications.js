import api from "./client";

export const list = (params) => api.get("/notifications", { params });

export const getUnreadCount = () => api.get("/notifications/unread-count");

export const markAllRead = () => api.patch("/notifications/read-all");

export const markRead = (id) => api.patch(`/notifications/${id}/read`);

export const getPreferences = () => api.get("/notifications/preferences");

export const updatePreference = (notification_type, enabled) =>
  api.patch("/notifications/preferences", { notification_type, enabled });
