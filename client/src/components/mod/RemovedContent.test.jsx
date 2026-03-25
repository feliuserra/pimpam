import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../../api/moderation", () => ({
  restorePost: vi.fn(),
  removePost: vi.fn(),
  restoreComment: vi.fn(),
  removeComment: vi.fn(),
}));

vi.mock("./ModSection.module.css", () => ({
  default: {
    heading: "heading",
    section: "section",
    inlineForm: "inlineForm",
    input: "input",
    btn: "btn",
    dangerBtn: "dangerBtn",
    error: "error",
    success: "success",
  },
}));

import RemovedContent from "./RemovedContent";
import * as modApi from "../../api/moderation";

describe("RemovedContent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Posts and Comments sections", () => {
    render(<RemovedContent communityName="tech" />);
    expect(screen.getByText("Posts")).toBeInTheDocument();
    expect(screen.getByText("Comments")).toBeInTheDocument();
  });

  it("renders post ID and comment ID inputs", () => {
    render(<RemovedContent communityName="tech" />);
    expect(screen.getByPlaceholderText("Post ID")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Comment ID")).toBeInTheDocument();
  });

  it("restore and remove buttons are disabled when input is empty", () => {
    render(<RemovedContent communityName="tech" />);
    const restoreButtons = screen.getAllByText("Restore");
    const removeButtons = screen.getAllByText("Remove");
    restoreButtons.forEach((btn) => expect(btn).toBeDisabled());
    removeButtons.forEach((btn) => expect(btn).toBeDisabled());
  });

  // Post actions
  it("restores a post successfully", async () => {
    modApi.restorePost.mockResolvedValue({});

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Post ID"), {
      target: { value: "123" },
    });

    // The Restore button is the submit button of the first form
    const restoreButtons = screen.getAllByText("Restore");
    fireEvent.click(restoreButtons[0]);

    await waitFor(() => {
      expect(modApi.restorePost).toHaveBeenCalledWith("tech", "123");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Post 123 restored.");
    // type="number" input has value null when cleared, not ""
    expect(screen.getByPlaceholderText("Post ID")).toHaveValue(null);
  });

  it("removes a post successfully", async () => {
    modApi.removePost.mockResolvedValue({});

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Post ID"), {
      target: { value: "456" },
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(modApi.removePost).toHaveBeenCalledWith("tech", "456");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Post 456 removed.");
  });

  it("shows error when post restore fails", async () => {
    modApi.restorePost.mockRejectedValue({
      response: { data: { detail: "Post not found" } },
    });

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Post ID"), {
      target: { value: "999" },
    });

    const restoreButtons = screen.getAllByText("Restore");
    fireEvent.click(restoreButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Post not found");
    });
  });

  it("shows error when post remove fails", async () => {
    modApi.removePost.mockRejectedValue({
      response: { data: { detail: "Not authorized" } },
    });

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Post ID"), {
      target: { value: "456" },
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Not authorized");
    });
  });

  // Comment actions
  it("restores a comment successfully", async () => {
    modApi.restoreComment.mockResolvedValue({});

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Comment ID"), {
      target: { value: "77" },
    });

    const restoreButtons = screen.getAllByText("Restore");
    fireEvent.click(restoreButtons[1]); // second Restore button is for comments

    await waitFor(() => {
      expect(modApi.restoreComment).toHaveBeenCalledWith("tech", "77");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Comment 77 restored.");
  });

  it("removes a comment successfully", async () => {
    modApi.removeComment.mockResolvedValue({});

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Comment ID"), {
      target: { value: "88" },
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[1]); // second Remove button is for comments

    await waitFor(() => {
      expect(modApi.removeComment).toHaveBeenCalledWith("tech", "88");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Comment 88 removed.");
  });

  it("shows error when comment restore fails", async () => {
    modApi.restoreComment.mockRejectedValue({
      response: { data: { detail: "Comment not found" } },
    });

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Comment ID"), {
      target: { value: "99" },
    });

    const restoreButtons = screen.getAllByText("Restore");
    fireEvent.click(restoreButtons[1]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Comment not found");
    });
  });

  it("shows fallback error when no detail in response", async () => {
    modApi.restorePost.mockRejectedValue(new Error("Network error"));

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Post ID"), {
      target: { value: "123" },
    });

    const restoreButtons = screen.getAllByText("Restore");
    fireEvent.click(restoreButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Failed to restore post",
      );
    });
  });

  it("shows fallback error for comment remove failure", async () => {
    modApi.removeComment.mockRejectedValue(new Error("Network error"));

    render(<RemovedContent communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Comment ID"), {
      target: { value: "88" },
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[1]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Failed to remove comment",
      );
    });
  });
});
