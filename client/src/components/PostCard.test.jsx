import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import PostCard from "./PostCard";

// Mock dependencies
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));

vi.mock("../api/posts", () => ({
  remove: vi.fn(),
  vote: vi.fn(),
  retractVote: vi.fn(),
}));

// Mock CSS module
vi.mock("./PostCard.module.css", () => ({ default: {} }));

import { useAuth } from "../contexts/AuthContext";
import * as postsApi from "../api/posts";

const basePost = {
  id: 10,
  title: "Test Post Title",
  content: "Some content here",
  author_id: 1,
  author_username: "testuser",
  author_avatar_url: null,
  community_name: "tech",
  created_at: new Date().toISOString(),
  is_edited: false,
  edited_at: null,
  karma: 5,
  user_vote: null,
  comment_count: 0,
  images: [],
  image_url: null,
  shared_from_id: null,
  share_comment: null,
  url: null,
  visibility: "public",
};

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("PostCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
  });

  it("renders post title, author username, and community badge", () => {
    wrap(<PostCard post={basePost} />);

    expect(screen.getByText("Test Post Title")).toBeInTheDocument();
    expect(screen.getByText("@testuser")).toBeInTheDocument();
    expect(screen.getByText("c/tech")).toBeInTheDocument();
  });

  it("renders vote buttons with karma count", () => {
    wrap(<PostCard post={basePost} />);

    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByLabelText("Upvote")).toBeInTheDocument();
    expect(screen.getByLabelText("Downvote")).toBeInTheDocument();
  });

  it("shows comment count when > 0", () => {
    wrap(<PostCard post={{ ...basePost, comment_count: 12 }} />);

    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("does not show comment count when 0", () => {
    wrap(<PostCard post={{ ...basePost, comment_count: 0 }} />);

    // Only the karma "5" should be rendered as a number
    const fives = screen.getAllByText("5");
    expect(fives.length).toBeGreaterThan(0);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows (edited) indicator when post.is_edited is true", () => {
    wrap(<PostCard post={{ ...basePost, is_edited: true }} />);

    expect(screen.getByText("(edited)")).toBeInTheDocument();
  });

  it("shows share header when post.shared_from_id exists", () => {
    wrap(
      <PostCard
        post={{ ...basePost, shared_from_id: 99, author_username: "testuser" }}
      />,
    );

    expect(screen.getByText("shared")).toBeInTheDocument();
  });

  it("shows overflow menu (edit/delete) only for author", () => {
    wrap(<PostCard post={basePost} />);

    // Author sees More options button
    expect(screen.getByLabelText("More options")).toBeInTheDocument();
  });

  it("does not show overflow menu for non-author", () => {
    useAuth.mockReturnValue({ user: { id: 999, username: "otheruser" } });
    wrap(<PostCard post={basePost} />);

    expect(screen.queryByLabelText("More options")).not.toBeInTheDocument();
  });

  it("calls onDelete when delete confirmed", async () => {
    const onDelete = vi.fn();
    postsApi.remove.mockResolvedValue({});
    vi.spyOn(window, "confirm").mockReturnValue(true);

    wrap(<PostCard post={basePost} onDelete={onDelete} />);

    // Open menu
    fireEvent.click(screen.getByLabelText("More options"));
    // Click Delete
    fireEvent.click(screen.getByText("Delete"));

    await waitFor(() => {
      expect(postsApi.remove).toHaveBeenCalledWith(10);
      expect(onDelete).toHaveBeenCalledWith(10);
    });

    window.confirm.mockRestore();
  });

  it("hides edit in menu when past 1h window", () => {
    const oldDate = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    wrap(<PostCard post={{ ...basePost, created_at: oldDate }} />);

    // Open menu
    fireEvent.click(screen.getByLabelText("More options"));

    // Delete should be present, Edit should not
    expect(screen.getByText("Delete")).toBeInTheDocument();
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
  });

  it("shows edit in menu when within 1h window", () => {
    const recentDate = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    wrap(<PostCard post={{ ...basePost, created_at: recentDate }} />);

    fireEvent.click(screen.getByLabelText("More options"));

    expect(screen.getByText("Edit")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("renders images with +N badge for multiple", () => {
    const post = {
      ...basePost,
      images: [
        { url: "/img1.webp", id: 1 },
        { url: "/img2.webp", id: 2 },
        { url: "/img3.webp", id: 3 },
      ],
    };
    wrap(<PostCard post={post} />);

    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("does not show +N badge for single image", () => {
    const post = {
      ...basePost,
      images: [{ url: "/img1.webp", id: 1 }],
    };
    wrap(<PostCard post={post} />);

    expect(screen.queryByText(/\+\d/)).not.toBeInTheDocument();
  });
});
