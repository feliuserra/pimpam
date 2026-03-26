import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import CommentCard from "./CommentCard";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));

vi.mock("../api/comments", () => ({
  create: vi.fn(),
  remove: vi.fn(),
  react: vi.fn(),
  listReplies: vi.fn(),
}));

import { useAuth } from "../contexts/AuthContext";
import * as commentsApi from "../api/comments";

const baseComment = {
  id: 100,
  post_id: 10,
  author_id: 1,
  author_username: "testuser",
  author_avatar_url: null,
  content: "This is a comment.",
  created_at: new Date().toISOString(),
  is_removed: false,
  depth: 0,
  reply_count: 0,
  reaction_counts: {},
};

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("CommentCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
  });

  it("renders author, content, and timestamp", () => {
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.getByText("@testuser")).toBeInTheDocument();
    expect(screen.getByText("This is a comment.")).toBeInTheDocument();
    // RelativeTime renders a <time> element
    expect(screen.getByTagName?.("time") ?? document.querySelector("time")).toBeTruthy();
  });

  it("shows [deleted] for removed comments", () => {
    wrap(<CommentCard comment={{ ...baseComment, is_removed: true }} />);

    expect(screen.getByText("[deleted]")).toBeInTheDocument();
    expect(screen.queryByText("This is a comment.")).not.toBeInTheDocument();
  });

  it("shows reaction buttons", () => {
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.getByText("Agree")).toBeInTheDocument();
    expect(screen.getByText("Love")).toBeInTheDocument();
    expect(screen.getByText("Misleading")).toBeInTheDocument();
    expect(screen.getByText("Disagree")).toBeInTheDocument();
  });

  it("shows reply button for authenticated users", () => {
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.getByText("Reply")).toBeInTheDocument();
  });

  it("does not show reply button for unauthenticated users", () => {
    useAuth.mockReturnValue({ user: null });
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.queryByText("Reply")).not.toBeInTheDocument();
  });

  it("submitting reply calls API and invokes onReply", async () => {
    const onReply = vi.fn();
    const newReply = {
      id: 101,
      post_id: 10,
      author_id: 1,
      author_username: "testuser",
      content: "My reply",
      created_at: new Date().toISOString(),
      is_removed: false,
      depth: 1,
      reply_count: 0,
      reaction_counts: {},
    };
    commentsApi.create.mockResolvedValue({ data: newReply });

    wrap(<CommentCard comment={baseComment} onReply={onReply} />);

    // Click Reply to show input
    fireEvent.click(screen.getByText("Reply"));

    // Type reply
    const input = screen.getByPlaceholderText("Write a reply...");
    fireEvent.change(input, { target: { value: "My reply" } });

    // Submit form
    fireEvent.submit(input.closest("form"));

    await waitFor(() => {
      expect(commentsApi.create).toHaveBeenCalledWith(10, {
        content: "My reply",
        parent_id: 100,
      });
      expect(onReply).toHaveBeenCalledWith(newReply);
    });
  });

  it("shows 'Load N replies' when reply_count > 0", () => {
    wrap(<CommentCard comment={{ ...baseComment, reply_count: 3 }} />);

    expect(screen.getByText("Load 3 replies")).toBeInTheDocument();
  });

  it("shows singular 'Load 1 reply' for single reply", () => {
    wrap(<CommentCard comment={{ ...baseComment, reply_count: 1 }} />);

    expect(screen.getByText("Load 1 reply")).toBeInTheDocument();
  });

  it("delete button visible only for author", () => {
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("delete button not visible for non-author", () => {
    useAuth.mockReturnValue({ user: { id: 999, username: "otheruser" } });
    wrap(<CommentCard comment={baseComment} />);

    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("clicking delete calls API when confirmed", async () => {
    const onDeleted = vi.fn();
    commentsApi.remove.mockResolvedValue({});
    vi.spyOn(window, "confirm").mockReturnValue(true);

    wrap(<CommentCard comment={baseComment} onDeleted={onDeleted} />);

    fireEvent.click(screen.getByText("Delete"));

    await waitFor(() => {
      expect(commentsApi.remove).toHaveBeenCalledWith(100);
      expect(onDeleted).toHaveBeenCalledWith(100);
    });

    window.confirm.mockRestore();
  });
});
