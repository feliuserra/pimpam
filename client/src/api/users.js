import api from "./client";

export const getMe = () => api.get("/users/me");

export const updateMe = (data) => api.patch("/users/me", data);

export const getUser = (username) => api.get(`/users/${username}`);

export const getUserPosts = (username, params) =>
  api.get(`/users/${username}/posts`, { params });

export const getFollowers = (username, params) =>
  api.get(`/users/${username}/followers`, { params });

export const getFollowing = (username, params) =>
  api.get(`/users/${username}/following`, { params });

export const follow = (username) => api.post(`/users/${username}/follow`);

export const unfollow = (username) => api.delete(`/users/${username}/follow`);

export const deleteAccount = (password) =>
  api.post("/users/me/delete", { password });

export const cancelDeletion = () => api.post("/users/me/delete/cancel");

export const exportData = () => api.get("/users/me/data-export");

export const getSuggestions = () => api.get("/users/me/suggestions");

export const pinPost = (postId) => api.post(`/users/me/pin/${postId}`);

export const unpinPost = () => api.delete("/users/me/pin");

export const getCommunityStats = (username) =>
  api.get(`/users/${username}/community-stats`);

export const autocompleteUsers = (q, limit = 5) =>
  api.get("/users/autocomplete", { params: { q, limit } });
