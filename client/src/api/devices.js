import api from "./client";

export const registerDevice = (data) => api.post("/devices", data);

export const getMyDevices = () => api.get("/devices");

export const renameDevice = (id, name) =>
  api.patch(`/devices/${id}`, { device_name: name });

export const revokeDevice = (id) => api.delete(`/devices/${id}`);

export const getUserDeviceKeys = (username) =>
  api.get(`/users/${username}/devices`);

export const uploadBackup = (deviceId, data) =>
  api.post(`/devices/${deviceId}/backup`, data);

export const getBackup = (deviceId) =>
  api.get(`/devices/${deviceId}/backup`);

export const deleteBackup = (deviceId) =>
  api.delete(`/devices/${deviceId}/backup`);

export const getAvailableBackups = () =>
  api.get("/devices/backups/available");
