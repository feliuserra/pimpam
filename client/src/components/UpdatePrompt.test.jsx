import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const mockUpdateServiceWorker = vi.fn();

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: vi.fn(() => ({
    needRefresh: [false],
    updateServiceWorker: mockUpdateServiceWorker,
  })),
}));

vi.mock("./UpdatePrompt.module.css", () => ({ default: {} }));

import UpdatePrompt from "./UpdatePrompt";
import { useRegisterSW } from "virtual:pwa-register/react";

describe("UpdatePrompt", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useRegisterSW.mockReturnValue({
      needRefresh: [false],
      updateServiceWorker: mockUpdateServiceWorker,
    });
  });

  it("renders nothing when no refresh is needed", () => {
    const { container } = render(<UpdatePrompt />);
    expect(container.innerHTML).toBe("");
  });

  it("renders the update banner when needRefresh is true", () => {
    useRegisterSW.mockReturnValue({
      needRefresh: [true],
      updateServiceWorker: mockUpdateServiceWorker,
    });

    render(<UpdatePrompt />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("A new version is available")).toBeInTheDocument();
    expect(screen.getByText("Update")).toBeInTheDocument();
  });

  it("calls updateServiceWorker when Update button is clicked", () => {
    useRegisterSW.mockReturnValue({
      needRefresh: [true],
      updateServiceWorker: mockUpdateServiceWorker,
    });

    render(<UpdatePrompt />);

    fireEvent.click(screen.getByText("Update"));
    expect(mockUpdateServiceWorker).toHaveBeenCalledWith(true);
  });

  it("dismisses the banner when dismiss button is clicked", () => {
    useRegisterSW.mockReturnValue({
      needRefresh: [true],
      updateServiceWorker: mockUpdateServiceWorker,
    });

    render(<UpdatePrompt />);

    expect(screen.getByText("A new version is available")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Dismiss"));

    expect(screen.queryByText("A new version is available")).not.toBeInTheDocument();
  });

  it("has accessible dismiss button with aria-label", () => {
    useRegisterSW.mockReturnValue({
      needRefresh: [true],
      updateServiceWorker: mockUpdateServiceWorker,
    });

    render(<UpdatePrompt />);

    expect(screen.getByLabelText("Dismiss")).toBeInTheDocument();
  });
});
