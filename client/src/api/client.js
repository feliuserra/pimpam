import axios from "axios";

const isNative = window.Capacitor?.isNativePlatform?.();
const API_BASE = isNative
  ? "http://192.168.1.34:8000/api/v1"
  : "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach the access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, attempt a token refresh then retry once.
// Skip refresh for auth endpoints — login/register 401s should surface to the caller.
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const url = original?.url || "";
    const isAuthRoute = url.startsWith("/auth/");
    if (error.response?.status === 401 && !original._retry && !isAuthRoute) {
      original._retry = true;
      try {
        const refresh_token = localStorage.getItem("refresh_token");
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        // Refresh failed — clear tokens and send to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
