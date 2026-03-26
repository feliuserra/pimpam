import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";

// Mock dependencies
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));

vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
  })),
}));

vi.mock("./BottomTabBar.module.css", () => ({ default: {} }));

// Mock icon components
vi.mock("./ui/icons/BellIcon", () => ({ default: () => <span data-testid="bell-icon" /> }));
vi.mock("./ui/icons/CommunityIcon", () => ({ default: () => <span data-testid="community-icon" /> }));
vi.mock("./ui/icons/HomeIcon", () => ({ default: () => <span data-testid="home-icon" /> }));
vi.mock("./ui/icons/MessageIcon", () => ({ default: () => <span data-testid="message-icon" /> }));
vi.mock("./ui/icons/UserIcon", () => ({ default: () => <span data-testid="user-icon" /> }));

import BottomTabBar from "./BottomTabBar";
import { useAuth } from "../contexts/AuthContext";
import { useNotifications } from "../contexts/NotificationContext";

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("BottomTabBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
    useNotifications.mockReturnValue({ unreadNotifications: 0, unreadMessages: 0 });
  });

  it("renders all 5 tabs with labels", () => {
    wrap(<BottomTabBar />);

    expect(screen.getByText("Feed")).toBeInTheDocument();
    expect(screen.getByText("Communities")).toBeInTheDocument();
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("has aria-label on nav element and each tab link", () => {
    wrap(<BottomTabBar />);

    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByLabelText("Feed")).toBeInTheDocument();
    expect(screen.getByLabelText("Communities")).toBeInTheDocument();
    expect(screen.getByLabelText("Messages")).toBeInTheDocument();
    expect(screen.getByLabelText("Notifications")).toBeInTheDocument();
    expect(screen.getByLabelText("Profile")).toBeInTheDocument();
  });

  it("shows unread messages badge", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 0, unreadMessages: 7 });

    wrap(<BottomTabBar />);

    expect(screen.getByLabelText("7 unread")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("shows unread notifications badge", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 12, unreadMessages: 0 });

    wrap(<BottomTabBar />);

    expect(screen.getByLabelText("12 unread")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("caps badge display at 99+", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 0, unreadMessages: 200 });

    wrap(<BottomTabBar />);

    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("does not render badges when counts are 0", () => {
    wrap(<BottomTabBar />);

    expect(screen.queryByLabelText(/unread/)).not.toBeInTheDocument();
  });

  it("links Profile to the user's profile page", () => {
    wrap(<BottomTabBar />);

    const profileLink = screen.getByLabelText("Profile");
    expect(profileLink).toHaveAttribute("href", "/u/testuser");
  });
});
