import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let store;

beforeEach(() => {
  store = {};
  vi.stubGlobal("localStorage", {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, val) => {
      store[key] = val;
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
  });

  window.matchMedia = vi.fn(() => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));

  // Reset data-theme attribute
  document.documentElement.removeAttribute("data-theme");

  vi.clearAllMocks();
});

// Dynamic import needed since getInitialTheme runs at module scope
// We re-import to avoid stale closure over localStorage
import { useTheme } from "./useTheme";

describe("useTheme", () => {
  it("defaults to light when no stored value and prefers-color-scheme is light", () => {
    window.matchMedia = vi.fn(() => ({ matches: false }));

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("defaults to dark when no stored value and prefers-color-scheme is dark", () => {
    window.matchMedia = vi.fn(() => ({ matches: true }));
    // Need to clear module cache for getInitialTheme to re-evaluate
    // But since useTheme calls useState(getInitialTheme), each render re-calls it
    // The initial state function captures matchMedia at call time
    const { result } = renderHook(() => useTheme());
    // matchMedia returns true for dark, so if no stored value, should be dark
    // Note: because useTheme uses useState(getInitialTheme), the initial call reads matchMedia
    expect(result.current.theme).toBe("dark");
  });

  it("uses stored theme from localStorage", () => {
    store.pimpam_theme = "dark";
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });

  it("sets data-theme attribute on document element", () => {
    store.pimpam_theme = "dark";
    renderHook(() => useTheme());
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("persists theme to localStorage on change", () => {
    const { result } = renderHook(() => useTheme());
    // Initial theme persisted
    expect(localStorage.setItem).toHaveBeenCalledWith("pimpam_theme", expect.any(String));
  });

  it("toggle switches from light to dark", () => {
    store.pimpam_theme = "light";
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("toggle switches from dark to light", () => {
    store.pimpam_theme = "dark";
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.theme).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("ignores invalid stored values and falls back to matchMedia", () => {
    store.pimpam_theme = "invalid-value";
    window.matchMedia = vi.fn(() => ({ matches: true }));
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });
});
