import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import Offline from "./Offline";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Offline", () => {
  it("renders heading and explanatory text", () => {
    render(<Offline />);

    expect(
      screen.getByRole("heading", { name: /you appear to be offline/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Check your internet connection and try again."),
    ).toBeInTheDocument();
  });

  it("renders a retry button", () => {
    render(<Offline />);

    expect(
      screen.getByRole("button", { name: /retry/i }),
    ).toBeInTheDocument();
  });

  it("calls window.location.reload when retry button is clicked", () => {
    // Mock window.location.reload
    const reloadMock = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload: reloadMock },
      writable: true,
    });

    render(<Offline />);

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(reloadMock).toHaveBeenCalled();
  });
});
