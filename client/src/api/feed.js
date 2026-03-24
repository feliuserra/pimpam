import api from "./client";

export const getFeed = (params) => api.get("/feed", { params });
