import api from "./client";

export const create = (data) => api.post("/issues", data);

export const list = (params) => api.get("/issues", { params });

export const get = (id) => api.get(`/issues/${id}`);

export const vote = (id) => api.post(`/issues/${id}/vote`);

export const unvote = (id) => api.delete(`/issues/${id}/vote`);

export const addComment = (id, data) =>
  api.post(`/issues/${id}/comments`, data);

export const listComments = (id, params) =>
  api.get(`/issues/${id}/comments`, { params });

export const update = (id, data) => api.patch(`/issues/${id}`, data);

export const close = (id) => api.post(`/issues/${id}/close`);

export const reopen = (id) => api.post(`/issues/${id}/reopen`);

export const votePoll = (issueId, optionId) =>
  api.post(`/issues/${issueId}/poll/vote`, { option_id: optionId });

export const unvotePoll = (issueId, optionId) =>
  api.delete(`/issues/${issueId}/poll/vote`, {
    data: { option_id: optionId },
  });
