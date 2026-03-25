import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/feed", () => ({
  getTrending: vi.fn(),
  getNews: vi.fn(),
}));

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
vi.mock("../components/PostCard", () => ({
  default: ({ post }) => <div data-testid="post-card">{post.title}</div>,
}));
vi.mock("../components/PostCardSkeleton", () => ({
  default: () => <div data-testid="skeleton">Skeleton</div>,
}));
vi.mock("../components/ui/Spinner", () => ({
  default: () => <div role="status" aria-label="Loading">Loading...</div>,
}));

import * as feedApi from "../api/feed";
import Discover from "./Discover";

beforeEach(() => {
  global.IntersectionObserver = vi.fn(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.clearAllMocks();
});

describe("Discover", () => {
  const trendingPosts = [
    { id: 1, title: "Hot post", content: "Trending content" },
    { id: 2, title: "Popular post", content: "Also trending" },
  ];

  const newsPosts = [
    { id: 10, title: "News article", content: "Breaking news" },
    { id: 11, title: "Another article", content: "More news" },
  ];

  it("renders Trending and News tabs", () => {
    feedApi.getTrending.mockReturnValue(new Promise(() => {}));

    render(<Discover />);

    expect(screen.getByRole("tab", { name: "Trending" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Discover")).toBeInTheDocument();
  });

  it("shows skeleton placeholders while trending is loading", () => {
    feedApi.getTrending.mockReturnValue(new Promise(() => {}));

    render(<Discover />);

    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });

  it("renders trending posts after loading", async () => {
    feedApi.getTrending.mockResolvedValue({ data: trendingPosts });

    render(<Discover />);

    await waitFor(() => {
      expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    });

    expect(screen.getByText("Hot post")).toBeInTheDocument();
    expect(screen.getByText("Popular post")).toBeInTheDocument();
    // Trending posts show rank numbers
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
  });

  it("shows empty state when no trending posts", async () => {
    feedApi.getTrending.mockResolvedValue({ data: [] });

    render(<Discover />);

    await waitFor(() => {
      expect(
        screen.getByText("No trending posts in this time window."),
      ).toBeInTheDocument();
    });
  });

  it("switches to News tab and loads news posts", async () => {
    feedApi.getTrending.mockResolvedValue({ data: trendingPosts });
    feedApi.getNews.mockResolvedValue({ data: newsPosts });

    render(<Discover />);

    // Wait for trending to load first
    await waitFor(() => {
      expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    });

    // Click News tab
    fireEvent.click(screen.getByRole("tab", { name: "News" }));

    await waitFor(() => {
      expect(screen.getByText("News article")).toBeInTheDocument();
    });

    expect(screen.getByText("Another article")).toBeInTheDocument();
    expect(feedApi.getNews).toHaveBeenCalled();
  });

  it("time window buttons reload trending with different hours", async () => {
    feedApi.getTrending.mockResolvedValue({ data: trendingPosts });

    render(<Discover />);

    await waitFor(() => {
      expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    });

    // Click the 48h window button
    fireEvent.click(screen.getByText("48h"));

    await waitFor(() => {
      expect(feedApi.getTrending).toHaveBeenCalledWith(
        expect.objectContaining({ hours: 48 }),
      );
    });
  });
});
