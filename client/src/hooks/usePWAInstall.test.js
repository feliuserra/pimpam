import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { usePWAInstall } from "./usePWAInstall";

describe("usePWAInstall", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("canInstall is false initially", () => {
    const { result } = renderHook(() => usePWAInstall());
    expect(result.current.canInstall).toBe(false);
  });

  it("sets canInstall to true when beforeinstallprompt fires", () => {
    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      event.preventDefault = vi.fn();
      window.dispatchEvent(event);
    });

    expect(result.current.canInstall).toBe(true);
  });

  it("prevents default on beforeinstallprompt event", () => {
    renderHook(() => usePWAInstall());

    const event = new Event("beforeinstallprompt");
    event.preventDefault = vi.fn();

    act(() => {
      window.dispatchEvent(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("promptInstall returns false when no deferred prompt", async () => {
    const { result } = renderHook(() => usePWAInstall());

    let outcome;
    await act(async () => {
      outcome = await result.current.promptInstall();
    });

    expect(outcome).toBe(false);
  });

  it("promptInstall calls prompt() and returns true on acceptance", async () => {
    const { result } = renderHook(() => usePWAInstall());

    const mockPrompt = {
      prompt: vi.fn(),
      userChoice: Promise.resolve({ outcome: "accepted" }),
      preventDefault: vi.fn(),
    };

    act(() => {
      const event = new Event("beforeinstallprompt");
      event.preventDefault = vi.fn();
      event.prompt = mockPrompt.prompt;
      event.userChoice = mockPrompt.userChoice;
      window.dispatchEvent(event);
    });

    expect(result.current.canInstall).toBe(true);

    let outcome;
    await act(async () => {
      outcome = await result.current.promptInstall();
    });

    expect(outcome).toBe(true);
    expect(result.current.canInstall).toBe(false);
  });

  it("promptInstall returns false on dismissal", async () => {
    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      event.preventDefault = vi.fn();
      event.prompt = vi.fn();
      event.userChoice = Promise.resolve({ outcome: "dismissed" });
      window.dispatchEvent(event);
    });

    let outcome;
    await act(async () => {
      outcome = await result.current.promptInstall();
    });

    expect(outcome).toBe(false);
    expect(result.current.canInstall).toBe(false);
  });

  it("cleans up event listener on unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => usePWAInstall());

    expect(addSpy).toHaveBeenCalledWith("beforeinstallprompt", expect.any(Function));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("beforeinstallprompt", expect.any(Function));

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});
