import api from "./client";

export const list = () => api.get("/friend-groups");

export const create = (name) => api.post("/friend-groups", { name });

export const getCloseFriends = () => api.get("/friend-groups/close-friends");

export const getDetail = (id) => api.get(`/friend-groups/${id}`);

export const rename = (id, name) =>
  api.patch(`/friend-groups/${id}`, { name });

export const remove = (id) => api.delete(`/friend-groups/${id}`);

export const addMember = (id, user_id) =>
  api.post(`/friend-groups/${id}/members`, { user_id });

export const removeMember = (id, userId) =>
  api.delete(`/friend-groups/${id}/members/${userId}`);
