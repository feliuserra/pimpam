import api from "./client";

export const removePost = (name, postId) =>
  api.delete(`/communities/${name}/posts/${postId}`);

export const restorePost = (name, postId) =>
  api.post(`/communities/${name}/posts/${postId}/restore`);

export const removeComment = (name, commentId) =>
  api.delete(`/communities/${name}/comments/${commentId}`);

export const restoreComment = (name, commentId) =>
  api.post(`/communities/${name}/comments/${commentId}/restore`);

export const proposeBan = (name, data) =>
  api.post(`/communities/${name}/bans`, data);

export const voteBan = (name, proposalId) =>
  api.post(`/communities/${name}/bans/${proposalId}/vote`);

export const listBans = (name) => api.get(`/communities/${name}/bans`);

export const submitAppeal = (name, data) =>
  api.post(`/communities/${name}/appeals`, data);

export const voteAppeal = (name, appealId) =>
  api.post(`/communities/${name}/appeals/${appealId}/vote`);

export const listAppeals = (name) => api.get(`/communities/${name}/appeals`);

export const proposeMod = (name, data) =>
  api.post(`/communities/${name}/moderators`, data);

export const voteMod = (name, proposalId) =>
  api.post(`/communities/${name}/moderators/${proposalId}/vote`);

export const proposeTransfer = (name, data) =>
  api.post(`/communities/${name}/ownership-transfer`, data);

export const respondTransfer = (name, transferId, accept) =>
  api.post(`/communities/${name}/ownership-transfer/${transferId}/respond`, {
    accept,
  });

export const listReports = (name, status) => {
  const params = status ? `?status=${status}` : "";
  return api.get(`/communities/${name}/reports${params}`);
};

export const resolveReport = (name, reportId, action) =>
  api.post(`/communities/${name}/reports/${reportId}/resolve?action=${action}`);

export const listRemoved = (name) =>
  api.get(`/communities/${name}/removed`);

export const listTeam = (name) => api.get(`/communities/${name}/team`);
