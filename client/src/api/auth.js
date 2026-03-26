import api from "./client";

export const login = (username, password, totp_code) =>
  api.post("/auth/login", { username: username.toLowerCase(), password, ...(totp_code && { totp_code }) });

export const register = (data) => api.post("/auth/register", data);

export const refresh = (refresh_token) =>
  api.post("/auth/refresh", { refresh_token });

export const logout = () => api.post("/auth/logout");

export const changePassword = (data) => api.post("/auth/change-password", data);

export const requestPasswordReset = (email, mode = "link") =>
  api.post("/auth/password-reset/request", { email, mode });

export const confirmPasswordReset = (token, new_password) =>
  api.post("/auth/password-reset/confirm", { token, new_password });

export const verifyEmail = (token) => api.get(`/auth/verify?token=${token}`);

export const resendVerification = () => api.post("/auth/resend-verification");

export const totpSetup = () => api.post("/auth/totp/setup");

export const totpVerify = (code) => api.post("/auth/totp/verify", { code });

export const totpDisable = (password, code) =>
  api.post("/auth/totp/disable", { password, code });
