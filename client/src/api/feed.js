import api from "./client";

export const getFeed = (params) => api.get("/feed", { params });

export const getTrending = (params) => api.get("/feed/trending", { params });

export const getNews = (params) => api.get("/feed/news", { params });

export const getForYou = (params) => api.get("/feed/for-you", { params });
