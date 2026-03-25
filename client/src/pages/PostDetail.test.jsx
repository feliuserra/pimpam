import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/posts", () => ({
  get: vi.fn(),
  edit: vi.fn(),
  remove: vi.fn(),
}));

// Mock routing
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ id: "42" })),
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
vi.mock("../components/CommentThread", () => ({
  default: ({ postId }) => (
    <div data-testid="comment-thread">Comments for {postId}</div>
  ),
}));
vi.mock("../components/VoteButtons", () => ({
  default: ({ karma }) => <div data-testid="vote-buttons">Karma: {karma}</div>,
}));
vi.mock("../components/ImageGallery", () => ({
  default: () => <div data-testid="image-gallery" />,
}));
vi.mock("../components/ui/Avatar", () => ({
  default: ({ alt }) => <img data-testid="avatar" alt={alt} />,
}));
vi.mock("../components/ui/RelativeTime", () => ({
  default: () => <span data-testid="relative-time">just now</span>,
}));

import * as postsApi from "../api/posts";
import { useAuth } from "../contexts/AuthContext";
import PostDetail from "./PostDetail";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PostDetail", () => {
  const basePost = {
    id: 42,
    title: "Test Post Title",
    content: "Test post content body.",
    author_id: 1,
    author_username: "testuser",
    author_avatar_url: null,
    karma: 5,
    user_vote: null,
    created_at: new Date().toISOString(),
    community_name: null,
    is_edited: false,
    images: [],
    image_url: null,
    shared_from_id: null,
    visibility: "public",
  };

  it("shows spinner then loads post", async () => {
    postsApi.get.mockResolvedValue({ data: basePost });

    render(<PostDetail />);

    // Spinner should show while loading
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();

    // After loading, post title should appear
    await waitFor(() => {
      expect(screen.getByText("Test Post Title")).toBeInTheDocument();
    });
  });

  it("shows error state when post not found (404)", async () => {
    postsApi.get.mockRejectedValue({ response: { status: 404 } });

    render(<PostDetail />);

    await waitFor(() => {
      expect(screen.getByText("Post not found")).toBeInTheDocument();
    });
  });

  it("renders post title and content", async () => {
    postsApi.get.mockResolvedValue({ data: basePost });

    render(<PostDetail />);

    await waitFor(() => {
      expect(screen.getByText("Test Post Title")).toBeInTheDocument();
    });

    expect(screen.getByText("Test post content body.")).toBeInTheDocument();
    expect(screen.getByTestId("comment-thread")).toBeInTheDocument();
    expect(screen.getByTestId("vote-buttons")).toBeInTheDocument();
  });

  it("shows edit button for author within 1h", async () => {
    // Post created just now, so within the 1-hour edit window
    const recentPost = {
      ...basePost,
      created_at: new Date().toISOString(),
    };
    postsApi.get.mockResolvedValue({ data: recentPost });

    render(<PostDetail />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /edit/i }),
      ).toBeInTheDocument();
    });
  });

  it("does not show edit button after 1h", async () => {
    // Post created 2 hours ago, outside the edit window
    const oldPost = {
      ...basePost,
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    };
    postsApi.get.mockResolvedValue({ data: oldPost });

    render(<PostDetail />);

    await waitFor(() => {
      expect(screen.getByText("Test Post Title")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
  });

  it("shows delete button for author", async () => {
    postsApi.get.mockResolvedValue({ data: basePost });

    render(<PostDetail />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });
  });

  it("does not show author actions for non-author", async () => {
    // Current user id=1, post author id=99
    const otherPost = { ...basePost, author_id: 99, author_username: "other" };
    postsApi.get.mockResolvedValue({ data: otherPost });

    render(<PostDetail />);

    await waitFor(() => {
      expect(screen.getByText("Test Post Title")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
  });
});
