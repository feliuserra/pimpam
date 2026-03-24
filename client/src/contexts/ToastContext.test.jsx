import { renderHook, act } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ToastProvider, useToast } from "./ToastContext";

describe("ToastContext", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  const wrapper = ({ children }) => <ToastProvider>{children}</ToastProvider>;

  it("addToast shows a toast message", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Hello!", "info");
    });

    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("auto-dismisses toast after duration", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Temporary", "success", 2000);
    });

    expect(screen.getByText("Temporary")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.queryByText("Temporary")).not.toBeInTheDocument();
  });

  it("can show multiple toasts", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("First", "info");
      result.current.addToast("Second", "error");
    });

    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("dismiss button removes toast", async () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.addToast("Dismissable", "info");
    });

    expect(screen.getByText("Dismissable")).toBeInTheDocument();

    const closeBtn = screen.getByLabelText("Dismiss");
    act(() => {
      closeBtn.click();
    });

    expect(screen.queryByText("Dismissable")).not.toBeInTheDocument();
  });

  it("throws when useToast is used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useToast());
    }).toThrow("useToast must be used within ToastProvider");

    spy.mockRestore();
  });
});
