import axios from "axios";

const isNative = window.Capacitor?.isNativePlatform?.();
const API_BASE = isNative
  ? "http://localhost:8000/api/v1"
  : "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// --- Simple in-memory GET cache (60s TTL) ---
const _cache = new Map();
const CACHE_TTL = 60_000;
const CACHEABLE = ["/communities/", "/users/", "/labels"];

function getCacheKey(config) {
  if (config.method !== "get") return null;
  const url = config.url || "";
  if (!CACHEABLE.some((p) => url.includes(p))) return null;
  const params = config.params ? JSON.stringify(config.params) : "";
  return `${url}|${params}`;
}

// Invalidate cache entries that match a mutation's resource
function invalidateCache(url) {
  for (const key of _cache.keys()) {
    if (key.startsWith(url.split("?")[0])) _cache.delete(key);
  }
}

// Return cached response for stable GET endpoints
api.interceptors.request.use((config) => {
  const key = getCacheKey(config);
  if (key) {
    const entry = _cache.get(key);
    if (entry && Date.now() - entry.ts < CACHE_TTL) {
      config.adapter = () => Promise.resolve(entry.res);
      return config;
    }
  }
  return config;
});

// Attach the access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Cache successful GET responses & invalidate on mutations
api.interceptors.response.use(
  (res) => {
    const config = res.config;
    const key = getCacheKey(config);
    if (key) _cache.set(key, { res, ts: Date.now() });
    // Invalidate on mutations
    if (["post", "put", "patch", "delete"].includes(config.method)) {
      invalidateCache(config.url || "");
    }
    return res;
  },
  (error) => Promise.reject(error),
);

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
