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

vi.mock("./Sidebar.module.css", () => ({ default: {} }));

// Mock icon components
vi.mock("./ui/icons/BellIcon", () => ({ default: () => <span data-testid="bell-icon" /> }));
vi.mock("./ui/icons/CommunityIcon", () => ({ default: () => <span data-testid="community-icon" /> }));
vi.mock("./ui/icons/FriendsIcon", () => ({ default: () => <span data-testid="friends-icon" /> }));
vi.mock("./ui/icons/HomeIcon", () => ({ default: () => <span data-testid="home-icon" /> }));
vi.mock("./ui/icons/TrendingIcon", () => ({ default: () => <span data-testid="trending-icon" /> }));
vi.mock("./ui/icons/MessageIcon", () => ({ default: () => <span data-testid="message-icon" /> }));
vi.mock("./ui/icons/UserIcon", () => ({ default: () => <span data-testid="user-icon" /> }));

import Sidebar from "./Sidebar";
import { useAuth } from "../contexts/AuthContext";
import { useNotifications } from "../contexts/NotificationContext";

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
    useNotifications.mockReturnValue({ unreadNotifications: 0, unreadMessages: 0 });
  });

  it("renders all navigation links and the logo", () => {
    wrap(<Sidebar />);

    expect(screen.getByText("PimPam")).toBeInTheDocument();
    expect(screen.getByText("Feed")).toBeInTheDocument();
    expect(screen.getByText("Friends")).toBeInTheDocument();
    expect(screen.getByText("Communities")).toBeInTheDocument();
    expect(screen.getByText("Discover")).toBeInTheDocument();
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("has correct aria-label on the aside element", () => {
    wrap(<Sidebar />);

    expect(screen.getByLabelText("Main navigation")).toBeInTheDocument();
  });

  it("displays unread messages badge when count > 0", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 0, unreadMessages: 5 });

    wrap(<Sidebar />);

    expect(screen.getByLabelText("5 unread")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("displays unread notifications badge when count > 0", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 3, unreadMessages: 0 });

    wrap(<Sidebar />);

    expect(screen.getByLabelText("3 unread")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("caps badge display at 99+", () => {
    useNotifications.mockReturnValue({ unreadNotifications: 150, unreadMessages: 0 });

    wrap(<Sidebar />);

    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("does not show badges when counts are 0", () => {
    wrap(<Sidebar />);

    expect(screen.queryByLabelText(/unread/)).not.toBeInTheDocument();
  });

  it("links Profile to the current user's profile URL", () => {
    wrap(<Sidebar />);

    const profileLink = screen.getByText("Profile").closest("a");
    expect(profileLink).toHaveAttribute("href", "/u/testuser");
  });
});
