import api from "./client";

export const send = (data) => api.post("/messages", data);

export const getInbox = (deviceId) =>
  api.get("/messages", {
    params: deviceId ? { device_id: deviceId } : undefined,
  });

export const getConversation = (otherUserId, beforeId, deviceId) =>
  api.get(`/messages/${otherUserId}`, {
    params: {
      ...(beforeId ? { before_id: beforeId } : {}),
      ...(deviceId ? { device_id: deviceId } : {}),
    },
  });

export const getSingleMessage = (messageId, deviceId) =>
  api.get(`/messages/single/${messageId}`, {
    params: deviceId ? { device_id: deviceId } : undefined,
  });

export const deleteMessage = (messageId) =>
  api.delete(`/messages/${messageId}`);

export const markRead = (otherUserId) =>
  api.patch(`/messages/${otherUserId}/read`);
