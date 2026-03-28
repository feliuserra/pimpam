import api from "./client";

export const send = (data) => api.post("/messages", data);

export const getInbox = () => api.get("/messages");

export const getConversation = (otherUserId, beforeId) =>
  api.get(`/messages/${otherUserId}`, {
    params: beforeId ? { before_id: beforeId } : undefined,
  });

export const getSingleMessage = (messageId) =>
  api.get(`/messages/single/${messageId}`);

export const deleteMessage = (messageId) =>
  api.delete(`/messages/${messageId}`);

export const markRead = (otherUserId) =>
  api.patch(`/messages/${otherUserId}/read`);
