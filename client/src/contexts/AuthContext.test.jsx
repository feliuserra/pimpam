import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";

// Mock the API modules
vi.mock("../api/auth", () => ({
  login: vi.fn(),
}));

vi.mock("../api/users", () => ({
  getMe: vi.fn(),
}));

import * as authApi from "../api/auth";
import * as usersApi from "../api/users";

describe("AuthContext", () => {
  let store;

  beforeEach(() => {
    store = {};
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key) => store[key] ?? null),
      setItem: vi.fn((key, val) => { store[key] = val; }),
      removeItem: vi.fn((key) => { delete store[key]; }),
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

  it("finishes loading with no user when no token exists", async () => {
    // No token in localStorage — hydration skips the API call
    usersApi.getMe.mockRejectedValue(new Error("No token"));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user).toBe(null);
    // getMe should NOT have been called since there's no token
    expect(usersApi.getMe).not.toHaveBeenCalled();
  });

  it("hydrates user from token on mount", async () => {
    store.access_token = "valid-token";
    const mockUser = { id: 1, username: "donbenito", is_verified: true };
    usersApi.getMe.mockResolvedValue({ data: mockUser });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(usersApi.getMe).toHaveBeenCalledTimes(1);
  });

  it("clears tokens on hydration failure", async () => {
    store.access_token = "expired-token";
    store.refresh_token = "old-refresh";
    usersApi.getMe.mockRejectedValue({ response: { status: 401 } });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user).toBe(null);
    expect(localStorage.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorage.removeItem).toHaveBeenCalledWith("refresh_token");
  });

  it("login stores tokens and sets user", async () => {
    // No token initially — hydration skips getMe
    // After login, getMe is called to fetch profile
    usersApi.getMe.mockResolvedValue({ data: { id: 1, username: "donbenito" } });

    authApi.login.mockResolvedValue({
      data: { access_token: "new-access", refresh_token: "new-refresh" },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.login("donbenito", "password123");
    });

    expect(localStorage.setItem).toHaveBeenCalledWith("access_token", "new-access");
    expect(localStorage.setItem).toHaveBeenCalledWith("refresh_token", "new-refresh");
    expect(result.current.user).toEqual({ id: 1, username: "donbenito" });
  });

  it("logout clears user and tokens", async () => {
    store.access_token = "valid-token";
    const mockUser = { id: 1, username: "donbenito" };
    usersApi.getMe.mockResolvedValue({ data: mockUser });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBe(null);
    expect(localStorage.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorage.removeItem).toHaveBeenCalledWith("refresh_token");
  });

  it("updateUser merges fields into current user", async () => {
    store.access_token = "valid-token";
    const mockUser = { id: 1, username: "donbenito", bio: null };
    usersApi.getMe.mockResolvedValue({ data: mockUser });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    act(() => {
      result.current.updateUser({ bio: "Hello world" });
    });

    expect(result.current.user.bio).toBe("Hello world");
    expect(result.current.user.username).toBe("donbenito");
  });

  it("throws when useAuth is used outside provider", () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within AuthProvider");

    spy.mockRestore();
  });
});
