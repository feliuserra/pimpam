import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useMediaQuery } from "./useMediaQuery";

describe("useMediaQuery", () => {
  let listeners;
  let matchState;

  beforeEach(() => {
    listeners = [];
    matchState = false;
    window.matchMedia = vi.fn((query) => ({
      matches: matchState,
      media: query,
      addEventListener: (_, fn) => listeners.push(fn),
      removeEventListener: (_, fn) => {
        listeners = listeners.filter((l) => l !== fn);
      },
    }));
  });

  it("returns initial match state", () => {
    matchState = true;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(true);
  });

  it("returns false when query does not match", () => {
    matchState = false;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(false);
  });

  it("updates when media query changes", () => {
    matchState = false;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(false);

    act(() => {
      listeners.forEach((fn) => fn({ matches: true }));
    });
    expect(result.current).toBe(true);
  });

  it("cleans up listener on unmount", () => {
    const { unmount } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(listeners.length).toBe(1);
    unmount();
    expect(listeners.length).toBe(0);
  });
});
