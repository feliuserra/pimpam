import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockGetFeed = vi.fn();
const mockGetMine = vi.fn();
const mockGetSeenStories = vi.fn(() => new Set());
const mockMarkStoriesSeen = vi.fn();

vi.mock("../api/stories", () => ({
  getFeed: (...args) => mockGetFeed(...args),
  getMine: (...args) => mockGetMine(...args),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser", avatar_url: null },
  })),
}));

vi.mock("../utils/seenStories", () => ({
  getSeenStories: (...args) => mockGetSeenStories(...args),
  markStoriesSeen: (...args) => mockMarkStoriesSeen(...args),
}));

import StoriesRow from "./StoriesRow";

describe("StoriesRow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetFeed.mockResolvedValue({ data: [] });
    mockGetMine.mockResolvedValue({ data: [] });
    localStorage.clear();
  });

  it("renders the Stories label and own story button", async () => {
    render(<StoriesRow onView={vi.fn()} onCompose={vi.fn()} />);

    expect(screen.getByText("Stories")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Your story")).toBeInTheDocument();
    });
  });

  it("renders story groups from the feed", async () => {
    mockGetFeed.mockResolvedValue({
      data: [
        {
          id: 10,
          author_username: "alice",
          author_avatar_url: null,
          author_id: 2,
          image_url: "/img1.webp",
        },
        {
          id: 11,
          author_username: "bob",
          author_avatar_url: null,
          author_id: 3,
          image_url: "/img2.webp",
        },
      ],
    });

    render(<StoriesRow onView={vi.fn()} onCompose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("alice")).toBeInTheDocument();
      expect(screen.getByText("bob")).toBeInTheDocument();
    });
  });

  it("calls onCompose when own story button clicked and user has no stories", async () => {
    const onCompose = vi.fn();
    mockGetMine.mockResolvedValue({ data: [] });

    render(<StoriesRow onView={vi.fn()} onCompose={onCompose} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Add story")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Add story"));
    expect(onCompose).toHaveBeenCalled();
  });

  it("calls onView when own story button clicked and user has stories", async () => {
    const onView = vi.fn();
    mockGetMine.mockResolvedValue({
      data: [{ id: 50, image_url: "/my.webp", caption: null }],
    });

    render(<StoriesRow onView={onView} onCompose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByLabelText("View your story")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("View your story"));
    expect(onView).toHaveBeenCalledWith(
      expect.objectContaining({
        author: expect.objectContaining({ username: "testuser" }),
        items: expect.arrayContaining([
          expect.objectContaining({ id: 50 }),
        ]),
      }),
    );
  });

  it("calls onView with group and marks stories seen when clicking a story group", async () => {
    mockGetFeed.mockResolvedValue({
      data: [
        {
          id: 20,
          author_username: "alice",
          author_avatar_url: null,
          author_id: 2,
          image_url: "/img.webp",
        },
      ],
    });

    const onView = vi.fn();
    render(<StoriesRow onView={onView} onCompose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("alice")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("View alice's story"));
    expect(onView).toHaveBeenCalled();
    expect(mockMarkStoriesSeen).toHaveBeenCalledWith([20]);
  });

  it("toggles collapse and restores from localStorage", async () => {
    render(<StoriesRow onView={vi.fn()} onCompose={vi.fn()} />);

    // Initially expanded — stories row visible
    await waitFor(() => {
      expect(screen.getByLabelText("Stories")).toBeInTheDocument();
    });

    // Click to collapse
    fireEvent.click(screen.getByLabelText("Hide stories"));

    // Stories row should be hidden
    expect(screen.queryByLabelText("Stories")).not.toBeInTheDocument();

    // localStorage should be updated
    expect(localStorage.getItem("pimpam_stories_collapsed")).toBe("1");

    // Click to expand again
    fireEvent.click(screen.getByLabelText("Show stories"));
    expect(screen.getByLabelText("Stories")).toBeInTheDocument();
  });
});
