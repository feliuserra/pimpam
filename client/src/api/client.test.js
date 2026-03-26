import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import axios from "axios";

// We need to test the interceptor behavior, so we mock axios at the adapter level
describe("API client interceptor", () => {
  let api;

  beforeEach(async () => {
    // Reset module so interceptors are re-registered fresh
    vi.resetModules();

    // Mock localStorage
    const store = {};
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key) => store[key] ?? null),
      setItem: vi.fn((key, val) => { store[key] = val; }),
      removeItem: vi.fn((key) => { delete store[key]; }),
    });

    // Prevent window.location.href redirect
    delete window.location;
    window.location = { href: "" };

    const mod = await import("./client.js");
    api = mod.default;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches access token to requests", async () => {
    localStorage.setItem("access_token", "test-token-123");

    // Intercept at adapter level to check headers
    const adapter = vi.fn().mockResolvedValue({
      data: {},
      status: 200,
      statusText: "OK",
      headers: {},
      config: {},
    });

    await api.get("/test", { adapter });

    expect(adapter).toHaveBeenCalled();
    const config = adapter.mock.calls[0][0];
    expect(config.headers.Authorization).toBe("Bearer test-token-123");
  });

  it("skips refresh for auth endpoints on 401", async () => {
    localStorage.setItem("access_token", "expired");

    const adapter = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Invalid credentials" } },
      config: { url: "/auth/login", headers: {} },
    });

    await expect(api.post("/auth/login", {}, { adapter })).rejects.toBeTruthy();

    // Should NOT have redirected to /login (which would mean the refresh interceptor fired)
    // The error should propagate to the caller
    expect(window.location.href).toBe("");
  });

  it("does not attach token when none exists", async () => {
    // No token set in localStorage

    const adapter = vi.fn().mockResolvedValue({
      data: {},
      status: 200,
      statusText: "OK",
      headers: {},
      config: {},
    });

    await api.get("/test", { adapter });

    const config = adapter.mock.calls[0][0];
    expect(config.headers.Authorization).toBeUndefined();
  });
});
