import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/notifications", () => ({
  list: vi.fn(),
  markAllRead: vi.fn(),
  markRead: vi.fn(),
}));

// Mock contexts
const mockClearNotifications = vi.fn();
const mockDecrementNotifications = vi.fn();
const mockRefetch = vi.fn();
vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 3,
    unreadMessages: 0,
    clearNotifications: mockClearNotifications,
    decrementNotifications: mockDecrementNotifications,
    refetch: mockRefetch,
  })),
}));
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));
vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));
vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => vi.fn()),
}));

// Mock routing
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: vi.fn(() => vi.fn()),
    Link: ({ children, to }) => <a href={to}>{children}</a>,
  };
});

// Mock complex child components
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));
vi.mock("../components/NotificationItem", () => ({
  default: ({ notification, onRead }) => (
    <div data-testid="notification-item" onClick={() => onRead(notification.id)}>
      {notification.type} - {notification.is_read ? "read" : "unread"}
    </div>
  ),
}));

import * as notificationsApi from "../api/notifications";
import Notifications from "./Notifications";

// Mock IntersectionObserver for useInfiniteList
beforeEach(() => {
  global.IntersectionObserver = vi.fn(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.clearAllMocks();
});

describe("Notifications", () => {
  const sampleNotifications = [
    {
      id: 1,
      type: "follow",
      actor_username: "alice",
      actor_avatar_url: null,
      is_read: false,
      created_at: new Date().toISOString(),
    },
    {
      id: 2,
      type: "new_comment",
      actor_username: "bob",
      actor_avatar_url: null,
      post_id: 10,
      is_read: false,
      created_at: new Date().toISOString(),
    },
    {
      id: 3,
      type: "vote",
      actor_username: "charlie",
      actor_avatar_url: null,
      post_id: 11,
      is_read: true,
      created_at: new Date().toISOString(),
    },
  ];

  it("shows spinner while loading", () => {
    notificationsApi.list.mockReturnValue(new Promise(() => {}));

    render(<Notifications />);

    // The component may render multiple spinners (initial + sentinel); verify at least one exists
    const spinners = screen.getAllByRole("status", { name: "Loading" });
    expect(spinners.length).toBeGreaterThanOrEqual(1);
  });

  it("renders notification items", async () => {
    notificationsApi.list.mockResolvedValue({ data: sampleNotifications });

    render(<Notifications />);

    await waitFor(() => {
      expect(screen.getAllByTestId("notification-item")).toHaveLength(3);
    });

    expect(screen.getByText(/follow/)).toBeInTheDocument();
    expect(screen.getByText(/new_comment/)).toBeInTheDocument();
    expect(screen.getByText(/vote/)).toBeInTheDocument();
  });

  it("mark all read button calls API", async () => {
    notificationsApi.list.mockResolvedValue({ data: sampleNotifications });
    notificationsApi.markAllRead.mockResolvedValue({});

    render(<Notifications />);

    await waitFor(() => {
      expect(screen.getAllByTestId("notification-item")).toHaveLength(3);
    });

    // The mark-all-read button should be present since there are unread items
    const markAllBtn = screen.getByRole("button", { name: /mark all as read/i });
    expect(markAllBtn).toBeInTheDocument();

    fireEvent.click(markAllBtn);

    await waitFor(() => {
      expect(notificationsApi.markAllRead).toHaveBeenCalledTimes(1);
    });

    expect(mockClearNotifications).toHaveBeenCalled();
  });

  it("shows empty state", async () => {
    notificationsApi.list.mockResolvedValue({ data: [] });

    render(<Notifications />);

    await waitFor(() => {
      expect(screen.getByText("No notifications yet.")).toBeInTheDocument();
    });
  });
});
