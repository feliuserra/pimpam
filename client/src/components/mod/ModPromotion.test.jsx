import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../../api/moderation", () => ({
  proposeMod: vi.fn(),
}));

vi.mock("./ModSection.module.css", () => ({
  default: {
    heading: "heading",
    hint: "hint",
    form: "form",
    input: "input",
    btn: "btn",
    error: "error",
    success: "success",
  },
}));

import ModPromotion from "./ModPromotion";
import * as modApi from "../../api/moderation";

describe("ModPromotion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading and hint text", () => {
    render(<ModPromotion communityName="tech" />);
    expect(screen.getByText("Propose Moderator")).toBeInTheDocument();
    expect(
      screen.getByText(/Target must have 200\+ community karma/),
    ).toBeInTheDocument();
  });

  it("renders form with username input and role select", () => {
    render(<ModPromotion communityName="tech" />);
    expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Moderator")).toBeInTheDocument();
  });

  it("submit button is disabled when username is empty", () => {
    render(<ModPromotion communityName="tech" />);
    const submitBtn = screen.getByRole("button", { name: "Propose" });
    expect(submitBtn).toBeDisabled();
  });

  it("submit button is enabled when username is filled", () => {
    render(<ModPromotion communityName="tech" />);
    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "alice" },
    });
    const submitBtn = screen.getByRole("button", { name: "Propose" });
    expect(submitBtn).not.toBeDisabled();
  });

  it("submits proposal with correct data", async () => {
    modApi.proposeMod.mockResolvedValue({
      data: { vote_count: 1, required_votes: 3 },
    });

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "alice" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(modApi.proposeMod).toHaveBeenCalledWith("tech", {
        target_username: "alice",
        target_role: "moderator",
      });
    });
  });

  it("shows success message after successful proposal", async () => {
    modApi.proposeMod.mockResolvedValue({
      data: { vote_count: 1, required_votes: 3 },
    });

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Proposal created. Votes: 1/3",
      );
    });

    // Username should be cleared after success
    expect(screen.getByPlaceholderText("Username")).toHaveValue("");
  });

  it("shows error message on failure", async () => {
    modApi.proposeMod.mockRejectedValue({
      response: { data: { detail: "Insufficient karma" } },
    });

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "newbie" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Insufficient karma");
    });
  });

  it("shows fallback error when no detail in response", async () => {
    modApi.proposeMod.mockRejectedValue(new Error("Network error"));

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Failed to propose",
      );
    });
  });

  it("can select senior_mod role", async () => {
    modApi.proposeMod.mockResolvedValue({
      data: { vote_count: 1, required_votes: 5 },
    });

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "bob" },
    });
    fireEvent.change(screen.getByDisplayValue("Moderator"), {
      target: { value: "senior_mod" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(modApi.proposeMod).toHaveBeenCalledWith("tech", {
        target_username: "bob",
        target_role: "senior_mod",
      });
    });
  });

  it("shows Submitting... text while busy", async () => {
    modApi.proposeMod.mockReturnValue(new Promise(() => {})); // Never resolves

    render(<ModPromotion communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose" }));

    await waitFor(() => {
      expect(screen.getByText("Submitting...")).toBeInTheDocument();
    });
  });
});
