import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API and context dependencies
vi.mock("../api/feed", () => ({ getFeed: vi.fn() }));
vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
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
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: vi.fn(() => vi.fn()) };
});

// Mock complex child components
vi.mock("../components/PostCard", () => ({
  default: ({ post }) => <div data-testid="post-card">{post.title}</div>,
}));
vi.mock("../components/StoriesRow", () => ({
  default: () => <div data-testid="stories-row">Stories</div>,
}));
vi.mock("../components/StoryViewer", () => ({
  default: () => <div data-testid="story-viewer">StoryViewer</div>,
}));
vi.mock("../components/StoryCompose", () => ({
  default: () => <div data-testid="story-compose">StoryCompose</div>,
}));
vi.mock("../components/ComposePost", () => ({
  default: () => <div data-testid="compose-post">ComposePost</div>,
}));
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));

import { getFeed } from "../api/feed";
import { useWS } from "../contexts/WSContext";
import Feed from "./Feed";

// Mock IntersectionObserver for useInfiniteList
beforeEach(() => {
  global.IntersectionObserver = vi.fn(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.clearAllMocks();
});

describe("Feed", () => {
  it("shows spinner while loading", async () => {
    // getFeed never resolves, so loading stays true once triggered
    getFeed.mockReturnValue(new Promise(() => {}));

    render(<Feed />);

    // Trigger the IntersectionObserver callback to start loading
    const observerCallback =
      global.IntersectionObserver.mock.calls[0]?.[0];
    if (observerCallback) {
      observerCallback([{ isIntersecting: true }]);
    }

    await waitFor(() => {
      expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    });
  });

  it("renders posts from feed API", async () => {
    const posts = [
      { id: 1, title: "First post", content: "Hello" },
      { id: 2, title: "Second post", content: "World" },
    ];
    getFeed.mockResolvedValue({ data: posts });

    render(<Feed />);

    // useInfiniteList calls refresh on initial render via IntersectionObserver
    // We need to trigger it manually; let's trigger via the hook's flow.
    // The hook calls loadMore when the sentinel is intersecting.
    // Since we mock IntersectionObserver, we need to trigger the callback.
    const observerCallback =
      global.IntersectionObserver.mock.calls[0]?.[0];
    if (observerCallback) {
      observerCallback([{ isIntersecting: true }]);
    }

    await waitFor(() => {
      expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    });

    expect(screen.getByText("First post")).toBeInTheDocument();
    expect(screen.getByText("Second post")).toBeInTheDocument();
  });

  it("shows empty state when no posts", async () => {
    getFeed.mockResolvedValue({ data: [] });

    render(<Feed />);

    const observerCallback =
      global.IntersectionObserver.mock.calls[0]?.[0];
    if (observerCallback) {
      observerCallback([{ isIntersecting: true }]);
    }

    await waitFor(() => {
      expect(
        screen.getByText("Follow people or join a community to see posts!"),
      ).toBeInTheDocument();
    });
  });

  it("shows 'New posts available' banner when WS new_post event fires", async () => {
    getFeed.mockResolvedValue({ data: [{ id: 1, title: "Existing" }] });

    // Capture the WS callback that Feed registers
    let wsCallback;
    useWS.mockImplementation((eventType, handler) => {
      if (eventType === "new_post") {
        wsCallback = handler;
      }
    });

    render(<Feed />);

    // Trigger the sentinel to load initial posts
    const observerCallback =
      global.IntersectionObserver.mock.calls[0]?.[0];
    if (observerCallback) {
      observerCallback([{ isIntersecting: true }]);
    }

    await waitFor(() => {
      expect(screen.getByTestId("post-card")).toBeInTheDocument();
    });

    // Simulate WS new_post event
    expect(wsCallback).toBeDefined();
    wsCallback();

    await waitFor(() => {
      expect(screen.getByText("New posts available")).toBeInTheDocument();
    });
  });
});
