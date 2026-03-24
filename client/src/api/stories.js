import api from "./client";

export const create = (data) => api.post("/stories", data);

export const getFeed = (params) => api.get("/stories/feed", { params });

export const remove = (id) => api.delete(`/stories/${id}`);

export const report = (id) => api.post(`/stories/${id}/report`);
