import api from "./client";

export const create = (data) => api.post("/posts", data);

export const get = (id) => api.get(`/posts/${id}`);

export const edit = (id, data) => api.patch(`/posts/${id}`, data);

export const remove = (id) => api.delete(`/posts/${id}`);

export const vote = (id, direction) =>
  api.post(`/posts/${id}/vote`, { direction });

export const retractVote = (id) => api.delete(`/posts/${id}/vote`);

export const boost = (id) => api.post(`/posts/${id}/boost`);

export const share = (id, data) => api.post(`/posts/${id}/share`, data);

export const getLinkPreview = (url) =>
  api.get("/posts/link-preview", { params: { url } });
