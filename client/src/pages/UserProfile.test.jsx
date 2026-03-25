import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/users", () => ({
  getUser: vi.fn(),
  getUserPosts: vi.fn(),
  getFollowers: vi.fn(),
  getFollowing: vi.fn(),
  follow: vi.fn(),
  unfollow: vi.fn(),
}));

// Mock routing
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ username: "testuser" })),
    useNavigate: vi.fn(() => vi.fn()),
    Link: ({ children, to }) => <a href={to}>{children}</a>,
  };
});

// Mock contexts
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
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
  useToast: vi.fn(() => vi.fn()),
}));

// Mock complex child components
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));
vi.mock("../components/PostCard", () => ({
  default: ({ post }) => <div data-testid="post-card">{post.title}</div>,
}));
vi.mock("../components/UserCard", () => ({
  default: ({ user }) => <div data-testid="user-card">{user.username}</div>,
}));
vi.mock("../components/EditProfileModal", () => ({
  default: ({ open }) =>
    open ? <div data-testid="edit-profile-modal">Edit Modal</div> : null,
}));
vi.mock("../components/ui/Avatar", () => ({
  default: ({ alt }) => <img data-testid="avatar" alt={alt} />,
}));

import * as usersApi from "../api/users";
import { useAuth } from "../contexts/AuthContext";
import { useParams } from "react-router-dom";
import UserProfile from "./UserProfile";

beforeEach(() => {
  vi.clearAllMocks();
  // Default: viewing own profile
  useParams.mockReturnValue({ username: "testuser" });
  useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
});

describe("UserProfile", () => {
  const selfProfile = {
    id: 1,
    username: "testuser",
    display_name: "Test User",
    bio: "This is my bio.",
    avatar_url: null,
    follower_count: 42,
    following_count: 18,
    karma: 100,
    is_following: false,
  };

  const otherProfile = {
    id: 99,
    username: "otheruser",
    display_name: "Other User",
    bio: "Another user.",
    avatar_url: null,
    follower_count: 10,
    following_count: 5,
    karma: 50,
    is_following: false,
  };

  it("shows spinner while loading", () => {
    usersApi.getUser.mockReturnValue(new Promise(() => {}));

    render(<UserProfile />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("renders profile info (username, display name, bio)", async () => {
    usersApi.getUser.mockResolvedValue({ data: selfProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    // Username appears in header and profile section
    expect(screen.getAllByText("@testuser").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("This is my bio.")).toBeInTheDocument();
  });

  it("shows follower/following counts", async () => {
    usersApi.getUser.mockResolvedValue({ data: selfProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
    });

    expect(screen.getByText("followers")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText("following")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("karma")).toBeInTheDocument();
  });

  it("shows follow button for other users", async () => {
    useParams.mockReturnValue({ username: "otheruser" });
    usersApi.getUser.mockResolvedValue({ data: otherProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(screen.getByText("Other User")).toBeInTheDocument();
    });

    // Use exact text "Follow" to distinguish from "Following" tab and "Followers" tab
    expect(screen.getByRole("button", { name: "Follow" })).toBeInTheDocument();
  });

  it("shows edit profile button for self", async () => {
    usersApi.getUser.mockResolvedValue({ data: selfProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /edit profile/i }),
      ).toBeInTheDocument();
    });
  });

  it("does not show follow button for self", async () => {
    usersApi.getUser.mockResolvedValue({ data: selfProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /^follow$/i }),
    ).not.toBeInTheDocument();
  });

  it("renders Posts/Followers/Following tabs", async () => {
    usersApi.getUser.mockResolvedValue({ data: selfProfile });
    usersApi.getUserPosts.mockResolvedValue({ data: [] });

    render(<UserProfile />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Posts" })).toBeInTheDocument();
    });

    expect(screen.getByRole("tab", { name: "Followers" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Following" })).toBeInTheDocument();
  });
});
