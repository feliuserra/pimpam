import api from "./client";

export const list = (params) => api.get("/communities", { params });

export const listJoined = () => api.get("/communities/joined");

export const create = (data) => api.post("/communities", data);

export const get = (name) => api.get(`/communities/${name}`);

export const getPosts = (name, params) =>
  api.get(`/communities/${name}/posts`, { params });

export const join = (name) => api.post(`/communities/${name}/join`);

export const leave = (name) => api.post(`/communities/${name}/leave`);

export const getMemberKarma = (name, username) =>
  api.get(`/communities/${name}/members/${username}/karma`);

export const update = (name, data) => api.patch(`/communities/${name}`, data);

export const getAuditLog = (name, params) =>
  api.get(`/communities/${name}/audit-log`, { params });
