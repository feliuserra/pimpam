import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useIdleTimer } from "./useIdleTimer";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useIdleTimer", () => {
  it("calls onIdle after timeout with no activity", () => {
    const onIdle = vi.fn();
    renderHook(() => useIdleTimer({ timeoutMs: 5000, onIdle, enabled: true }));

    expect(onIdle).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(5000));

    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it("resets timer on user activity", () => {
    const onIdle = vi.fn();
    renderHook(() => useIdleTimer({ timeoutMs: 5000, onIdle, enabled: true }));

    act(() => vi.advanceTimersByTime(3000));
    expect(onIdle).not.toHaveBeenCalled();

    // Simulate activity
    act(() => window.dispatchEvent(new Event("mousedown")));

    // Advance past original timeout — should NOT fire because timer was reset
    act(() => vi.advanceTimersByTime(3000));
    expect(onIdle).not.toHaveBeenCalled();

    // Advance to full timeout from reset point
    act(() => vi.advanceTimersByTime(2000));
    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it("does not fire when disabled", () => {
    const onIdle = vi.fn();
    renderHook(() => useIdleTimer({ timeoutMs: 1000, onIdle, enabled: false }));

    act(() => vi.advanceTimersByTime(5000));

    expect(onIdle).not.toHaveBeenCalled();
  });

  it("cleans up on unmount", () => {
    const onIdle = vi.fn();
    const { unmount } = renderHook(() =>
      useIdleTimer({ timeoutMs: 5000, onIdle, enabled: true }),
    );

    unmount();

    act(() => vi.advanceTimersByTime(10000));

    expect(onIdle).not.toHaveBeenCalled();
  });

  it("resets on keyboard and touch events", () => {
    const onIdle = vi.fn();
    renderHook(() => useIdleTimer({ timeoutMs: 5000, onIdle, enabled: true }));

    act(() => vi.advanceTimersByTime(4000));
    act(() => window.dispatchEvent(new Event("keydown")));

    act(() => vi.advanceTimersByTime(4000));
    act(() => window.dispatchEvent(new Event("touchstart")));

    act(() => vi.advanceTimersByTime(4000));
    expect(onIdle).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(1000));
    expect(onIdle).toHaveBeenCalledTimes(1);
  });
});
