import api from "./client";

export const list = (postId, params) =>
  api.get(`/posts/${postId}/comments`, { params });

export const create = (postId, data) =>
  api.post(`/posts/${postId}/comments`, data);

export const listReplies = (commentId) =>
  api.get(`/comments/${commentId}/replies`);

export const remove = (commentId) => api.delete(`/comments/${commentId}`);

export const react = (commentId, reaction_type) =>
  api.post(`/comments/${commentId}/reactions`, { reaction_type });

export const removeReaction = (commentId, reactionType) =>
  api.delete(`/comments/${commentId}/reactions/${reactionType}`);
