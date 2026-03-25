import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockList = vi.fn();
const mockCreate = vi.fn();

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser" },
  })),
}));

vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
}));

vi.mock("../api/comments", () => ({
  list: (...args) => mockList(...args),
  create: (...args) => mockCreate(...args),
}));

vi.mock("./CommentCard", () => ({
  default: ({ comment }) => (
    <div data-testid={`comment-${comment.id}`}>
      <span>{comment.author_username}</span>
      <span>{comment.content}</span>
    </div>
  ),
}));

vi.mock("./ui/Spinner", () => ({
  default: () => <span data-testid="spinner">Loading...</span>,
}));

import CommentThread from "./CommentThread";
import { useAuth } from "../contexts/AuthContext";

const sampleComments = [
  {
    id: 100,
    post_id: 10,
    author_id: 2,
    author_username: "alice",
    author_avatar_url: null,
    content: "Great post!",
    created_at: new Date().toISOString(),
    is_removed: false,
    depth: 0,
    reply_count: 0,
    reaction_counts: {},
  },
  {
    id: 101,
    post_id: 10,
    author_id: 3,
    author_username: "bob",
    author_avatar_url: null,
    content: "I agree",
    created_at: new Date().toISOString(),
    is_removed: false,
    depth: 0,
    reply_count: 0,
    reaction_counts: {},
  },
];

describe("CommentThread", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ data: sampleComments });
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
  });

  it("renders comments after loading", async () => {
    render(<CommentThread postId={10} />);

    await waitFor(() => {
      expect(screen.getByTestId("comment-100")).toBeInTheDocument();
      expect(screen.getByTestId("comment-101")).toBeInTheDocument();
    });

    expect(mockList).toHaveBeenCalledWith(10, { sort: "latest", limit: 50 });
  });

  it("shows empty state when no comments", async () => {
    mockList.mockResolvedValue({ data: [] });

    render(<CommentThread postId={10} />);

    await waitFor(() => {
      expect(screen.getByText("No comments yet. Be the first!")).toBeInTheDocument();
    });
  });

  it("shows sort selector with Latest and Top options", async () => {
    render(<CommentThread postId={10} />);

    const select = screen.getByLabelText("Sort comments");
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue("latest");

    // Change sort
    fireEvent.change(select, { target: { value: "top" } });

    await waitFor(() => {
      expect(mockList).toHaveBeenCalledWith(10, { sort: "top", limit: 50 });
    });
  });

  it("renders comment compose form for authenticated users", async () => {
    render(<CommentThread postId={10} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Write a comment...")).toBeInTheDocument();
      expect(screen.getByText("Post")).toBeInTheDocument();
    });
  });

  it("does not render compose form when user is not logged in", async () => {
    useAuth.mockReturnValue({ user: null });

    render(<CommentThread postId={10} />);

    await waitFor(() => {
      expect(screen.queryByPlaceholderText("Write a comment...")).not.toBeInTheDocument();
    });
  });

  it("submits a new comment successfully", async () => {
    const newComment = {
      id: 102,
      post_id: 10,
      author_id: 1,
      author_username: "testuser",
      content: "My new comment",
      created_at: new Date().toISOString(),
      is_removed: false,
      depth: 0,
      reply_count: 0,
      reaction_counts: {},
    };
    mockCreate.mockResolvedValue({ data: newComment });

    render(<CommentThread postId={10} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Write a comment...")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText("Write a comment...");
    fireEvent.change(input, { target: { value: "My new comment" } });
    fireEvent.submit(input.closest("form"));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(10, { content: "My new comment" });
      expect(screen.getByTestId("comment-102")).toBeInTheDocument();
    });
  });

  it("disables submit button when input is empty", async () => {
    render(<CommentThread postId={10} />);

    await waitFor(() => {
      const submitBtn = screen.getByText("Post");
      expect(submitBtn).toBeDisabled();
    });
  });
});
