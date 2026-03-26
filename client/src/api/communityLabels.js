import api from "./client";

export const list = (name) => api.get(`/communities/${name}/labels`);

export const create = (name, data) =>
  api.post(`/communities/${name}/labels`, data);

export const update = (name, labelId, data) =>
  api.patch(`/communities/${name}/labels/${labelId}`, data);

export const remove = (name, labelId) =>
  api.delete(`/communities/${name}/labels/${labelId}`);

export const reorder = (name, ids) =>
  api.put(`/communities/${name}/labels/reorder`, { ids });
