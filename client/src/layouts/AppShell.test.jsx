import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock dependencies
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser", is_verified: true },
    loading: false,
  })),
}));

vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
  })),
}));

vi.mock("./AppShell.module.css", () => ({ default: {} }));

// Mock child components
vi.mock("../components/BottomTabBar", () => ({
  default: () => <nav data-testid="bottom-tab-bar">BottomTabBar</nav>,
}));

vi.mock("../components/Sidebar", () => ({
  default: () => <aside data-testid="sidebar">Sidebar</aside>,
}));

vi.mock("../components/VerificationBanner", () => ({
  default: () => <div data-testid="verification-banner">Verify email</div>,
}));

vi.mock("../components/ui/Spinner", () => ({
  default: () => <span data-testid="spinner" role="status" aria-label="Loading" />,
}));

import AppShell from "./AppShell";
import { useAuth } from "../contexts/AuthContext";

const renderWithRouter = (ui) =>
  render(<MemoryRouter>{ui}</MemoryRouter>);

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({
      user: { id: 1, username: "testuser", is_verified: true },
      loading: false,
    });
  });

  it("renders Sidebar, BottomTabBar, and main content area when authenticated", () => {
    renderWithRouter(<AppShell />);

    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-tab-bar")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("shows loading spinner when auth is loading", () => {
    useAuth.mockReturnValue({ user: null, loading: true });

    renderWithRouter(<AppShell />);

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("sidebar")).not.toBeInTheDocument();
  });

  it("redirects to /login when user is not authenticated", () => {
    useAuth.mockReturnValue({ user: null, loading: false });

    renderWithRouter(<AppShell />);

    // Navigate component renders nothing visible; sidebar and bottom bar should not appear
    expect(screen.queryByTestId("sidebar")).not.toBeInTheDocument();
    expect(screen.queryByTestId("bottom-tab-bar")).not.toBeInTheDocument();
  });

  it("shows VerificationBanner when user is not verified", () => {
    useAuth.mockReturnValue({
      user: { id: 1, username: "testuser", is_verified: false },
      loading: false,
    });

    renderWithRouter(<AppShell />);

    expect(screen.getByTestId("verification-banner")).toBeInTheDocument();
  });

  it("does not show VerificationBanner when user is verified", () => {
    renderWithRouter(<AppShell />);

    expect(screen.queryByTestId("verification-banner")).not.toBeInTheDocument();
  });
});
