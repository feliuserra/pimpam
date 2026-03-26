import api from "./client";

export const send = (data) => api.post("/messages", data);

export const getInbox = () => api.get("/messages");

export const getConversation = (otherUserId) =>
  api.get(`/messages/${otherUserId}`);

export const markRead = (otherUserId) =>
  api.patch(`/messages/${otherUserId}/read`);
