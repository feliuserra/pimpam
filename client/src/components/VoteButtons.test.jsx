import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VoteButtons from "./VoteButtons";

vi.mock("../api/posts", () => ({
  vote: vi.fn(),
  retractVote: vi.fn(),
}));

vi.mock("./VoteButtons.module.css", () => ({
  default: {
    votes: "votes",
    voteBtn: "voteBtn",
    upvoted: "upvoted",
    downvoted: "downvoted",
    karma: "karma",
  },
}));

import * as postsApi from "../api/posts";

describe("VoteButtons", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders karma count", () => {
    render(<VoteButtons postId={1} karma={42} userVote={null} />);

    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("upvote button calls API and updates optimistically", async () => {
    postsApi.vote.mockResolvedValue({});
    const onKarmaChange = vi.fn();

    render(
      <VoteButtons
        postId={1}
        karma={10}
        userVote={null}
        onKarmaChange={onKarmaChange}
      />,
    );

    fireEvent.click(screen.getByLabelText("Upvote"));

    // Optimistic: karma should increase to 11
    expect(screen.getByText("11")).toBeInTheDocument();

    await waitFor(() => {
      expect(postsApi.vote).toHaveBeenCalledWith(1, 1);
      expect(onKarmaChange).toHaveBeenCalledWith(11, 1);
    });
  });

  it("downvote button calls API and updates optimistically", async () => {
    postsApi.vote.mockResolvedValue({});
    const onKarmaChange = vi.fn();

    render(
      <VoteButtons
        postId={1}
        karma={10}
        userVote={null}
        onKarmaChange={onKarmaChange}
      />,
    );

    fireEvent.click(screen.getByLabelText("Downvote"));

    // Optimistic: karma should decrease to 9
    expect(screen.getByText("9")).toBeInTheDocument();

    await waitFor(() => {
      expect(postsApi.vote).toHaveBeenCalledWith(1, -1);
      expect(onKarmaChange).toHaveBeenCalledWith(9, -1);
    });
  });

  it("reverts on API error", async () => {
    postsApi.vote.mockRejectedValue(new Error("Network error"));

    render(<VoteButtons postId={1} karma={10} userVote={null} />);

    fireEvent.click(screen.getByLabelText("Upvote"));

    // Optimistic: karma jumps to 11
    expect(screen.getByText("11")).toBeInTheDocument();

    // After rejection, should revert to 10
    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument();
    });
  });

  it("highlights active vote direction (upvoted)", () => {
    const { container } = render(
      <VoteButtons postId={1} karma={5} userVote={1} />,
    );

    const upvoteBtn = screen.getByLabelText("Upvote");
    expect(upvoteBtn.className).toContain("upvoted");
  });

  it("highlights active vote direction (downvoted)", () => {
    render(<VoteButtons postId={1} karma={5} userVote={-1} />);

    const downvoteBtn = screen.getByLabelText("Downvote");
    expect(downvoteBtn.className).toContain("downvoted");
  });

  it("retracts vote when clicking same direction again", async () => {
    postsApi.retractVote.mockResolvedValue({});
    const onKarmaChange = vi.fn();

    render(
      <VoteButtons
        postId={1}
        karma={10}
        userVote={1}
        onKarmaChange={onKarmaChange}
      />,
    );

    fireEvent.click(screen.getByLabelText("Upvote"));

    // Optimistic: karma should decrease to 9 (retract upvote)
    expect(screen.getByText("9")).toBeInTheDocument();

    await waitFor(() => {
      expect(postsApi.retractVote).toHaveBeenCalledWith(1);
      expect(onKarmaChange).toHaveBeenCalledWith(9, null);
    });
  });
});
