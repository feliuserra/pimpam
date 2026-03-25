import api from "./client";

export const trending = (limit = 20) =>
  api.get("/hashtags/trending", { params: { limit } });

export const getHashtag = (name) => api.get(`/hashtags/${name}`);

export const getPostsByHashtag = (name, params = {}) =>
  api.get(`/hashtags/${name}/posts`, { params });
