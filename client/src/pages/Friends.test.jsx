import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/users", () => ({
  getFollowers: vi.fn(),
  getFollowing: vi.fn(),
  getSuggestions: vi.fn(),
}));
vi.mock("../api/friendGroups", () => ({
  list: vi.fn(),
  create: vi.fn(),
  getCloseFriends: vi.fn(),
  getDetail: vi.fn(),
  addMember: vi.fn(),
  removeMember: vi.fn(),
  remove: vi.fn(),
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

// Mock contexts
const mockUser = { id: 1, username: "testuser" };
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: mockUser })),
}));
vi.mock("../contexts/CloseFriendsContext", () => ({
  useCloseFriends: vi.fn(() => ({
    closeFriendIds: new Set(),
    isCloseFriend: () => false,
    refresh: vi.fn(),
  })),
}));
vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));
vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
    clearNotifications: vi.fn(),
    decrementNotifications: vi.fn(),
  })),
}));
vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: vi.fn() })),
}));

// Mock child components
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));
vi.mock("../components/UserCard", () => ({
  default: ({ user }) => <div data-testid="user-card">{user.username}</div>,
}));
vi.mock("../components/ui/Spinner", () => ({
  default: () => <div role="status" aria-label="Loading">Loading...</div>,
}));

import * as usersApi from "../api/users";
import * as friendGroupsApi from "../api/friendGroups";
import Friends from "./Friends";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Friends", () => {
  const followingUsers = [
    { id: 2, username: "alice", display_name: "Alice" },
    { id: 3, username: "bob", display_name: "Bob" },
  ];

  const followerUsers = [
    { id: 4, username: "charlie", display_name: "Charlie" },
  ];

  it("renders all five tabs", () => {
    friendGroupsApi.getCloseFriends.mockReturnValue(new Promise(() => {}));

    render(<Friends />);

    expect(screen.getByRole("tab", { name: "Close Friends" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Following" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Followers" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Groups" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Suggestions" })).toBeInTheDocument();
    expect(screen.getByText("Friends")).toBeInTheDocument();
  });

  it("shows spinner while Close Friends tab is loading", () => {
    friendGroupsApi.getCloseFriends.mockReturnValue(new Promise(() => {}));

    render(<Friends />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("renders following users on the Following tab", async () => {
    friendGroupsApi.getCloseFriends.mockResolvedValue({ data: { members: [] } });
    usersApi.getFollowing.mockResolvedValue({ data: followingUsers });

    render(<Friends />);

    // Switch to Following tab
    fireEvent.click(screen.getByRole("tab", { name: "Following" }));

    await waitFor(() => {
      expect(screen.getAllByTestId("user-card")).toHaveLength(2);
    });

    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(screen.getByText("bob")).toBeInTheDocument();
  });

  it("switches to Followers tab and loads followers", async () => {
    friendGroupsApi.getCloseFriends.mockResolvedValue({ data: { members: [] } });
    usersApi.getFollowers.mockResolvedValue({ data: followerUsers });

    render(<Friends />);

    // Switch to Followers tab
    fireEvent.click(screen.getByRole("tab", { name: "Followers" }));

    await waitFor(() => {
      expect(screen.getByText("charlie")).toBeInTheDocument();
    });

    expect(usersApi.getFollowers).toHaveBeenCalledWith("testuser", { limit: 100 });
  });

  it("shows empty state when no following", async () => {
    friendGroupsApi.getCloseFriends.mockResolvedValue({ data: { members: [] } });
    usersApi.getFollowing.mockResolvedValue({ data: [] });

    render(<Friends />);

    // Switch to Following tab
    fireEvent.click(screen.getByRole("tab", { name: "Following" }));

    await waitFor(() => {
      expect(screen.getByText("No following yet.")).toBeInTheDocument();
    });
  });

  it("switches to Groups tab and shows create form", async () => {
    friendGroupsApi.getCloseFriends.mockResolvedValue({ data: { members: [] } });
    friendGroupsApi.list.mockResolvedValue({ data: [] });
    usersApi.getFollowing.mockResolvedValue({ data: [] });

    render(<Friends />);

    // Switch to Groups tab
    fireEvent.click(screen.getByRole("tab", { name: "Groups" }));

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("New group name..."),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("No friend groups yet.")).toBeInTheDocument();
  });

  it("switches to Suggestions tab and loads suggestions", async () => {
    friendGroupsApi.getCloseFriends.mockResolvedValue({ data: { members: [] } });
    usersApi.getSuggestions.mockResolvedValue({
      data: [{ id: 5, username: "diana", display_name: "Diana" }],
    });

    render(<Friends />);

    // Switch to Suggestions tab
    fireEvent.click(screen.getByRole("tab", { name: "Suggestions" }));

    await waitFor(() => {
      expect(screen.getByText("diana")).toBeInTheDocument();
    });

    expect(
      screen.getByText("People followed by your friends"),
    ).toBeInTheDocument();
  });
});
